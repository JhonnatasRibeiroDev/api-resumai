from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.users.models import User
from app.users.schemas import UserCreate


def normalize_email(email: str) -> str:
    return email.strip().lower()


def normalize_username(username: str) -> str:
    return username.strip()


def create_user(db: Session, payload: UserCreate) -> User:
    email = normalize_email(str(payload.email))
    username = normalize_username(payload.username)

    existing_email = db.scalar(select(User).where(User.email == email))
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email já cadastrado.",
        )

    existing_username = db.scalar(select(User).where(User.username == username))
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username já cadastrado.",
        )

    user = User(
        full_name=payload.full_name.strip(),
        username=username,
        email=email,
        password_hash=hash_password(payload.password),
        description=payload.description,
        profile_image=payload.profile_image,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, identifier: str, password: str) -> User:
    normalized_identifier = identifier.strip()
    email_identifier = normalized_identifier.lower()
    user = db.scalar(
        select(User).where(
            or_(
                User.email == email_identifier,
                User.username == normalized_identifier,
            )
        )
    )

    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_user_by_id(db: Session, user_id: UUID) -> User | None:
    return db.get(User, user_id)
