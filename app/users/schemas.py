from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=255)
    username: str = Field(min_length=3, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    description: str | None = None
    profile_image: str | None = None


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    username: str | None = Field(default=None, min_length=3, max_length=100)
    email: EmailStr | None = None
    description: str | None = None
    profile_image: str | None = None


class UserRead(BaseModel):
    id: UUID
    full_name: str
    username: str
    email: EmailStr
    description: str | None = None
    profile_image: str | None = None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
