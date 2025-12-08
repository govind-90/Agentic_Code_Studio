from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List, Optional

from app.models import User, Todo
from app.schemas import UserCreate, TodoCreate, TodoUpdate
from app.auth import get_password_hash

# --- User CRUD ---

async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Retrieves a user by email."""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalars().first()

async def create_user(db: AsyncSession, user: UserCreate) -> User:
    """Creates a new user."""
    hashed_password = get_password_hash(user.password)
    db_user = User(email=user.email, hashed_password=hashed_password)
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

# --- Todo CRUD ---

async def create_user_todo(db: AsyncSession, todo: TodoCreate, user_id: int) -> Todo:
    """Creates a new todo item for a specific user."""
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
    """Retrieves a single todo item by ID, ensuring ownership."""
    result = await db.execute(
        select(Todo)
        .where(Todo.id == todo_id, Todo.owner_id == user_id)
    )
    return result.scalars().first()

async def update_todo(db: AsyncSession, db_todo: Todo, todo_update: TodoUpdate) -> Todo:
    """Updates an existing todo item."""
    update_data = todo_update.model_dump(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(db_todo, key, value)
        
    db.add(db_todo)
    await db.commit()
    await db.refresh(db_todo)
    return db_todo

async def delete_todo(db: AsyncSession, todo_id: int, user_id: int) -> bool:
    """Deletes a todo item by ID, ensuring ownership."""
    result = await db.execute(
        delete(Todo)
        .where(Todo.id == todo_id, Todo.owner_id == user_id)
    )
    await db.commit()
    return result.rowcount > 0