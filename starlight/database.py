"""Database initialization, session management, and DB-backed progress for Starlight."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from starlight.config import settings
from starlight.core.progress import ProgressManager
from starlight.models import Base, User, UserProgress

engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db() -> None:
    """Create all tables if they don't exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the session factory for dependency injection."""
    return async_session


# ------------------------------------------------------------------
# User helpers
# ------------------------------------------------------------------

async def ensure_user(telegram_id: int, name: str) -> int:
    """Create a User row if missing. Returns the internal ``users.id``."""
    async with async_session() as session:
        stmt = select(User).where(User.telegram_id == str(telegram_id))
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None:
            user = User(telegram_id=str(telegram_id), name=name)
            session.add(user)
            await session.commit()
            await session.refresh(user)
        return user.id


async def get_active_cartridge(telegram_id: int) -> str | None:
    """Return the cartridge_id of the user's most recent *in_progress* row, or None."""
    async with async_session() as session:
        stmt = (
            select(UserProgress)
            .join(User)
            .where(User.telegram_id == str(telegram_id))
            .where(UserProgress.status == "in_progress")
            .order_by(UserProgress.started_at.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        progress = result.scalar_one_or_none()
        return progress.cartridge_id if progress else None


# ------------------------------------------------------------------
# DB-backed progress manager
# ------------------------------------------------------------------

class DatabaseProgressManager:
    """Drop-in replacement for MockProgressManager backed by SQLite.

    Each method opens its own short-lived ``AsyncSession`` so the
    long-lived harness never holds a stale connection.
    """

    @staticmethod
    async def _resolve_user_id(session: AsyncSession, telegram_id: int) -> int:
        stmt = select(User).where(User.telegram_id == str(telegram_id))
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None:
            raise ValueError(
                f"User with telegram_id={telegram_id} not found – call ensure_user first"
            )
        return user.id

    async def get_progress(self, user_id: int, cartridge_id: str):
        async with async_session() as session:
            uid = await self._resolve_user_id(session, user_id)
            return await ProgressManager(session).get_progress(uid, cartridge_id)

    async def start_cartridge(self, user_id: int, cartridge_id: str, entry_node: str = "N01"):
        async with async_session() as session:
            uid = await self._resolve_user_id(session, user_id)
            return await ProgressManager(session).start_cartridge(uid, cartridge_id, entry_node)

    async def advance_node(self, user_id: int, cartridge_id: str, next_node: str):
        async with async_session() as session:
            uid = await self._resolve_user_id(session, user_id)
            return await ProgressManager(session).advance_node(uid, cartridge_id, next_node)

    async def complete_cartridge(self, user_id: int, cartridge_id: str):
        async with async_session() as session:
            uid = await self._resolve_user_id(session, user_id)
            return await ProgressManager(session).complete_cartridge(uid, cartridge_id)
