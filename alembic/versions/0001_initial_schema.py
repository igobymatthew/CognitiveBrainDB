"""Initial schema with vector-backed embeddings.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-03-02 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "capture",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source_uri", sa.String(length=2048), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "chunk",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("capture_id", sa.UUID(), nullable=False),
        sa.Column("index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["capture_id"], ["capture.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chunk_capture_id_index", "chunk", ["capture_id", "index"], unique=True)

    op.create_table(
        "mode",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("vec_base", Vector(dim=1536), nullable=False),
        sa.Column("vec_current", Vector(dim=1536), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "chunk_embedding",
        sa.Column("chunk_id", sa.UUID(), nullable=False),
        sa.Column("embedding", Vector(dim=1536), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["chunk_id"], ["chunk.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("chunk_id"),
    )

    op.create_table(
        "edge",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source_chunk_id", sa.UUID(), nullable=False),
        sa.Column("target_chunk_id", sa.UUID(), nullable=False),
        sa.Column("mode_id", sa.UUID(), nullable=True),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["mode_id"], ["mode.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_chunk_id"], ["chunk.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_chunk_id"], ["chunk.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_edge_source_target_mode", "edge", ["source_chunk_id", "target_chunk_id", "mode_id"], unique=False)

    op.create_table(
        "activation",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("mode_id", sa.UUID(), nullable=False),
        sa.Column("chunk_id", sa.UUID(), nullable=True),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["chunk_id"], ["chunk.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["mode_id"], ["mode.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_activation_mode_created", "activation", ["mode_id", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_activation_mode_created", table_name="activation")
    op.drop_table("activation")

    op.drop_index("ix_edge_source_target_mode", table_name="edge")
    op.drop_table("edge")

    op.drop_table("chunk_embedding")
    op.drop_table("mode")

    op.drop_index("ix_chunk_capture_id_index", table_name="chunk")
    op.drop_table("chunk")

    op.drop_table("capture")
