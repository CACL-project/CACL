import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, Boolean, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID

from cacl.models.base import Base


class JWTToken(Base):
    """
    Database model for JWT token storage.
    Supports access and refresh tokens with expiration and blacklist control.

    NOTE: user_id is a plain UUID column with an index.
    CACL intentionally does NOT define a database-level foreign key to the users table.
    This decouples CACL from your application's ORM base class and table structure.

    Security contract: token verification still loads the current user via get_user_model()
    and rejects the token if the user does not exist or is inactive.

    Orphaned tokens: if your application hard-deletes users, you are responsible for
    removing the related jwt_tokens rows in your application layer or via a cleanup job.
    """
    __tablename__ = "jwt_tokens"

    __table_args__ = (
        Index("ix_jwt_tokens_token_type", "token", "token_type"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    token = Column(Text, unique=True, nullable=False)
    token_type = Column(String, nullable=False)  # "access" or "refresh"
    is_blacklisted = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)

    def __str__(self):
        return f"{self.token_type} token for user {self.user_id} (blacklisted={self.is_blacklisted})"

    def is_valid(self) -> bool:
        return (not self.is_blacklisted) and (self.expires_at > datetime.utcnow())
