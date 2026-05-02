from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.db.models.job import Job


class JobResult(Base):
    __tablename__ = 'job_results'

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text('gen_random_uuid()'),
    )
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('jobs.id'), unique=True)
    result_file_path: Mapped[str] = mapped_column(String(500))
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    job: Mapped[Job] = relationship(back_populates='result')
