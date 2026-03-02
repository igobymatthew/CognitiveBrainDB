from __future__ import annotations

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cognitivebrain.models.base import Base


class Capture(Base):
    __tablename__ = "capture"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_uri: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    chunks: Mapped[list[Chunk]] = relationship(back_populates="capture", cascade="all, delete-orphan")


class Chunk(Base):
    __tablename__ = "chunk"
    __table_args__ = (Index("ix_chunk_capture_id_index", "capture_id", "index", unique=True),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    capture_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("capture.id", ondelete="CASCADE"), nullable=False
    )
    index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    capture: Mapped[Capture] = relationship(back_populates="chunks")
    embedding: Mapped[ChunkEmbedding | None] = relationship(
        back_populates="chunk", uselist=False, cascade="all, delete-orphan"
    )
    outgoing_edges: Mapped[list[Edge]] = relationship(
        foreign_keys="Edge.source_chunk_id",
        back_populates="source_chunk",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    incoming_edges: Mapped[list[Edge]] = relationship(
        foreign_keys="Edge.target_chunk_id",
        back_populates="target_chunk",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    activations: Mapped[list[Activation]] = relationship(back_populates="chunk")


class ChunkEmbedding(Base):
    __tablename__ = "chunk_embedding"

    chunk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chunk.id", ondelete="CASCADE"), primary_key=True
    )
    embedding: Mapped[list[float]] = mapped_column(Vector(1536), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    chunk: Mapped[Chunk] = relationship(back_populates="embedding")


class Mode(Base):
    __tablename__ = "mode"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    vec_base: Mapped[list[float]] = mapped_column(Vector(1536), nullable=False)
    vec_current: Mapped[list[float]] = mapped_column(Vector(1536), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    edges: Mapped[list[Edge]] = relationship(back_populates="mode")
    activations: Mapped[list[Activation]] = relationship(back_populates="mode", passive_deletes=True)


class Edge(Base):
    __tablename__ = "edge"
    __table_args__ = (Index("ix_edge_source_target_mode", "source_chunk_id", "target_chunk_id", "mode_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_chunk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chunk.id", ondelete="CASCADE"), nullable=False
    )
    target_chunk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chunk.id", ondelete="CASCADE"), nullable=False
    )
    mode_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("mode.id", ondelete="SET NULL"), nullable=True
    )
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    source_chunk: Mapped[Chunk] = relationship(foreign_keys=[source_chunk_id], back_populates="outgoing_edges")
    target_chunk: Mapped[Chunk] = relationship(foreign_keys=[target_chunk_id], back_populates="incoming_edges")
    mode: Mapped[Mode | None] = relationship(back_populates="edges")


class Activation(Base):
    __tablename__ = "activation"
    __table_args__ = (Index("ix_activation_mode_created", "mode_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mode_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("mode.id", ondelete="CASCADE"), nullable=False
    )
    chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chunk.id", ondelete="SET NULL"), nullable=True
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    mode: Mapped[Mode] = relationship(back_populates="activations")
    chunk: Mapped[Chunk | None] = relationship(back_populates="activations")
