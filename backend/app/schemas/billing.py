import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.db.enums import TransactionType


class BalanceResponse(BaseModel):
    wallet_id: uuid.UUID
    balance: Decimal


class TopupRequest(BaseModel):
    amount: Decimal = Field(gt=0, decimal_places=2)


class PromoRequest(BaseModel):
    code: str = Field(min_length=1, max_length=50)


class TransactionOut(BaseModel):
    id: uuid.UUID
    type: TransactionType
    amount: Decimal
    description: str | None
    created_at: datetime

    model_config = {'from_attributes': True}


class TransactionListResponse(BaseModel):
    items: list[TransactionOut]
    total: int
