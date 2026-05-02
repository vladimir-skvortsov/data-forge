from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.db.models.job import Job
    from app.db.models.transaction import Transaction
    from app.db.models.wallet import Wallet


class User(Base):
    __tablename__ = 'users'

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text('gen_random_uuid()'),
    )
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    wallet: Mapped[Wallet] = relationship(back_populates='user', uselist=False)
    jobs: Mapped[list[Job]] = relationship(back_populates='user')
    transactions: Mapped[list[Transaction]] = relationship(back_populates='user')
