import pytest
from starlight.core.progress import ProgressManager
from starlight.models import User, Cartridge, UserProgress

@pytest.mark.asyncio
async def test_start_cartridge(db_session):
    user = User(telegram_id="12345", name="test")
    cart = Cartridge(id="python-basics", title="Python", entry_node="N01")
    db_session.add_all([user, cart])
    await db_session.commit()

    mgr = ProgressManager(db_session)
    progress = await mgr.start_cartridge(user.id, "python-basics", entry_node="N01")
    assert progress.current_node == "N01"
    assert progress.status == "in_progress"

@pytest.mark.asyncio
async def test_advance_node(db_session):
    user = User(telegram_id="12345", name="test")
    cart = Cartridge(id="python-basics", title="Python", entry_node="N01")
    db_session.add_all([user, cart])
    await db_session.commit()

    progress = UserProgress(user_id=user.id, cartridge_id="python-basics", current_node="N01", status="in_progress")
    db_session.add(progress)
    await db_session.commit()

    mgr = ProgressManager(db_session)
    updated = await mgr.advance_node(user.id, "python-basics", "N02")
    assert updated.current_node == "N02"

@pytest.mark.asyncio
async def test_complete_cartridge(db_session):
    user = User(telegram_id="12345", name="test")
    cart = Cartridge(id="python-basics", title="Python", entry_node="N01")
    db_session.add_all([user, cart])
    await db_session.commit()

    progress = UserProgress(user_id=user.id, cartridge_id="python-basics", current_node="N03", status="in_progress")
    db_session.add(progress)
    await db_session.commit()

    mgr = ProgressManager(db_session)
    updated = await mgr.complete_cartridge(user.id, "python-basics")
    assert updated.status == "completed"
    assert updated.completed_at is not None

@pytest.mark.asyncio
async def test_get_progress_none(db_session):
    mgr = ProgressManager(db_session)
    result = await mgr.get_progress(999, "nonexistent")
    assert result is None

@pytest.mark.asyncio
async def test_get_progress_existing(db_session):
    user = User(telegram_id="12345", name="test")
    cart = Cartridge(id="python-basics", title="Python", entry_node="N01")
    db_session.add_all([user, cart])
    await db_session.commit()

    progress = UserProgress(user_id=user.id, cartridge_id="python-basics", current_node="N01", status="in_progress")
    db_session.add(progress)
    await db_session.commit()

    mgr = ProgressManager(db_session)
    result = await mgr.get_progress(user.id, "python-basics")
    assert result is not None
    assert result.current_node == "N01"

@pytest.mark.asyncio
async def test_advance_nonexistent_raises(db_session):
    mgr = ProgressManager(db_session)
    with pytest.raises(ValueError):
        await mgr.advance_node(999, "nonexistent", "N02")
