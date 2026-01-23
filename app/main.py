from fastapi import FastAPI, Depends
from sqlalchemy import select

from app.db import async_session_maker
from app.models.users import User
from app.routes.auth import router as auth_router
from cacl.db import register_session_maker
from cacl.dependencies import get_current_user, get_current_admin

register_session_maker(async_session_maker)

app = FastAPI(title="CACL Demo App")

app.include_router(auth_router)


@app.get("/me")
async def get_my_profile(user=Depends(get_current_user)):
    """
    Returns current user profile.
    """
    return {
        "id": str(user.id),
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "is_admin": user.is_admin,
        "is_active": user.is_active,
    }


@app.get("/admin/users")
async def list_users(admin=Depends(get_current_admin)):
    """
    Returns list of all users (admin only).
    """
    async with async_session_maker() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()

        return [
            {
                "id": str(u.id),
                "email": u.email,
                "first_name": u.first_name,
                "last_name": u.last_name,
                "is_admin": u.is_admin,
                "is_active": u.is_active,
            }
            for u in users
        ]
