from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.dashboard.schemas import DashboardRead
from app.dashboard.service import get_dashboard
from app.db.session import get_db
from app.users.models import User


router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardRead)
def read_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DashboardRead:
    return get_dashboard(db, current_user)
