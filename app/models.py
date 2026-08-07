from datetime import datetime
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import get_settings
from app.core.db import Base

settings = get_settings()
DIM = settings.embedding_dimensions


class Founder(Base):
    __tablename__ = "founders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    stage: Mapped[str] = mapped_column(String(50), nullable=False)
    sector: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[Optional[list[float]]] = mapped_column(Vector(DIM))
    meta: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Investor(Base):
    __tablename__ = "investors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    firm: Mapped[str] = mapped_column(String(255), nullable=False)
    thesis: Mapped[str] = mapped_column(Text, nullable=False)
    preferred_stages: Mapped[list] = mapped_column(JSONB, default=list)
    preferred_sectors: Mapped[list] = mapped_column(JSONB, default=list)
    check_size_min: Mapped[Optional[float]] = mapped_column(Float)
    check_size_max: Mapped[Optional[float]] = mapped_column(Float)
    embedding: Mapped[Optional[list[float]]] = mapped_column(Vector(DIM))
    meta: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MatchPipeline(Base):
    __tablename__ = "match_pipelines"
    __table_args__ = (UniqueConstraint("founder_id", "investor_id", name="uq_founder_investor"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    founder_id: Mapped[int] = mapped_column(Integer, nullable=False)
    investor_id: Mapped[int] = mapped_column(Integer, nullable=False)
    current_stage: Mapped[str] = mapped_column(String(50), default="matched", nullable=False)
    last_reply_summary: Mapped[Optional[str]] = mapped_column(Text)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    score_at_match: Mapped[Optional[float]] = mapped_column(Float)

    # Meeting details
    meeting_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    meeting_type: Mapped[Optional[str]] = mapped_column(String(50))  # intro | follow_up | partner | other
    meeting_notes: Mapped[Optional[str]] = mapped_column(Text)
    follow_up_expected: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MatchMessage(Base):
    __tablename__ = "match_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    founder_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    investor_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    sender: Mapped[str] = mapped_column(String(50), nullable=False)
    kind: Mapped[str] = mapped_column(String(50), default="note", nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MatchFeedback(Base):
    __tablename__ = "match_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    founder_id: Mapped[int] = mapped_column(Integer, nullable=False)
    investor_id: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    outcome: Mapped[str] = mapped_column(String(50), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())