# REQUIRES: pytest, httpx, sqlalchemy[asyncio], aiosqlite

import pytest
import httpx
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from main import app
from database import Base, get_db
from config import settings
from models import User, Todo
from auth import get_password_hash

# --- Test Database Setup ---

# Use an in-memory SQLite database for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture(scope="session")
def anyio_backend():
    """Required for async fixtures in pytest."""
    return "asyncio"

@pytest.fixture(scope="session")
async def test_engine():
    """Creates the test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def test_db_session(test_engine):
    """Provides a transactional session for each test."""
    AsyncSessionLocal = sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with AsyncSessionLocal() as session:
        # Begin a transaction
        async with session.begin():
            yield session
            # Rollback the transaction after the test finishes
            await session.rollback()

@pytest.fixture
def override_get_db(test_db_session):
    """Overrides the application's get_db dependency to use the test session."""
    async def _override_get_db():
        yield test_db_session
    app.dependency_overrides[get_db] = _override_get_db

@pytest.fixture
async def client(override_get_db):
    """Provides an asynchronous test client."""
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        yield client

# --- Helper Functions ---

async def register_and_login(client: httpx.AsyncClient, username: str, password: str):
    """Registers a user and returns the access token."""
    await client.post("/auth/register", json={"username": username, "password": password})
    
    response = await client.post(
        "/auth/token",
        data={"username": username, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]

# --- Tests ---

@pytest.mark.asyncio
async def test_root(client: httpx.AsyncClient):
    response = await client.get("/")
    assert response.status_code == 200
    assert "Welcome to the Todo API" in response.json()["message"]

@pytest.mark.asyncio
async def test_register_and_login(client: httpx.AsyncClient):
    # 1. Registration
    response = await client.post(
        "/auth/register",
        json={"username": "testuser", "password": "testpassword"}
    )
    assert response.status_code == 201
    assert response.json()["username"] == "testuser"
    
    # 2. Login
    response = await client.post(
        "/auth/token",
        data={"username": "testuser", "password": "testpassword"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_todo_crud_flow(client: httpx.AsyncClient):
    # Setup: Register and get token
    token = await register_and_login(client, "cruduser", "crudpass")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create Todo
    todo_data = {"title": "Buy Milk", "description": "Need whole milk"}
    response = await client.post("/todos/", json=todo_data, headers=headers)
    assert response.status_code == 201
    created_todo = response.json()
    assert created_todo["title"] == "Buy Milk"
    assert created_todo["completed"] is False
    todo_id = created_todo["id"]

    # 2. Read Todos (List)
    response = await client.get("/todos/", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == todo_id

    # 3. Read Specific Todo
    response = await client.get(f"/todos/{todo_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["title"] == "Buy Milk"

    # 4. Update Todo
    update_data = {"title": "Buy Almond Milk", "completed": True}
    response = await client.put(f"/todos/{todo_id}", json=update_data, headers=headers)
    assert response.status_code == 200
    updated_todo = response.json()
    assert updated_todo["title"] == "Buy Almond Milk"
    assert updated_todo["completed"] is True

    # 5. Delete Todo
    response = await client.delete(f"/todos/{todo_id}", headers=headers)
    assert response.status_code == 204

    # 6. Verify Deletion
    response = await client.get(f"/todos/{todo_id}", headers=headers)
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_unauthorized_access(client: httpx.AsyncClient):
    # Attempt to access protected endpoint without token
    response = await client.get("/todos/")
    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"