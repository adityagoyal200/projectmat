from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

# For async operations we use the asyncpg driver
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.ENV == "development",
    future=True,
)

async_session = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)


class Base(DeclarativeBase):
    """Base declarative class for all SQLAlchemy ORM models."""

    pass
