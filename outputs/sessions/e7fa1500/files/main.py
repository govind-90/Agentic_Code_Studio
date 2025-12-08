import os
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

# FastAPI and Dependencies
from fastapi import FastAPI, Depends, HTTPException, status, APIRouter
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

# SQLAlchemy
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, Session, relationship

# Security
from passlib.context import CryptContext
from jose import JWTError, jwt

# Pydantic
from pydantic import BaseModel, Field

# --- Configuration and Setup ---

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Database Configuration ---
# Use SQLite for simplicity. In production, use PostgreSQL or MySQL.
SQLALCHEMY_DATABASE_URL = "sqlite:///./todo_app.db"

# Create the SQLAlchemy engine
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# Create a configured "SessionLocal" class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for declarative class definitions
Base = declarative_base()

# Dependency to get the database session
def get_db():
    """Provides a database session and ensures it is closed after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Security Configuration ---
# Load secret key from environment variables or use a default (DANGER: Change this!)
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key-that-should-be-changed-in-prod")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

# --- 1. SQLAlchemy Models ---

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)

    todos = relationship("Todo", back_populates="owner")

class Todo(Base):
    __tablename__ = "todos"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    description = Column(String, index=True)
    completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    
    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="todos")

# --- 2. Pydantic Schemas ---

# --- User Schemas ---
class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)

class UserResponse(UserBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True

# --- Auth Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    username: Optional[str] = None

# --- Todo Schemas ---
class TodoBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None

class TodoCreate(TodoBase):
    pass

class TodoUpdate(TodoBase):
    completed: bool

class TodoResponse(TodoBase):
    id: int
    completed: bool
    owner_id: int
    created_at: datetime

    class Config:
        from_attributes = True

# --- 3. Security Utilities ---

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hashes a password."""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Creates a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- 4. Authentication Dependency ---

def get_user_by_username(db: Session, username: str):
    """Fetches a user by username."""
    return db.query(User).filter(User.username == username).first()

async def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> User:
    """
    Decodes the JWT token and fetches the corresponding active user.
    Raises HTTPException if token is invalid or user is not found/active.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError as e:
        logger.error(f"JWT Error: {e}")
        raise credentials_exception
    
    user = get_user_by_username(db, username=token_data.username)
    if user is None or not user.is_active:
        raise credentials_exception
    
    return user

# --- 5. Routers ---

# --- Authentication Router ---
auth_router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)

@auth_router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    """Registers a new user."""
    db_user = get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")
    
    hashed_password = get_password_hash(user.password)
    
    db_user = User(
        username=user.username,
        hashed_password=hashed_password
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    logger.info(f"User registered: {db_user.username}")
    return db_user

@auth_router.post("/token", response_model=Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Handles user login and returns an access token."""
    user = get_user_by_username(db, username=form_data.username)
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    logger.info(f"User logged in: {user.username}")
    return {"access_token": access_token, "token_type": "bearer"}

@auth_router.get("/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_user)):
    """Returns the details of the currently authenticated user."""
    return current_user

# --- Todo Router ---
todo_router = APIRouter(
    prefix="/todos",
    tags=["Todos"],
    dependencies=[Depends(get_current_user)] # All routes here require authentication
)

@todo_router.post("/", response_model=TodoResponse, status_code=status.HTTP_201_CREATED)
def create_todo(
    todo: TodoCreate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """Creates a new todo item for the authenticated user."""
    db_todo = Todo(
        **todo.model_dump(),
        owner_id=current_user.id
    )
    db.add(db_todo)
    db.commit()
    db.refresh(db_todo)
    logger.info(f"Todo created by user {current_user.id}: {db_todo.title}")
    return db_todo

@todo_router.get("/", response_model=List[TodoResponse])
def read_todos(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """Retrieves all todo items belonging to the authenticated user."""
    todos = db.query(Todo).filter(Todo.owner_id == current_user.id).offset(skip).limit(limit).all()
    return todos

@todo_router.get("/{todo_id}", response_model=TodoResponse)
def read_todo(
    todo_id: int, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """Retrieves a specific todo item by ID, ensuring ownership."""
    db_todo = db.query(Todo).filter(Todo.id == todo_id, Todo.owner_id == current_user.id).first()
    if db_todo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found or unauthorized")
    return db_todo

@todo_router.put("/{todo_id}", response_model=TodoResponse)
def update_todo(
    todo_id: int, 
    todo_update: TodoUpdate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """Updates an existing todo item, ensuring ownership."""
    db_todo = db.query(Todo).filter(Todo.id == todo_id, Todo.owner_id == current_user.id).first()
    
    if db_todo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found or unauthorized")

    # Update fields
    db_todo.title = todo_update.title
    db_todo.description = todo_update.description
    db_todo.completed = todo_update.completed
    
    db.commit()
    db.refresh(db_todo)
    logger.info(f"Todo updated: ID {todo_id} by user {current_user.id}")
    return db_todo

@todo_router.delete("/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_todo(
    todo_id: int, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """Deletes a todo item, ensuring ownership."""
    db_todo = db.query(Todo).filter(Todo.id == todo_id, Todo.owner_id == current_user.id).first()
    
    if db_todo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found or unauthorized")
    
    db.delete(db_todo)
    db.commit()
    logger.warning(f"Todo deleted: ID {todo_id} by user {current_user.id}")
    return

# --- 6. Main Application Setup ---

app = FastAPI(
    title="FastAPI Todo API with JWT Auth",
    description="A robust Todo list application using FastAPI, SQLAlchemy, and JWT.",
    version="1.0.0"
)

@app.on_event("startup")
def on_startup():
    """Creates database tables if they don't exist."""
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database setup complete.")

# Include routers
app.include_router(auth_router)
app.include_router(todo_router)

@app.get("/", tags=["Health Check"])
def read_root():
    return {"message": "Welcome to the Todo API. Check /docs for endpoints."}

if __name__ == "__main__":
    import uvicorn
    # Note: When running via Docker, the host will be '0.0.0.0'
    uvicorn.run(app, host="0.0.0.0", port=8000)

# --- Docker Support Files ---