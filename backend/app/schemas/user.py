"""User schemas — Pydantic v2 models for user management."""

from datetime import datetime
from pydantic import BaseModel, Field


class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    created_at: datetime
    is_active: bool
    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=255)
    role: str = Field("", max_length=50)
    role_ids: list[int] = Field(default_factory=list)


class UserUpdate(BaseModel):
    role: str | None = Field(None, max_length=50)
    password: str | None = Field(None, max_length=255)
    role_ids: list[int] | None = Field(None)
