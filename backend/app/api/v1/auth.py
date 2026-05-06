from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.security import create_access_token, verify_password
from app.database import get_db
from app.schemas.common import ok

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    from app.models.user import User

    result = await db.execute(select(User).where(User.username == req.username, User.deleted_at.is_(None)))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(req.password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token(user.id, user.username)
    return ok({"token": token, "username": user.username, "role": user.role})


@router.get("/me")
async def me(current_user: dict = Depends(get_current_user)):
    return ok(current_user)
