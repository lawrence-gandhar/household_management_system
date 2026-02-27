import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, validates


class Base(DeclarativeBase):
    """Project-wide declarative base."""


class UUIDMixin:
    """Adds a UUID primary key column."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )


class TimestampMixin:
    """Adds server-side ``created_at`` / ``updated_at`` columns.

    Both columns are **database-managed**:

    ``created_at``
        Set once on INSERT via ``server_default=func.now()``.  Read-only
        from Python — assigning it raises ``AttributeError``.  SQLAlchemy
        does NOT fire this guard during ORM load / refresh operations.

    ``updated_at``
        Set on INSERT and refreshed on every UPDATE via ``onupdate=func.now()``.
        Also read-only from Python for the same reason.

    Neither field should ever appear in Create or Update forms; both are
    excluded globally via :attr:`LabeledModelAdmin._db_managed_fields`.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        index=True,
    )

    # ── ORM-level read-only guards ────────────────────────────────────────────
    # SQLAlchemy fires @validates on explicit Python-level attribute sets but
    # NOT during internal ORM load / flush / refresh operations, so the guard
    # is safe to use unconditionally.

    @validates("created_at")
    def _guard_created_at(self, key: str, value: datetime) -> datetime:  # noqa: ARG002
        raise AttributeError(
            f"'{type(self).__name__}.created_at' is server-managed and "
            "cannot be assigned in Python."
        )

    @validates("updated_at")
    def _guard_updated_at(self, key: str, value: datetime) -> datetime:  # noqa: ARG002
        raise AttributeError(
            f"'{type(self).__name__}.updated_at' is server-managed and "
            "cannot be assigned in Python."
        )
