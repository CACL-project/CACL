import uuid
from datetime import datetime
from passlib.hash import bcrypt
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from cacl.models.base import Base


class User(Base):
    """
    User model for the demo application.
    """
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    surname = Column(String, nullable=True)
    email = Column(String, unique=True, nullable=False)
    phone = Column(String, unique=True, nullable=True)
    date_of_birth = Column(DateTime, nullable=True)
    medical_policy_number = Column(String, nullable=True)
    password_hash = Column(String, nullable=True)
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=False)
    email_verify = Column(Boolean, default=False)
    created = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<User {self.email}>"

    def set_password(self, password: str):
        """Hash password using bcrypt and store in password_hash field."""
        self.password_hash = bcrypt.hash(password)

    def verify_password(self, password: str) -> bool:
        """Verify password against stored hash."""
        if not self.password_hash:
            return False
        return bcrypt.verify(password, self.password_hash)
