from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import schemas, models, auth
from ..database import get_db

router = APIRouter(
    prefix="/todos",
    tags=["ToDos"]
)

# Helper function to check ownership
def get_todo_or_404(db: Session, todo_id: int, owner_id: int) -> models.ToDo:
    """Fetches a ToDo item by ID, ensuring it belongs to the owner."""
    todo = db.query(models.ToDo).filter(
        models.ToDo.id == todo_id,
        models.ToDo.owner_id == owner_id
    ).first()
    
    if todo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ToDo item not found or access denied"
        )
    return todo

@router.post("/", response_model=schemas.ToDoResponse, status_code=status.HTTP_201_CREATED)
def create_todo(
    todo: schemas.ToDoCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Creates a new ToDo item for the authenticated user."""
    db_todo = models.ToDo(**todo.model_dump(), owner_id=current_user.id)
    
    db.add(db_todo)
    db.commit()
    db.refresh(db_todo)
    
    return db_todo

@router.get("/", response_model=List[schemas.ToDoResponse])
def read_todos(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Retrieves all ToDo items belonging to the authenticated user."""
    todos = db.query(models.ToDo).filter(models.ToDo.owner_id == current_user.id).all()
    return todos

@router.get("/{todo_id}", response_model=schemas.ToDoResponse)
def read_todo(
    todo_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Retrieves a specific ToDo item by ID."""
    return get_todo_or_404(db, todo_id, current_user.id)

@router.put("/{todo_id}", response_model=schemas.ToDoResponse)
def update_todo(
    todo_id: int,
    todo_update: schemas.ToDoUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Updates an existing ToDo item."""
    db_todo = get_todo_or_404(db, todo_id, current_user.id)
    
    # Update fields dynamically
    update_data = todo_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_todo, key, value)
        
    db.commit()
    db.refresh(db_todo)
    
    return db_todo

@router.delete("/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_todo(
    todo_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Deletes a specific ToDo item."""
    db_todo = get_todo_or_404(db, todo_id, current_user.id)
    
    db.delete(db_todo)
    db.commit()
    
    return