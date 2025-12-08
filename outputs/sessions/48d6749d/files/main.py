import logging
from typing import List

from fastapi import FastAPI, Depends, HTTPException, status, APIRouter
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from . import models, schemas, auth
from .database import engine, get_db, Base

# --- Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_db_tables():
    """Initializes the database tables."""
    try:
        # This is suitable for small SQLite applications. For production, use Alembic migrations.
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully.")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")

app = FastAPI(
    title="FastAPI Authenticated Todo API",
    description="A simple Todo list API with JWT authentication and SQLAlchemy.",
    version="1.0.0"
)

# --- Routers Setup ---
router_auth = APIRouter(prefix="/auth", tags=["Authentication"])
router_todos = APIRouter(prefix="/todos", tags=["Todos"])

# --- Startup Event ---
@app.on_event("startup")
async def startup_event():
    create_db_tables()

# =============================================================================
# 1. Authentication Router (User Registration and Login)
# =============================================================================

@router_auth.post("/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """Registers a new user."""
    db_user = auth.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")
    
    hashed_password = auth.get_password_hash(user.password)
    
    db_user = models.User(
        username=user.username,
        hashed_password=hashed_password
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    logger.info(f"User registered: {user.username}")
    return db_user

@router_auth.post("/token", response_model=schemas.Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(get_db)
):
    """Handles user login and returns a JWT access token."""
    user = auth.get_user_by_username(db, username=form_data.username)
    
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token = auth.create_access_token(
        data={"sub": user.username}
    )
    logger.info(f"User logged in: {user.username}")
    return {"access_token": access_token, "token_type": "bearer"}

# =============================================================================
# 2. Todo Router (CRUD Operations)
# =============================================================================

@router_todos.post("/", response_model=schemas.TodoResponse, status_code=status.HTTP_201_CREATED)
def create_todo(
    todo: schemas.TodoCreate, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(auth.get_current_user)
):
    """Creates a new Todo item for the authenticated user."""
    db_todo = models.Todo(
        **todo.model_dump(), 
        owner_id=current_user.id
    )
    db.add(db_todo)
    db.commit()
    db.refresh(db_todo)
    logger.info(f"Todo created by user {current_user.id}: {db_todo.title}")
    return db_todo

@router_todos.get("/", response_model=List[schemas.TodoResponse])
def read_todos(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(auth.get_current_user)
):
    """Retrieves all Todo items belonging to the authenticated user."""
    todos = db.query(models.Todo).filter(models.Todo.owner_id == current_user.id).offset(skip).limit(limit).all()
    return todos

@router_todos.get("/{todo_id}", response_model=schemas.TodoResponse)
def read_todo(
    todo_id: int, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(auth.get_current_user)
):
    """Retrieves a specific Todo item by ID."""
    db_todo = db.query(models.Todo).filter(
        models.Todo.id == todo_id, 
        models.Todo.owner_id == current_user.id
    ).first()
    
    if db_todo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found or access denied")
        
    return db_todo

@router_todos.put("/{todo_id}", response_model=schemas.TodoResponse)
def update_todo(
    todo_id: int, 
    todo_update: schemas.TodoUpdate, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(auth.get_current_user)
):
    """Updates an existing Todo item."""
    db_todo = db.query(models.Todo).filter(
        models.Todo.id == todo_id, 
        models.Todo.owner_id == current_user.id
    ).first()
    
    if db_todo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found or access denied")

    # Use exclude_unset=True to only update fields provided in the request body
    update_data = todo_update.model_dump(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(db_todo, key, value)
        
    db.add(db_todo)
    db.commit()
    db.refresh(db_todo)
    logger.info(f"Todo updated: ID {todo_id} by user {current_user.id}")
    return db_todo

@router_todos.delete("/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_todo(
    todo_id: int, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(auth.get_current_user)
):
    """Deletes a Todo item."""
    db_todo = db.query(models.Todo).filter(
        models.Todo.id == todo_id, 
        models.Todo.owner_id == current_user.id
    ).first()
    
    if db_todo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found or access denied")
        
    db.delete(db_todo)
    db.commit()
    logger.info(f"Todo deleted: ID {todo_id} by user {current_user.id}")
    return 

# --- Include Routers in App ---
app.include_router(router_auth)
app.include_router(router_todos)

# --- Execution Block (for local testing) ---
if __name__ == "__main__":
    import uvicorn
    # Ensure tables are created if running locally without Docker startup event
    create_db_tables() 
    uvicorn.run(app, host="0.0.0.0", port=8000)