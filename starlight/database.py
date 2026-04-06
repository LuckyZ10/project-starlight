"""Database initialization, session management, and DB-backed progress for Starlight."""
from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from starlight.config import settings
from starlight.core.progress import ProgressManager
from starlight.core.session import Session, Exchange
from starlight.core.learner import LearnerProfile, ErrorPattern, ZPDZone
from starlight.core.spaced_rep import ReviewCard
from starlight.models import (
    Base, User, UserProgress,
    LearningSession, LearnerProfileModel, ReviewCardModel,
)

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
    
    Expects ``user_id`` to be the internal ``users.id`` (not telegram_id).
    The TelegramAdapter calls ``ensure_user()`` before invoking the harness,
    so the user row always exists.
    """

    async def get_progress(self, user_id: int, cartridge_id: str):
        async with async_session() as session:
            return await ProgressManager(session).get_progress(user_id, cartridge_id)

    async def start_cartridge(self, user_id: int, cartridge_id: str, entry_node: str = "N01"):
        async with async_session() as session:
            return await ProgressManager(session).start_cartridge(user_id, cartridge_id, entry_node)

    async def advance_node(self, user_id: int, cartridge_id: str, next_node: str):
        async with async_session() as session:
            return await ProgressManager(session).advance_node(user_id, cartridge_id, next_node)

    async def complete_cartridge(self, user_id: int, cartridge_id: str):
        async with async_session() as session:
            return await ProgressManager(session).complete_cartridge(user_id, cartridge_id)


# ------------------------------------------------------------------
# Session persistence
# ------------------------------------------------------------------

async def save_session(session: Session) -> None:
    """Upsert a learning session to DB."""
    async with async_session() as db:
        stmt = select(LearningSession).where(
            LearningSession.user_id == session.user_id,
            LearningSession.cartridge_id == session.cartridge_id,
        )
        result = await db.execute(stmt)
        row = result.scalar_one_or_none()

        conv_json = [
            {
                "role": ex.role,
                "content": ex.content,
                "metadata": ex.metadata,
                "timestamp": ex.timestamp.isoformat() if ex.timestamp else None,
            }
            for ex in session.conversation
        ]

        if row is None:
            row = LearningSession(
                user_id=session.user_id,
                cartridge_id=session.cartridge_id,
                current_node=session.current_node,
                turn_count=session.turn_count,
                max_turns=session.max_turns,
                conversation_json=conv_json,
                node_scores_json=session.node_scores,
            )
            db.add(row)
        else:
            row.current_node = session.current_node
            row.turn_count = session.turn_count
            row.max_turns = session.max_turns
            row.conversation_json = conv_json
            row.node_scores_json = session.node_scores
            row.updated_at = datetime.utcnow()

        await db.commit()


async def load_session(user_id: int, cartridge_id: str) -> Session | None:
    """Load a learning session from DB."""
    async with async_session() as db:
        stmt = select(LearningSession).where(
            LearningSession.user_id == user_id,
            LearningSession.cartridge_id == cartridge_id,
        )
        result = await db.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None

        conversation = []
        for ex_data in (row.conversation_json or []):
            ts = ex_data.get("timestamp")
            conversation.append(Exchange(
                role=ex_data["role"],
                content=ex_data["content"],
                metadata=ex_data.get("metadata"),
                timestamp=datetime.fromisoformat(ts) if ts else datetime.utcnow(),
            ))

        sess = Session(
            user_id=row.user_id,
            cartridge_id=row.cartridge_id,
            current_node=row.current_node,
            conversation=conversation,
            turn_count=row.turn_count,
            max_turns=row.max_turns,
            node_scores=row.node_scores_json or {},
            started_at=row.created_at,
        )
        return sess


async def delete_session(user_id: int, cartridge_id: str) -> None:
    """Delete a learning session from DB."""
    async with async_session() as db:
        stmt = select(LearningSession).where(
            LearningSession.user_id == user_id,
            LearningSession.cartridge_id == cartridge_id,
        )
        result = await db.execute(stmt)
        row = result.scalar_one_or_none()
        if row:
            await db.delete(row)
            await db.commit()


# ------------------------------------------------------------------
# Learner profile persistence
# ------------------------------------------------------------------

async def save_learner(learner: LearnerProfile) -> None:
    """Upsert a learner profile to DB."""
    async with async_session() as db:
        stmt = select(LearnerProfileModel).where(
            LearnerProfileModel.user_id == learner.user_id,
        )
        result = await db.execute(stmt)
        row = result.scalar_one_or_none()

        error_patterns_json = [
            {"error_type": p.error_type, "count": p.count,
             "last_seen_node": p.last_seen_node, "remediation": p.remediation}
            for p in learner.error_patterns
        ]

        if row is None:
            row = LearnerProfileModel(
                user_id=learner.user_id,
                knowledge_level=learner.knowledge_level,
                learning_speed=learner.learning_speed,
                confidence=learner.confidence,
                engagement=learner.engagement,
                cognitive_load=learner.cognitive_load,
                zpd_zone=learner.zpd_zone.value,
                bloom_level=learner.bloom_level,
                streak_days=learner.streak_days,
                total_xp=learner.total_xp,
                nodes_completed=learner.nodes_completed,
                error_patterns_json=error_patterns_json,
                history_json=learner.history,
            )
            db.add(row)
        else:
            row.knowledge_level = learner.knowledge_level
            row.learning_speed = learner.learning_speed
            row.confidence = learner.confidence
            row.engagement = learner.engagement
            row.cognitive_load = learner.cognitive_load
            row.zpd_zone = learner.zpd_zone.value
            row.bloom_level = learner.bloom_level
            row.streak_days = learner.streak_days
            row.total_xp = learner.total_xp
            row.nodes_completed = learner.nodes_completed
            row.error_patterns_json = error_patterns_json
            row.history_json = learner.history
            row.updated_at = datetime.utcnow()

        await db.commit()


async def load_learner(user_id: int) -> LearnerProfile | None:
    """Load a learner profile from DB."""
    async with async_session() as db:
        stmt = select(LearnerProfileModel).where(
            LearnerProfileModel.user_id == user_id,
        )
        result = await db.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None

        error_patterns = [
            ErrorPattern(
                error_type=p.get("error_type", ""),
                count=p.get("count", 0),
                last_seen_node=p.get("last_seen_node", ""),
                remediation=p.get("remediation", ""),
            )
            for p in (row.error_patterns_json or [])
        ]

        return LearnerProfile(
            user_id=row.user_id,
            knowledge_level=row.knowledge_level,
            learning_speed=row.learning_speed,
            confidence=row.confidence,
            engagement=row.engagement,
            cognitive_load=row.cognitive_load,
            zpd_zone=ZPDZone(row.zpd_zone),
            bloom_level=row.bloom_level,
            streak_days=row.streak_days,
            total_xp=row.total_xp,
            nodes_completed=row.nodes_completed,
            error_patterns=error_patterns,
            history=row.history_json or {},
        )


# ------------------------------------------------------------------
# Review card persistence
# ------------------------------------------------------------------

async def save_review_cards(user_id: int, cards: list[ReviewCard]) -> None:
    """Replace all review cards for a user in DB."""
    async with async_session() as db:
        # Delete existing cards for this user
        stmt = select(ReviewCardModel).where(ReviewCardModel.user_id == user_id)
        result = await db.execute(stmt)
        for row in result.scalars().all():
            await db.delete(row)

        # Insert new cards
        for card in cards:
            db.add(ReviewCardModel(
                user_id=user_id,
                node_id=card.node_id,
                cartridge_id=card.cartridge_id,
                interval=card.interval,
                ease_factor=card.ease_factor,
                repetition=card.repetition,
                last_review=card.last_review,
                next_review=card.next_review,
                title=card.title,
            ))

        await db.commit()


async def load_review_cards(user_id: int) -> list[ReviewCard]:
    """Load all review cards for a user from DB."""
    async with async_session() as db:
        stmt = select(ReviewCardModel).where(ReviewCardModel.user_id == user_id)
        result = await db.execute(stmt)
        rows = result.scalars().all()

        return [
            ReviewCard(
                node_id=row.node_id,
                cartridge_id=row.cartridge_id,
                interval=row.interval,
                ease_factor=row.ease_factor,
                repetition=row.repetition,
                last_review=row.last_review,
                next_review=row.next_review,
                title=row.title,
            )
            for row in rows
        ]
