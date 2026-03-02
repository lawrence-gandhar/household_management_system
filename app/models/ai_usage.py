# app/models/ai_usage.py
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AIUsageLog(Base):
    """
    Append-only table. Never update, never delete.
    Drives billing, abuse detection, and observability dashboards.

    Index strategy:
    - (user_id, created_at) for per-user dashboards
    - (created_at) for aggregate ops-level monitoring
    - (success, error_code) for error-rate alerting
    """
    __tablename__ = "ai_usage_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), index=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    # ── OpenAI metadata ───────────────────────────────────────────
    model:             Mapped[str]   = mapped_column(String(50))
    prompt_tokens:     Mapped[int]   = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int]   = mapped_column(Integer, default=0)
    total_tokens:      Mapped[int]   = mapped_column(Integer, default=0)
    cost_usd:          Mapped[float] = mapped_column(Float,   default=0.0)
    latency_ms:        Mapped[int]   = mapped_column(Integer, default=0)

    # ── Outcome ───────────────────────────────────────────────────
    cache_hit:  Mapped[bool]       = mapped_column(Boolean, default=False)
    success:    Mapped[bool]       = mapped_column(Boolean, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)