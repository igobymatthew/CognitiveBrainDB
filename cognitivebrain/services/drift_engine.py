from __future__ import annotations

import hashlib
import math
import random
from collections.abc import Iterable
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from cognitivebrain.models.entities import Activation, Edge, Mode

EMBEDDING_DIM = 1536

PROFILE_PARAMS: dict[str, dict[str, float]] = {
    "stable": {"alpha": 0.08, "lambda": 0.01, "tau": 0.12, "rho": 0.96},
    "balanced": {"alpha": 0.16, "lambda": 0.02, "tau": 0.2, "rho": 0.94},
    "aggressive": {"alpha": 0.28, "lambda": 0.03, "tau": 0.28, "rho": 0.9},
}


def embed_text(text: str) -> list[float]:
    """Generate a deterministic pseudo-embedding of length 1536 from text."""
    seed = int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest(), "big")
    rng = random.Random(seed)
    vec = [rng.uniform(-1.0, 1.0) for _ in range(EMBEDDING_DIM)]
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def _cosine_similarity(vec_a: Iterable[float], vec_b: Iterable[float]) -> float:
    a = list(vec_a)
    b = list(vec_b)
    if not a or not b:
        return 0.0
    denom = (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))) or 1.0
    return sum(x * y for x, y in zip(a, b, strict=False)) / denom


def _resolve_profile(profile: str) -> dict[str, float]:
    return PROFILE_PARAMS.get(profile.lower(), PROFILE_PARAMS["balanced"]).copy()


def _expand_touched_mode_ids(
    session: Session,
    seed_mode_ids: list[Any],
    expand_hops: int,
    k_touch: int,
) -> list[Any]:
    touched: list[Any] = []
    seen = set(seed_mode_ids)
    frontier = list(seed_mode_ids)

    for mode_id in seed_mode_ids:
        touched.append(mode_id)
        if len(touched) >= k_touch:
            return touched[:k_touch]

    if expand_hops <= 0:
        return touched[:k_touch]

    for _ in range(expand_hops):
        if not frontier or len(touched) >= k_touch:
            break

        rows = session.execute(
            select(Edge.source_chunk_id, Edge.target_chunk_id, Edge.mode_id).where(Edge.mode_id.in_(frontier))
        ).all()

        chunk_ids = {chunk_id for row in rows for chunk_id in (row.source_chunk_id, row.target_chunk_id)}
        if not chunk_ids:
            frontier = []
            continue

        neighbor_rows = session.execute(
            select(Edge.mode_id).where(
                Edge.mode_id.is_not(None),
                (Edge.source_chunk_id.in_(chunk_ids)) | (Edge.target_chunk_id.in_(chunk_ids)),
            )
        ).all()

        next_frontier: list[Any] = []
        for (neighbor_mode_id,) in neighbor_rows:
            if neighbor_mode_id is None or neighbor_mode_id in seen:
                continue
            seen.add(neighbor_mode_id)
            touched.append(neighbor_mode_id)
            next_frontier.append(neighbor_mode_id)
            if len(touched) >= k_touch:
                return touched[:k_touch]

        frontier = next_frontier

    return touched[:k_touch]


def query_and_drift(
    session: Session,
    query_text: str,
    profile: str,
    k_seeds: int = 20,
    k_touch: int = 80,
    expand_hops: int = 1,
) -> dict[str, Any]:
    """Run seed recall + drift updates and write a single activation record.

    Note: transaction commit is intentionally owned by the caller/route layer.
    """
    query_vec = embed_text(query_text)

    modes = session.scalars(select(Mode)).all()
    if not modes:
        return {"activation_id": None, "seeds": [], "touched": [], "delta": {}}

    ranked = sorted(
        ((mode, _cosine_similarity(query_vec, mode.vec_current)) for mode in modes),
        key=lambda item: item[1],
        reverse=True,
    )
    seeds = [mode for mode, _ in ranked[: max(0, k_seeds)]]
    seed_ids = [mode.id for mode in seeds]

    if not seed_ids:
        return {"activation_id": None, "seeds": [], "touched": [], "delta": {}}

    session.scalars(select(Mode).where(Mode.id.in_(seed_ids)).with_for_update()).all()

    touched_ids = _expand_touched_mode_ids(session, seed_ids, expand_hops=expand_hops, k_touch=k_touch)
    locked_touched = session.scalars(select(Mode).where(Mode.id.in_(touched_ids)).with_for_update()).all()

    params = _resolve_profile(profile)
    alpha = params.get("alpha", 0.0)
    lam = params.get("lambda", 0.0)
    tau = params.get("tau", 0.0)
    rho = params.get("rho", 1.0)

    now = datetime.now(timezone.utc)
    delta: dict[str, dict[str, float]] = {}

    for mode in locked_touched:
        old_vec = list(mode.vec_current)
        seed_sim = _cosine_similarity(mode.vec_current, query_vec)
        base_vec = list(mode.vec_base)

        new_vec = [
            (rho * cur) + (alpha * q) + (lam * (base - cur)) + (tau * seed_sim)
            for cur, q, base in zip(old_vec, query_vec, base_vec, strict=False)
        ]

        norm = math.sqrt(sum(v * v for v in new_vec)) or 1.0
        mode.vec_current = [v / norm for v in new_vec]

        if hasattr(mode, "mass"):
            current_mass = getattr(mode, "mass", 0.0) or 0.0
            setattr(mode, "mass", current_mass + max(0.0, seed_sim))

        if hasattr(mode, "last_activated_at"):
            setattr(mode, "last_activated_at", now)

        delta[str(mode.id)] = {
            "cos_before": seed_sim,
            "drift_magnitude": math.sqrt(
                sum((a - b) * (a - b) for a, b in zip(mode.vec_current, old_vec, strict=False))
            ),
        }

    activation_table = Activation.__table__
    payload: dict[str, Any] = {}
    cols = activation_table.c

    if "mode_id" in cols:
        payload["mode_id"] = seed_ids[0]
    if "chunk_id" in cols:
        payload["chunk_id"] = None
    if "score" in cols:
        payload["score"] = float(ranked[0][1])
    if "seed_mode_ids" in cols:
        payload["seed_mode_ids"] = seed_ids
    if "touched_mode_ids" in cols:
        payload["touched_mode_ids"] = touched_ids
    if "params_json" in cols:
        payload["params_json"] = params
    if "delta_json" in cols:
        payload["delta_json"] = delta

    inserted = session.execute(activation_table.insert().values(**payload).returning(activation_table.c.id)).scalar_one()

    return {
        "activation_id": inserted,
        "seeds": [str(mode_id) for mode_id in seed_ids],
        "touched": [str(mode_id) for mode_id in touched_ids],
        "delta": delta,
    }
