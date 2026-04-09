"""Tests for the FastAPI web backend (auth, cartridges, learning endpoints)."""
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# We need to override the DB before importing the app
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web" / "backend"))

# Patch database module to use in-memory DB before app imports complete
import database as db_mod
from models import Base

test_engine = create_async_engine("sqlite+aiosqlite:///:memory:")
TestSession = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

# Override get_db
async def _override_get_db():
    async with TestSession() as session:
        yield session

db_mod.engine = test_engine
db_mod.async_session = TestSession


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    from main import app
    from database import get_db

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# ---- Health ----

@pytest.mark.asyncio
async def test_health(client):
    r = await client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


# ---- Auth ----

@pytest.mark.asyncio
async def test_register_and_login(client):
    # Register
    r = await client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "secret123",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["email"] == "test@example.com"
    assert "token" in data
    assert "id" in data
    token = data["token"]

    # Duplicate registration
    r2 = await client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "secret123",
    })
    assert r2.status_code == 409

    # Login
    r3 = await client.post("/api/auth/login", json={
        "email": "test@example.com",
        "password": "secret123",
    })
    assert r3.status_code == 200
    assert r3.json()["token"]

    # Wrong password
    r4 = await client.post("/api/auth/login", json={
        "email": "test@example.com",
        "password": "wrong",
    })
    assert r4.status_code == 401

    # /me
    r5 = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r5.status_code == 200
    assert r5.json()["email"] == "test@example.com"

    # /me without token
    r6 = await client.get("/api/auth/me")
    assert r6.status_code == 401


# ---- Cartridges ----

@pytest.mark.asyncio
async def test_list_cartridges(client):
    r = await client.get("/api/cartridges")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_get_cartridge_not_found(client):
    r = await client.get("/api/cartridges/nonexistent-cartridge-xyz")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_get_node_not_found(client):
    r = await client.get("/api/cartridges/nonexistent/nodes/N99")
    assert r.status_code == 404


# ---- Learning (auth required) ----

async def _register(client):
    r = await client.post("/api/auth/register", json={
        "email": "learner@example.com", "password": "pass123",
    })
    return r.json()["token"]


@pytest.mark.asyncio
async def test_submit_answer(client):
    token = await _register(client)
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.post("/api/learning/answer", headers=headers, json={
        "cartridge_id": "test-cart",
        "node_id": "N01",
        "question_type": "single_choice",
        "user_answer": "A",
        "correct_answer": "A",
        "correct": True,
    })
    assert r.status_code == 200
    assert r.json()["correct"] is True


@pytest.mark.asyncio
async def test_complete_node(client):
    token = await _register(client)
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.post("/api/learning/complete", headers=headers, json={
        "cartridge_id": "test-cart",
        "node_id": "N01",
        "score": 90,
    })
    assert r.status_code == 200
    assert r.json()["status"] == "completed"
    assert r.json()["score"] == 90


@pytest.mark.asyncio
async def test_get_progress(client):
    token = await _register(client)
    headers = {"Authorization": f"Bearer {token}"}

    # Complete a node first
    await client.post("/api/learning/complete", headers=headers, json={
        "cartridge_id": "test-cart", "node_id": "N01", "score": 80,
    })

    r = await client.get("/api/learning/progress/test-cart", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert "N01" in data
    assert data["N01"]["status"] == "completed"
    assert data["N01"]["score"] == 80


@pytest.mark.asyncio
async def test_learning_stats(client):
    token = await _register(client)
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.get("/api/learning/stats", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert "total_nodes" in data
    assert "completed_nodes" in data
    assert "accuracy" in data


@pytest.mark.asyncio
async def test_unauth_learning_endpoints(client):
    """All learning endpoints require auth."""
    r1 = await client.post("/api/learning/answer", json={
        "cartridge_id": "c", "node_id": "N01", "question_type": "single_choice",
        "user_answer": "A", "correct_answer": "A", "correct": True,
    })
    assert r1.status_code == 401

    r2 = await client.post("/api/learning/complete", json={
        "cartridge_id": "c", "node_id": "N01", "score": 100,
    })
    assert r2.status_code == 401

    r3 = await client.get("/api/learning/progress/c")
    assert r3.status_code == 401

    r4 = await client.get("/api/learning/stats")
    assert r4.status_code == 401
