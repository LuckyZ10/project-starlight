"""Database initialization and session management for Starlight."""
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from starlight.models import Base
from starlight.config import settings


engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db() -> None:
    """Create all tables if they don't exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the session factory for dependency injection."""
    return async_session
