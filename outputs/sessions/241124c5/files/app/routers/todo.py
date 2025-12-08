from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app import crud, schemas, auth
from app.database import get_db
from app.models import User

router = APIRouter(
    prefix="/todos",
    tags=["Todos"],
    dependencies=[Depends(auth.get_current_user)] # All routes require authentication
)

@router.post("/", response_model=schemas.Todo, status_code=status.HTTP_201_CREATED)
async def create_todo_for_user(
    todo: schemas.TodoCreate,
    current_user: User = Depends(auth.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new todo item."""
    return await crud.create_user_todo(db=db, todo=todo, user_id=current_user.id)

@router.get("/", response_model=List[schemas.Todo])
async def read_todos(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(auth.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve a list of todos belonging to the current user."""
    todos = await crud.get_todos(db, user_id=current_user.id, skip=skip, limit=limit)
    return todos

@router.get("/{todo_id}", response_model=schemas.Todo)
async def read_todo(
    todo_id: int,
    current_user: User = Depends(auth.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve a specific todo item by ID."""
    db_todo = await crud.get_todo(db, todo_id=todo_id, user_id=current_user.id)
    if db_todo is None:
        raise HTTPException(status_code=404, detail="Todo not found or unauthorized")
    return db_todo

@router.put("/{todo_id}", response_model=schemas.Todo)
async def update_todo_item(
    todo_id: int,
    todo_update: schemas.TodoUpdate,
    current_user: User = Depends(auth.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update an existing todo item."""
    db_todo = await crud.get_todo(db, todo_id=todo_id, user_id=current_user.id)
    if db_todo is None:
        raise HTTPException(status_code=404, detail="Todo not found or unauthorized")
    
    return await crud.update_todo(db, db_todo=db_todo, todo_update=todo_update)

@router.delete("/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_todo_item(
    todo_id: int,
    current_user: User = Depends(auth.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a todo item."""
    success = await crud.delete_todo(db, todo_id=todo_id, user_id=current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Todo not found or unauthorized")
    return