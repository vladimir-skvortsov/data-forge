from fastapi import APIRouter

from app.api.deps import CurrentUser
from app.db.session import DBSession
from app.schemas.dashboard import DashboardStats
from app.services import dashboard_service

router = APIRouter(prefix='/dashboard', tags=['dashboard'])


@router.get('/stats')
async def get_stats(current_user: CurrentUser, db: DBSession) -> DashboardStats:
    data = await dashboard_service.get_stats(str(current_user.id), db)
    return DashboardStats(**data)
