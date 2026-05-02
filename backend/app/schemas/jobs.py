import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from app.db.enums import FileStatus, FileType, JobStatus


class PipelineBlockConfig(BaseModel):
    type: str
    params: dict[str, Any] = {}


class JobCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    schema_config: dict[str, Any]
    pipeline_config: list[PipelineBlockConfig] = []


class JobFileOut(BaseModel):
    id: uuid.UUID
    original_name: str
    file_type: FileType
    status: FileStatus
    file_size_bytes: int
    created_at: datetime

    model_config = {'from_attributes': True}


class JobOut(BaseModel):
    id: uuid.UUID
    title: str
    status: JobStatus
    schema_config: dict[str, Any]
    pipeline_config: list[Any]
    credits_estimate: Decimal | None
    credits_charged: Decimal | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    files: list[JobFileOut] = []

    model_config = {'from_attributes': True}


class JobListResponse(BaseModel):
    items: list[JobOut]
    total: int


class RunJobResponse(BaseModel):
    job_id: uuid.UUID
    status: JobStatus
    credits_held: Decimal
