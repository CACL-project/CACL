from pydantic import BaseModel, ConfigDict
from uuid import UUID


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    first_name: str | None = None
    last_name: str | None = None
    is_admin: bool
    is_active: bool
