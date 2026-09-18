"""
SQLAlchemy engine and session management.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.config import settings

engine = create_engine(
    settings.database_url,
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_session() -> Session:
    """Get a new database session. Caller is responsible for closing it."""
    return SessionLocal()


def get_db():
    """FastAPI dependency — yields a session and closes it after request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
