from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel


class EstimateItem(BaseModel):
    item: str
    credits: float


class EstimateResponse(BaseModel):
    breakdown: list[EstimateItem]
    total_credits: Decimal
    current_balance: Decimal
    can_proceed: bool


class CreditsByDay(BaseModel):
    date: str
    credits: float


class FileTypeCount(BaseModel):
    file_type: str
    count: int


class DashboardStats(BaseModel):
    jobs_by_status: dict[str, int]
    credits_by_day: list[CreditsByDay]
    top_file_types: list[FileTypeCount]
    total_credits_spent: Decimal
