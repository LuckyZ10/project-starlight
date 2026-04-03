import pytest
from starlight.models import User, Cartridge, Node, UserProgress, Assessment, Contributor

@pytest.mark.asyncio
async def test_create_user(db_session):
    user = User(telegram_id="12345", name="test_user", plan="free")
    db_session.add(user)
    await db_session.commit()
    result = await db_session.get(User, user.id)
    assert result.name == "test_user"
    assert result.plan == "free"

@pytest.mark.asyncio
async def test_cartridge_with_nodes(db_session):
    cart = Cartridge(id="python-basics", title="Python 基础", version="1.0.0", language="zh-CN", entry_node="N01")
    node = Node(id="N01", cartridge_id="python-basics", title="变量", file_path="nodes/N01.md", difficulty=1, pass_criteria="能写赋值语句")
    db_session.add_all([cart, node])
    await db_session.commit()
    assert node.cartridge_id == "python-basics"

@pytest.mark.asyncio
async def test_user_progress(db_session):
    user = User(telegram_id="12345", name="test_user")
    db_session.add(user)
    await db_session.flush()
    progress = UserProgress(user_id=user.id, cartridge_id="python-basics", current_node="N02", status="in_progress")
    db_session.add(progress)
    await db_session.commit()
    assert progress.status == "in_progress"

@pytest.mark.asyncio
async def test_assessment_record(db_session):
    user = User(telegram_id="12345", name="test_user")
    db_session.add(user)
    await db_session.flush()
    assessment = Assessment(user_id=user.id, node_id="N01", cartridge_id="python-basics", verdict="PASS", score=85)
    db_session.add(assessment)
    await db_session.commit()
    assert assessment.verdict == "PASS"
    assert assessment.score == 85

@pytest.mark.asyncio
async def test_contributor(db_session):
    c = Contributor(name="张轶霖", github="LuckyZ10", location="中国", bio="探索者", quote="从零开始")
    db_session.add(c)
    await db_session.commit()
    assert c.name == "张轶霖"
    assert c.github == "LuckyZ10"
