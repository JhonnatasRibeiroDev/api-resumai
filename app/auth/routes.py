from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.schemas import LoginRequest, Token
from app.auth.service import authenticate_user, create_user
from app.core.config import Settings, get_settings
from app.core.security import create_access_token
from app.db.session import get_db
from app.users.schemas import UserCreate, UserRead


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> UserRead:
    return create_user(db, payload)


@router.post("/login", response_model=Token)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Token:
    user = authenticate_user(db, payload.identifier, payload.password)
    access_token = create_access_token(str(user.id), settings)
    return Token(access_token=access_token)
