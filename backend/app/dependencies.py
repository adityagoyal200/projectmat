from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency to yield an async database session."""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
