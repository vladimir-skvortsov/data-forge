import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.enums import PromoCodeType
from app.db.session import Base

if TYPE_CHECKING:
    from app.db.models.promo_activation import PromoActivation


class PromoCode(Base):
    __tablename__ = 'promo_codes'

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text('gen_random_uuid()'),
    )
    code: Mapped[str] = mapped_column(String(50), unique=True)
    type: Mapped[PromoCodeType] = mapped_column(String(20))
    credit_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    discount_percentage: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    max_activations: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_activations: Mapped[int] = mapped_column(Integer, server_default=text('0'))
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text('true'))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    activations: Mapped[list[PromoActivation]] = relationship(
        back_populates='promo_code'
    )
