from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.db.models.promo_code import PromoCode


class PromoActivation(Base):
    __tablename__ = 'promo_activations'
    __table_args__ = (UniqueConstraint('user_id', 'promo_code_id'),)

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text('gen_random_uuid()'),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id'))
    promo_code_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('promo_codes.id'))
    activated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    promo_code: Mapped[PromoCode] = relationship(back_populates='activations')
