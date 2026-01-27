from typing import Protocol


class UserProtocol(Protocol):
    id: str
    is_active: bool
    is_admin: bool
