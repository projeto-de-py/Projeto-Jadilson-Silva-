"""Engine, sessao e base do SQLAlchemy."""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings

settings = get_settings()

connect_args: dict = {}
if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,  # reconecta conexoes mortas do MySQL
    connect_args=connect_args,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base de todos os models (SQLAlchemy 2.0 declarativo)."""


def get_db():
    """Dependencia do FastAPI: uma sessao por request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
