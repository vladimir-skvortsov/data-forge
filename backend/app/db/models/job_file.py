import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.enums import FileStatus, FileType
from app.db.session import Base

if TYPE_CHECKING:
    from app.db.models.job import Job


class JobFile(Base):
    __tablename__ = 'job_files'
    __table_args__ = (Index('idx_job_files_job_id', 'job_id'),)

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text('gen_random_uuid()'),
    )
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('jobs.id', ondelete='CASCADE'))
    original_name: Mapped[str] = mapped_column(String(255))
    file_type: Mapped[FileType] = mapped_column(String(20))
    file_path: Mapped[str] = mapped_column(String(500))
    file_size_bytes: Mapped[int] = mapped_column(Integer)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[FileStatus] = mapped_column(
        String(20), server_default=text("'queued'")
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    job: Mapped[Job] = relationship(back_populates='files')
