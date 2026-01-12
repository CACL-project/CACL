from fastapi import FastAPI, Depends

from app.db import async_session_maker
from cacl.db import register_session_maker
from cacl.dependencies import get_current_user, get_current_admin

register_session_maker(async_session_maker)

app = FastAPI(title="CACL App")


@app.get("/protected")
async def protected_route(user=Depends(get_current_user)):
    return {"detail": "Access granted", "user_id": str(user.id)}


@app.get("/admin-only")
async def admin_route(admin=Depends(get_current_admin)):
    return {"detail": "Admin access granted", "user_id": str(admin.id)}
