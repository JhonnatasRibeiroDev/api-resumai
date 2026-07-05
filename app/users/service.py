from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.service import normalize_email, normalize_username
from app.users.models import User
from app.users.schemas import UserUpdate


def update_user_profile(db: Session, user: User, payload: UserUpdate) -> User:
    data = payload.model_dump(exclude_unset=True)

    if "email" in data and data["email"] is not None:
        email = normalize_email(str(data["email"]))
        existing = db.scalar(select(User).where(User.email == email, User.id != user.id))
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email já cadastrado.",
            )
        user.email = email

    if "username" in data and data["username"] is not None:
        username = normalize_username(data["username"])
        existing = db.scalar(
            select(User).where(User.username == username, User.id != user.id)
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username já cadastrado.",
            )
        user.username = username

    if "full_name" in data and data["full_name"] is not None:
        user.full_name = data["full_name"].strip()

    if "description" in data:
        user.description = data["description"]

    if "profile_image" in data:
        user.profile_image = data["profile_image"]

    db.add(user)
    db.commit()
    db.refresh(user)
    return user
