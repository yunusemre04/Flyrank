from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# image.status lifecycle: pending -> processing -> tagged | flagged | failed
IMAGE_READY = ("tagged", "flagged")


class Image(Base):
    __tablename__ = "images"
    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(255), unique=True)
    path: Mapped[str] = mapped_column(String(1024))
    sha256: Mapped[str] = mapped_column(String(64), unique=True)  # same bytes are ingested once
    mime: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    subject: Mapped[str | None] = mapped_column(String(80), index=True)
    category: Mapped[str | None] = mapped_column(String(40), index=True)
    attributes: Mapped[list] = mapped_column(JSON, default=list)
    caption: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float | None] = mapped_column(Float)
    flagged: Mapped[bool] = mapped_column(Boolean, default=False)
    error: Mapped[str | None] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ImageTag(Base):
    """Normalised tags (subject / category / attribute) for filtering without parsing JSON."""

    __tablename__ = "image_tags"
    __table_args__ = (Index("ix_image_tags_kind_value", "kind", "value"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    image_id: Mapped[int] = mapped_column(ForeignKey("images.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(16))
    value: Mapped[str] = mapped_column(String(80))


class ImageVector(Base):
    __tablename__ = "image_vectors"
    image_id: Mapped[int] = mapped_column(ForeignKey("images.id", ondelete="CASCADE"), primary_key=True)
    model: Mapped[str] = mapped_column(String(80))
    dim: Mapped[int] = mapped_column(Integer)
    vector: Mapped[list] = mapped_column(JSON)  # ~50 rows: a JSON array + numpy is plenty (pgvector optional)


class Post(Base):
    __tablename__ = "posts"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True)
    title: Mapped[str] = mapped_column(String(300))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PostVector(Base):
    __tablename__ = "post_vectors"
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True)
    model: Mapped[str] = mapped_column(String(80))
    dim: Mapped[int] = mapped_column(Integer)
    vector: Mapped[list] = mapped_column(JSON)


class Suggestion(Base):
    """One (post, image) pairing with the guard's verdict and the human review state."""

    __tablename__ = "suggestions"
    __table_args__ = (
        UniqueConstraint("post_id", "image_id", name="uq_suggestion_pair"),
        Index("ix_suggestions_post_rank", "post_id", "rank"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"))
    image_id: Mapped[int] = mapped_column(ForeignKey("images.id", ondelete="CASCADE"), index=True)
    rank: Mapped[int] = mapped_column(Integer)
    similarity: Mapped[float] = mapped_column(Float)
    guard_approved: Mapped[bool] = mapped_column(Boolean)
    codes: Mapped[list] = mapped_column(JSON, default=list)
    reasons: Mapped[list] = mapped_column(JSON, default=list)
    review_status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    review_note: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(24), default="process")
    # queued | running | succeeded | partial | failed | budget_exceeded
    status: Mapped[str] = mapped_column(String(20), default="queued", index=True)
    total: Mapped[int] = mapped_column(Integer, default=0)
    done: Mapped[int] = mapped_column(Integer, default=0)
    failed: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CostEntry(Base):
    """One row per provider call (including failed/invalid ones)."""

    __tablename__ = "cost_entries"
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int | None] = mapped_column(ForeignKey("jobs.id", ondelete="SET NULL"), index=True)
    kind: Mapped[str] = mapped_column(String(16))  # vision | embedding
    provider: Mapped[str] = mapped_column(String(24))
    model: Mapped[str] = mapped_column(String(80))
    image_id: Mapped[int | None] = mapped_column(ForeignKey("images.id", ondelete="SET NULL"), index=True)
    post_id: Mapped[int | None] = mapped_column(ForeignKey("posts.id", ondelete="SET NULL"))
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)  # list-price equivalent; $0 is billed on free tiers
    ok: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
