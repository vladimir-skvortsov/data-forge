from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.enums import JobStatus
from app.db.session import Base

if TYPE_CHECKING:
    from app.db.models.job_file import JobFile
    from app.db.models.job_result import JobResult
    from app.db.models.user import User


class Job(Base):
    __tablename__ = 'jobs'
    __table_args__ = (
        Index('idx_jobs_user_id', 'user_id'),
        Index('idx_jobs_status', 'status'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text('gen_random_uuid()'),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id'))
    title: Mapped[str] = mapped_column(String(255))
    status: Mapped[JobStatus] = mapped_column(
        String(20), server_default=text("'draft'")
    )
    schema_config: Mapped[dict[str, Any]] = mapped_column(JSONB)
    pipeline_config: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        server_default=text("'[]'"),
    )
    credits_estimate: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    credits_charged: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user: Mapped[User] = relationship(back_populates='jobs')
    files: Mapped[list[JobFile]] = relationship(
        back_populates='job', cascade='all, delete-orphan'
    )
    result: Mapped[JobResult | None] = relationship(back_populates='job', uselist=False)
