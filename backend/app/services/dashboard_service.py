from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import TransactionType
from app.db.models.job import Job
from app.db.models.job_file import JobFile
from app.db.models.transaction import Transaction


async def get_stats(user_id: str, db: AsyncSession) -> dict:
    uid = uuid.UUID(user_id)

    # jobs by status
    rows = (
        await db.execute(
            select(Job.status, func.count(Job.id))
            .where(Job.user_id == uid)
            .group_by(Job.status)
        )
    ).fetchall()
    jobs_by_status = {str(row[0]): row[1] for row in rows}

    # credits by day — use HOLD (start of spending event), last 30 days
    since = datetime.now(UTC) - timedelta(days=30)
    rows = (
        await db.execute(
            select(
                func.date(Transaction.created_at).label('date'),
                func.sum(-Transaction.amount).label('credits'),
            )
            .where(
                Transaction.user_id == uid,
                Transaction.type == TransactionType.HOLD,
                Transaction.created_at >= since,
            )
            .group_by(func.date(Transaction.created_at))
            .order_by(func.date(Transaction.created_at))
        )
    ).fetchall()
    credits_by_day = [
        {'date': str(row.date), 'credits': float(row.credits or 0)} for row in rows
    ]

    # top file types
    rows = (
        await db.execute(
            select(JobFile.file_type, func.count(JobFile.id).label('cnt'))
            .join(Job, Job.id == JobFile.job_id)
            .where(Job.user_id == uid)
            .group_by(JobFile.file_type)
            .order_by(func.count(JobFile.id).desc())
            .limit(5)
        )
    ).fetchall()
    top_file_types = [{'file_type': str(row[0]), 'count': row[1]} for row in rows]

    # total credits charged (finalised billing events only)
    total = (
        await db.execute(
            select(func.coalesce(func.sum(-Transaction.amount), 0)).where(
                Transaction.user_id == uid,
                Transaction.type == TransactionType.CHARGE,
            )
        )
    ).scalar()

    return {
        'jobs_by_status': jobs_by_status,
        'credits_by_day': credits_by_day,
        'top_file_types': top_file_types,
        'total_credits_spent': Decimal(str(total or 0)),
    }
