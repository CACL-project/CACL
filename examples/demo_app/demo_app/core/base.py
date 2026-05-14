from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    SQLAlchemy declarative base for demo_app models.

    This is intentionally separate from cacl.models.base.Base.
    CACL does not require your application models to share its Base —
    keeping them separate avoids FK coupling and gives you full control
    over your own schema.
    """
    pass
