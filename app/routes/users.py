from fastapi import APIRouter, Depends
from sqlalchemy import select

from cacl.dependencies import get_current_user, get_current_admin

from app.db import async_session_maker
from app.models.users import User
from app.schemas.users import UserResponse


router = APIRouter(tags=["users"])


@router.get("/me", response_model=UserResponse)
async def get_profile(user=Depends(get_current_user)):
    return UserResponse.model_validate(user)


@router.get("/admin/users", response_model=list[UserResponse])
async def list_users(admin=Depends(get_current_admin)):
    async with async_session_maker() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()
        return [UserResponse.model_validate(u) for u in users]
