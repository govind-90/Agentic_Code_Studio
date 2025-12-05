# FILE: requirements.txt
# REQUIRES: fastapi, uvicorn, sqlalchemy, pydantic, pydantic-settings, python-jose, passlib, aiosqlite, httpx, pytest, python-multipart

fastapi==0.111.0
uvicorn[standard]==0.30.1
sqlalchemy==2.0.30
pydantic==2.7.1
pydantic-settings==2.2.1
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
aiosqlite==0.20.0
httpx==0.27.0
pytest==8.2.0
python-multipart==0.0.9

# FILE: app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # Database configuration
    DATABASE_URL: str = "sqlite+aiosqlite:///./sql_app.db"

    # JWT configuration
    SECRET_KEY: str = "09d25e094fa841a2986c87953f93863d" # Replace with a strong secret in production
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()

# FILE: app/database.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

# 1. Setup Engine
# Use create_async_engine for asynchronous database access
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)

# 2. Setup Session Maker
# Configure the session factory
AsyncSessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# 3. Base Class for Models
class Base(DeclarativeBase):
    """Base class which provides automated table name
    and default primary key column.
    """
    pass

# Dependency to get the database session
async def get_db() -> AsyncSession:
    """Provides a database session using a context manager."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# Function to initialize the database (create tables)
async def init_db():
    """Creates all tables defined in Base metadata."""
    async with engine.begin() as conn:
        # Import models here to ensure they are registered with Base metadata
        from app import models
        await conn.run_sync(Base.metadata.create_all)

# FILE: app/models.py
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationship to Todos
    todos: Mapped[list["Todo"]] = relationship("Todo", back_populates="owner")

class Todo(Base):
    __tablename__ = "todos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String, index=True)
    description: Mapped[str] = mapped_column(String)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Foreign Key relationship
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    # Relationship back to User
    owner: Mapped["User"] = relationship("User", back_populates="todos")

# FILE: app/schemas.py
from pydantic import BaseModel, Field
from typing import Optional

# --- User Schemas ---

class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)

class User(UserBase):
    id: int
    is_active: bool

    class ConfigDict:
        from_attributes = True

# --- Todo Schemas ---

class TodoBase(BaseModel):
    title: str = Field(..., max_length=100)
    description: Optional[str] = None
    completed: bool = False

class TodoCreate(TodoBase):
    pass

class TodoUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    completed: Optional[bool] = None

class Todo(TodoBase):
    id: int
    owner_id: int

    class ConfigDict:
        from_attributes = True

# --- Auth Schemas ---

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    username: Optional[str] = None

# FILE: app/security.py
from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings
from app.schemas import TokenData
from app.models import User
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme for token retrieval
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

# --- Password Utilities ---

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hashes a password."""
    return pwd_context.hash(password)

# --- JWT Utilities ---

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Creates a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

# --- Dependency Injection ---

async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    """Fetches a user by username."""
    result = await db.execute(select(User).where(User.username == username))
    return result.scalars().first()

async def get_current_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    token: Annotated[str, Depends(oauth2_scheme)]
) -> User:
    """Dependency to retrieve the current authenticated user from the JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode the JWT token
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception

    # Fetch user from DB
    user = await get_user_by_username(db, username=token_data.username)
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
        
    return user

# FILE: app/crud.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update
from typing import List, Optional

from app.models import User, Todo
from app.schemas import UserCreate, TodoCreate, TodoUpdate
from app.security import get_password_hash

# --- User CRUD ---

async def create_user(db: AsyncSession, user: UserCreate) -> User:
    """Creates a new user with a hashed password."""
    hashed_password = get_password_hash(user.password)
    db_user = User(username=user.username, hashed_password=hashed_password)
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

async def get_user_by_username_crud(db: AsyncSession, username: str) -> Optional[User]:
    """Fetches a user by username."""
    result = await db.execute(select(User).where(User.username == username))
    return result.scalars().first()

# --- Todo CRUD ---

async def create_user_todo(db: AsyncSession, todo: TodoCreate, user_id: int) -> Todo:
    """Creates a new todo item associated with a user."""
    db_todo = Todo(**todo.model_dump(), owner_id=user_id)
    db.add(db_todo)
    await db.commit()
    await db.refresh(db_todo)
    return db_todo

async def get_todos(db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100) -> List[Todo]:
    """Retrieves all todos for a specific user."""
    result = await db.execute(
        select(Todo)
        .where(Todo.owner_id == user_id)
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())

async def get_todo(db: AsyncSession, todo_id: int, user_id: int) -> Optional[Todo]:
    """Retrieves a specific todo item by ID and owner."""
    result = await db.execute(
        select(Todo)
        .where(Todo.id == todo_id, Todo.owner_id == user_id)
    )
    return result.scalars().first()

async def update_todo(db: AsyncSession, db_todo: Todo, todo_update: TodoUpdate) -> Todo:
    """Updates an existing todo item."""
    update_data = todo_update.model_dump(exclude_unset=True)
    
    if not update_data:
        return db_todo # Nothing to update

    # Apply updates to the model instance
    for key, value in update_data.items():
        setattr(db_todo, key, value)
    
    db.add(db_todo)
    await db.commit()
    await db.refresh(db_todo)
    return db_todo

async def delete_todo(db: AsyncSession, db_todo: Todo):
    """Deletes a todo item."""
    await db.delete(db_todo)
    await db.commit()
    return {"message": "Todo deleted successfully"}

# FILE: app/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta
from typing import Annotated

from app.schemas import UserCreate, User as UserSchema, Token
from app.database import get_db
from app import crud
from app.security import verify_password, create_access_token, get_user_by_username
from app.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/signup", response_model=UserSchema, status_code=status.HTTP_201_CREATED)
async def register_user(
    user: UserCreate, 
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """Registers a new user."""
    db_user = await get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    return await crud.create_user(db=db, user=user)

@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """Handles user login and returns a JWT access token."""
    user = await get_user_by_username(db, username=form_data.username)
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

# FILE: app/routers/todo.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated, List

from app.schemas import Todo as TodoSchema, TodoCreate, TodoUpdate
from app.database import get_db
from app import crud
from app.security import get_current_user
from app.models import User

router = APIRouter(prefix="/todos", tags=["Todos"])

@router.post("/", response_model=TodoSchema, status_code=status.HTTP_201_CREATED)
async def create_todo_for_user(
    todo: TodoCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """Creates a new todo item for the authenticated user."""
    return await crud.create_user_todo(db=db, todo=todo, user_id=current_user.id)

@router.get("/", response_model=List[TodoSchema])
async def read_todos(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = 0,
    limit: int = 100
):
    """Retrieves all todo items belonging to the authenticated user."""
    todos = await crud.get_todos(db, user_id=current_user.id, skip=skip, limit=limit)
    return todos

@router.get("/{todo_id}", response_model=TodoSchema)
async def read_todo(
    todo_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """Retrieves a specific todo item by ID."""
    db_todo = await crud.get_todo(db, todo_id=todo_id, user_id=current_user.id)
    if db_todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    return db_todo

@router.put("/{todo_id}", response_model=TodoSchema)
async def update_todo_item(
    todo_id: int,
    todo_update: TodoUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """Updates an existing todo item."""
    db_todo = await crud.get_todo(db, todo_id=todo_id, user_id=current_user.id)
    if db_todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    
    return await crud.update_todo(db, db_todo=db_todo, todo_update=todo_update)

@router.delete("/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_todo_item(
    todo_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """Deletes a specific todo item."""
    db_todo = await crud.get_todo(db, todo_id=todo_id, user_id=current_user.id)
    if db_todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    
    await crud.delete_todo(db, db_todo=db_todo)
    return

# FILE: app/main.py
import uvicorn
from fastapi import FastAPI, Depends
from contextlib import asynccontextmanager
import logging

from app.database import init_db
from app.routers import auth, todo

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles startup and shutdown events.
    Initializes the database connection and creates tables on startup.
    """
    logger.info("Application startup: Initializing database...")
    try:
        await init_db()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        # In a real application, you might want to exit here if DB is critical
        
    yield
    
    # Shutdown logic (if needed)
    logger.info("Application shutdown.")

app = FastAPI(
    title="FastAPI Todo App with JWT Auth",
    version="1.0.0",
    lifespan=lifespan
)

# Include Routers
app.include_router(auth.router)
app.include_router(todo.router)

@app.get("/")
async def root():
    return {"message": "Welcome to the Todo API. Use /docs for documentation."}

if __name__ == "__main__":
    # Ensure the application runs using the correct entry point
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

# FILE: tests/test_api.py
import pytest
import httpx
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete

# Import necessary components from the application
from app.main import app
from app.database import engine, Base, get_db, AsyncSessionLocal
from app.models import User, Todo
from app.security import get_password_hash

# Define the base URL for testing
BASE_URL = "http://test"

# --- Fixtures and Overrides ---

# 1. Setup Test Database
@pytest.fixture(scope="session", autouse=True)
def event_loop():
    """Create an instance of the default event loop for the session."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def setup_db():
    """Initializes and tears down the database for testing."""
    # Ensure tables are created
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Clean up tables after tests
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def db_session(setup_db):
    """Provides a clean, transactional database session for each test."""
    async with AsyncSessionLocal() as session:
        # Begin a transaction
        async with session.begin():
            # Override the dependency to use this session
            def override_get_db():
                yield session
            app.dependency_overrides[get_db] = override_get_db
            
            # Clean up data before test run
            await session.execute(delete(Todo))
            await session.execute(delete(User))
            await session.commit()
            
            yield session
            
            # Rollback the transaction to ensure isolation
            await session.rollback()

# 2. Setup Test Client
@pytest.fixture
async def client(db_session):
    """Provides an asynchronous test client."""
    async with httpx.AsyncClient(app=app, base_url=BASE_URL) as client:
        yield client

# 3. Helper Fixtures
@pytest.fixture
async def test_user_data():
    return {
        "username": "testuser",
        "password": "securepassword123"
    }

@pytest.fixture
async def registered_user(db_session: AsyncSession, test_user_data):
    """Creates and returns a registered user model."""
    hashed_password = get_password_hash(test_user_data["password"])
    user = User(username=test_user_data["username"], hashed_password=hashed_password)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user

@pytest.fixture
async def auth_token(client: httpx.AsyncClient, test_user_data, registered_user):
    """Logs in the registered user and returns the JWT token."""
    response = await client.post(
        "/auth/token",
        data={
            "username": test_user_data["username"],
            "password": test_user_data["password"],
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]

# --- Tests ---

@pytest.mark.asyncio
async def test_signup_and_login(client: httpx.AsyncClient, test_user_data):
    # 1. Signup
    signup_response = await client.post(
        "/auth/signup",
        json=test_user_data
    )
    assert signup_response.status_code == 201
    assert signup_response.json()["username"] == test_user_data["username"]
    
    # 2. Login (Get Token)
    login_response = await client.post(
        "/auth/token",
        data={
            "username": test_user_data["username"],
            "password": test_user_data["password"],
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert login_response.status_code == 200
    assert "access_token" in login_response.json()
    assert login_response.json()["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_create_read_update_delete_todo(client: httpx.AsyncClient, auth_token: str):
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    # 1. Create Todo
    todo_data = {"title": "Buy Milk", "description": "Whole milk, organic"}
    create_response = await client.post("/todos/", json=todo_data, headers=headers)
    assert create_response.status_code == 201
    created_todo = create_response.json()
    assert created_todo["title"] == "Buy Milk"
    assert created_todo["completed"] is False
    todo_id = created_todo["id"]

    # 2. Read Single Todo
    read_single_response = await client.get(f"/todos/{todo_id}", headers=headers)
    assert read_single_response.status_code == 200
    assert read_single_response.json()["title"] == "Buy Milk"

    # 3. Read All Todos
    read_all_response = await client.get("/todos/", headers=headers)
    assert read_all_response.status_code == 200
    assert len(read_all_response.json()) == 1
    assert read_all_response.json()[0]["id"] == todo_id

    # 4. Update Todo (Mark complete)
    update_data = {"completed": True, "description": "Milk bought and stored."}
    update_response = await client.put(f"/todos/{todo_id}", json=update_data, headers=headers)
    assert update_response.status_code == 200
    updated_todo = update_response.json()
    assert updated_todo["completed"] is True
    assert updated_todo["description"] == "Milk bought and stored."

    # 5. Delete Todo
    delete_response = await client.delete(f"/todos/{todo_id}", headers=headers)
    assert delete_response.status_code == 204

    # 6. Verify Deletion
    verify_delete_response = await client.get(f"/todos/{todo_id}", headers=headers)
    assert verify_delete_response.status_code == 404

@pytest.mark.asyncio
async def test_unauthorized_access(client: httpx.AsyncClient):
    # Attempt to access protected endpoint without token
    response = await client.get("/todos/")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"

# FILE: Dockerfile
# Use a lightweight Python base image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED 1
ENV APP_HOME /app
WORKDIR $APP_HOME

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app $APP_HOME/app

# Expose the port FastAPI runs on
EXPOSE 8000

# Command to run the application using Uvicorn
# Use gunicorn with uvicorn workers for production deployment
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# FILE: .github/workflows/ci.yml
name: Python CI/CD

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  build_and_test:
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Set up Python 3.11
      uses: actions/setup-python@v5
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt

    - name: Run tests with pytest
      # We use the tests/ directory structure defined in the project
      run: |
        pytest tests/test_api.py
        
    - name: Build Docker image (Optional, for verification)
      run: |
        docker build -t todo-fastapi-app .
        
    # Example of deployment step (e.g., push to Docker Hub/ECR)
    # - name: Log in to Docker Hub
    #   uses: docker/login-action@v3
    #   with:
    #     username: ${{ secrets.DOCKER_USERNAME }}
    #     password: ${{ secrets.DOCKER_PASSWORD }}
        
    # - name: Push Docker image
    #   run: |
    #     docker tag todo-fastapi-app:latest yourusername/todo-fastapi-app:latest
    #     docker push yourusername/todo-fastapi-app:latest
```