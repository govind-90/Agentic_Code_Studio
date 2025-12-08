import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from . import models
from .database import engine
from .routers import users, todos

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_tables():
    """Creates all database tables defined in models.py."""
    try:
        models.Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully.")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles startup and shutdown events."""
    # Startup
    create_tables()
    logger.info("FastAPI application startup complete.")
    yield
    # Shutdown (No specific shutdown tasks needed for SQLite)
    logger.info("FastAPI application shutdown complete.")


app = FastAPI(
    title="FastAPI ToDo API with Auth",
    description="A simple REST API for managing ToDo items with JWT authentication.",
    version="1.0.0",
    lifespan=lifespan
)

# Include routers
app.include_router(users.router)
app.include_router(todos.router)

@app.get("/", tags=["Root"])
def read_root():
    return {"message": "Welcome to the ToDo API. Access /docs for documentation."}

if __name__ == "__main__":
    # This block is primarily for local development testing outside of Docker/Uvicorn CLI
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)