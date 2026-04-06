"""Round-trip persistence tests for sessions, learner profiles, and review cards."""
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from starlight.core.session import Session, Exchange
from starlight.core.learner import LearnerProfile, ErrorPattern, ZPDZone
from starlight.core.spaced_rep import ReviewCard, calculate_next_review
from starlight.models import Base
from starlight import database as db


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def setup_db(db_engine, monkeypatch):
    """Replace the module-level engine/session with an in-memory one."""
    from sqlalchemy.ext.asyncio import async_sessionmaker
    test_session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    monkeypatch.setattr(db, "engine", db_engine)
    monkeypatch.setattr(db, "async_session", test_session_factory)


# ------------------------------------------------------------------
# Session round-trip
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_save_and_load_session(setup_db):
    session = Session(user_id=1, cartridge_id="python-basics", current_node="N01")
    session.max_turns = 7
    session.add_exchange("system", "知识内容：变量")
    session.add_exchange("assistant", "什么是变量？")
    session.add_exchange("user", "盒子", metadata={"verdict": "CONTINUE"})
    session.turn_count = 1
    session.record_score("N01", 80)

    await db.save_session(session)

    loaded = await db.load_session(1, "python-basics")
    assert loaded is not None
    assert loaded.user_id == 1
    assert loaded.cartridge_id == "python-basics"
    assert loaded.current_node == "N01"
    assert loaded.turn_count == 1
    assert loaded.max_turns == 7
    assert len(loaded.conversation) == 3
    assert loaded.conversation[0].role == "system"
    assert loaded.conversation[2].metadata == {"verdict": "CONTINUE"}
    assert loaded.node_scores == {"N01": [80]}


@pytest.mark.asyncio
async def test_save_session_upsert(setup_db):
    session = Session(user_id=1, cartridge_id="python-basics", current_node="N01")
    session.add_exchange("user", "hello")
    await db.save_session(session)

    # Update
    session.current_node = "N02"
    session.turn_count = 3
    await db.save_session(session)

    loaded = await db.load_session(1, "python-basics")
    assert loaded.current_node == "N02"
    assert loaded.turn_count == 3


@pytest.mark.asyncio
async def test_load_session_not_found(setup_db):
    loaded = await db.load_session(999, "nonexistent")
    assert loaded is None


@pytest.mark.asyncio
async def test_delete_session(setup_db):
    session = Session(user_id=1, cartridge_id="python-basics", current_node="N01")
    await db.save_session(session)
    await db.delete_session(1, "python-basics")
    loaded = await db.load_session(1, "python-basics")
    assert loaded is None


# ------------------------------------------------------------------
# Learner profile round-trip
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_save_and_load_learner(setup_db):
    learner = LearnerProfile(
        user_id=1,
        knowledge_level=0.6,
        learning_speed=1.2,
        confidence=0.7,
        engagement=0.8,
        cognitive_load=0.4,
        zpd_zone=ZPDZone.ZPD,
        bloom_level=3,
        streak_days=5,
        total_xp=500,
        nodes_completed=10,
        error_patterns=[
            ErrorPattern(error_type="concept", count=3, last_seen_node="N05"),
            ErrorPattern(error_type="attention", count=1),
        ],
        history={"last_cartridge": "python-basics"},
    )

    await db.save_learner(learner)

    loaded = await db.load_learner(1)
    assert loaded is not None
    assert loaded.user_id == 1
    assert loaded.knowledge_level == 0.6
    assert loaded.learning_speed == 1.2
    assert loaded.confidence == 0.7
    assert loaded.zpd_zone == ZPDZone.ZPD
    assert loaded.bloom_level == 3
    assert loaded.streak_days == 5
    assert loaded.total_xp == 500
    assert loaded.nodes_completed == 10
    assert len(loaded.error_patterns) == 2
    assert loaded.error_patterns[0].error_type == "concept"
    assert loaded.error_patterns[0].count == 3
    assert loaded.history == {"last_cartridge": "python-basics"}


@pytest.mark.asyncio
async def test_save_learner_upsert(setup_db):
    learner = LearnerProfile(user_id=1, total_xp=100)
    await db.save_learner(learner)

    learner.total_xp = 200
    learner.confidence = 0.9
    await db.save_learner(learner)

    loaded = await db.load_learner(1)
    assert loaded.total_xp == 200
    assert loaded.confidence == 0.9


@pytest.mark.asyncio
async def test_load_learner_not_found(setup_db):
    loaded = await db.load_learner(999)
    assert loaded is None


# ------------------------------------------------------------------
# Review card round-trip
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_save_and_load_review_cards(setup_db):
    cards = [
        ReviewCard(node_id="N01", cartridge_id="python-basics", title="变量",
                   interval=6, ease_factor=2.8, repetition=2),
        ReviewCard(node_id="N02", cartridge_id="python-basics", title="类型",
                   interval=1, ease_factor=2.5, repetition=0),
    ]
    calculate_next_review(cards[0], quality=4)
    calculate_next_review(cards[1], quality=2)

    await db.save_review_cards(1, cards)

    loaded = await db.load_review_cards(1)
    assert len(loaded) == 2
    # Find by node_id (order not guaranteed)
    n01 = next(c for c in loaded if c.node_id == "N01")
    n02 = next(c for c in loaded if c.node_id == "N02")
    assert n01.title == "变量"
    assert n01.repetition == 3  # quality 4 >= 3, so repetition increments
    assert n01.last_review is not None
    assert n02.title == "类型"
    assert n02.repetition == 0  # quality 2 < 3, so reset


@pytest.mark.asyncio
async def test_save_review_cards_replaces(setup_db):
    """Saving cards replaces all existing cards for that user."""
    cards_v1 = [ReviewCard(node_id="N01", cartridge_id="py", title="V1")]
    await db.save_review_cards(1, cards_v1)

    cards_v2 = [
        ReviewCard(node_id="N02", cartridge_id="py", title="V2-A"),
        ReviewCard(node_id="N03", cartridge_id="py", title="V2-B"),
    ]
    await db.save_review_cards(1, cards_v2)

    loaded = await db.load_review_cards(1)
    assert len(loaded) == 2
    assert all(c.node_id != "N01" for c in loaded)


@pytest.mark.asyncio
async def test_load_review_cards_empty(setup_db):
    loaded = await db.load_review_cards(999)
    assert loaded == []
