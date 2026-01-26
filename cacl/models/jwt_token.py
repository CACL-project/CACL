import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID

from cacl.models.base import Base


class JWTToken(Base):
    """
    Database model for JWT token storage.
    Supports access and refresh tokens with expiration and blacklist control.
    """
    __tablename__ = "jwt_tokens"

    __table_args__ = (
        Index("ix_jwt_tokens_token_type", "token", "token_type"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    token = Column(Text, unique=True, nullable=False)
    token_type = Column(String, nullable=False)  # "access" or "refresh"
    is_blacklisted = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)

    def __str__(self):
        return f"{self.token_type} token for user {self.user_id} (blacklisted={self.is_blacklisted})"

    def is_valid(self) -> bool:
        return (not self.is_blacklisted) and (self.expires_at > datetime.utcnow())
