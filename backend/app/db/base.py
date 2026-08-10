"""Declarative base shared by every SQLAlchemy model.

Kept in its own module (rather than in session.py) so `alembic/env.py` can import
`Base.metadata` without also importing the engine/session machinery.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
