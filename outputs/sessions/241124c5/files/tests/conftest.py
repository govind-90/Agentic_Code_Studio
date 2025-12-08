import asyncio
import pytest
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.main import app
from app.database import Base, get_db
from app.config import settings
from httpx import AsyncClient

# Use an in-memory SQLite database for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Override settings for testing
settings.DATABASE_URL = TEST_DATABASE_URL
settings.SECRET_KEY = "test-secret"
settings.ACCESS_TOKEN_EXPIRE_MINUTES = 1

# Setup test engine and session
test_engine = create_async_engine(
    TEST_DATABASE_URL, 
    echo=False, 
    connect_args={"check_same_thread": False}
)

TestingSessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    """Provides a clean, isolated database session for each test."""
    async with test_engine.begin() as connection:
        # Bind the connection to the session
        async with TestingSessionLocal(bind=connection) as session:
            # Begin a transaction
            await connection.begin()
            try:
                yield session
            finally:
                # Rollback the transaction after the test finishes
                await connection.rollback()

@pytest.fixture(scope="session", autouse=True)
def event_loop():
    """Create an instance of the default event loop for the session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session", autouse=True)
async def setup_db():
    """Setup and teardown the database tables once per session."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture(scope="function")
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Fixture for the FastAPI test client."""
    # Override the dependency before yielding the client
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
        
    # Clean up overrides
    app.dependency_overrides.clear()

@pytest.fixture
async def authenticated_client(client: AsyncClient) -> tuple[AsyncClient, dict]:
    """Fixture that registers a user and returns an authenticated client."""
    
    # 1. Register user
    user_data = {"email": "testuser@example.com", "password": "testpassword"}
    await client.post("/users/", json=user_data)
    
    # 2. Login and get token
    login_data = {"username": user_data["email"], "password": user_data["password"]}
    response = await client.post("/users/token", data=login_data)
    token = response.json()["access_token"]
    
    # 3. Configure client headers
    client.headers["Authorization"] = f"Bearer {token}"
    
    return client, user_data