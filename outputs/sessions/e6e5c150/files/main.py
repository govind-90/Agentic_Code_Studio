import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from database import init_db
from routers import auth, todos

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles startup and shutdown events."""
    logger.info("Application startup: Initializing database...")
    try:
        await init_db()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        # In a real application, this might be a fatal error requiring restart
        
    yield
    
    # Shutdown events (if any)
    logger.info("Application shutdown.")

app = FastAPI(
    title="FastAPI Todo App with JWT Auth",
    description="A simple REST API for managing todos with user authentication.",
    version="1.0.0",
    lifespan=lifespan
)

# Include routers
app.include_router(auth.router)
app.include_router(todos.router)

@app.get("/", tags=["Health"])
async def root():
    return {"message": "Welcome to the Todo API. Check /docs for endpoints."}

if __name__ == "__main__":
    import uvicorn
    # Note: When running via Docker or standard deployment, uvicorn is usually run directly
    # from the command line, not via this block. This is for local development convenience.
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)