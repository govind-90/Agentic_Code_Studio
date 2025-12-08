import logging
from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.database import init_db
from app.routers import user, todo

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles startup and shutdown events.
    On startup, initialize the database.
    """
    logger.info("Application startup: Initializing database...")
    try:
        await init_db()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        # In a real application, this might be a critical failure
        # For now, we log and continue, assuming DB might be external
        
    yield
    
    # Shutdown events (if any)
    logger.info("Application shutdown.")

app = FastAPI(
    title="FastAPI Todo App",
    description="A simple Todo application with JWT authentication and SQLAlchemy.",
    version="1.0.0",
    lifespan=lifespan
)

# Include routers
app.include_router(user.router)
app.include_router(todo.router)

@app.get("/", tags=["Health Check"])
async def root():
    return {"message": "Welcome to the FastAPI Todo API. Check /docs for endpoints."}

# --- Unit Tests ---