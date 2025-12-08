from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from schemas import TodoCreate, Todo as TodoSchema, TodoUpdate
from crud import create_user_todo, get_todos, get_todo, update_todo, delete_todo
from auth import get_current_user
from models import User

router = APIRouter(prefix="/todos", tags=["Todos"])

@router.post("/", response_model=TodoSchema, status_code=status.HTTP_201_CREATED)
async def create_todo_for_current_user(
    todo: TodoCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Creates a new todo item for the authenticated user."""
    return await create_user_todo(db=db, todo=todo, user_id=current_user.id)

@router.get("/", response_model=List[TodoSchema])
async def read_todos(
    skip: int = 0, 
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieves all todos belonging to the authenticated user."""
    todos = await get_todos(db, user_id=current_user.id, skip=skip, limit=limit)
    return todos

@router.get("/{todo_id}", response_model=TodoSchema)
async def read_todo(
    todo_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieves a specific todo item by ID."""
    db_todo = await get_todo(db, todo_id=todo_id, user_id=current_user.id)
    if db_todo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found or unauthorized")
    return db_todo

@router.put("/{todo_id}", response_model=TodoSchema)
async def update_todo_item(
    todo_id: int,
    todo_update: TodoUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Updates an existing todo item."""
    db_todo = await get_todo(db, todo_id=todo_id, user_id=current_user.id)
    if db_todo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found or unauthorized")
    
    return await update_todo(db, db_todo=db_todo, todo_update=todo_update)

@router.delete("/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_todo_item(
    todo_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Deletes a specific todo item."""
    db_todo = await get_todo(db, todo_id=todo_id, user_id=current_user.id)
    if db_todo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found or unauthorized")
    
    await delete_todo(db, db_todo=db_todo)
    return