from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.users.models import User
from app.users.schemas import UserRead, UserUpdate
from app.users.service import update_user_profile


router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
def read_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.patch("/me", response_model=UserRead)
def update_me(
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> User:
    return update_user_profile(db, current_user, payload)
