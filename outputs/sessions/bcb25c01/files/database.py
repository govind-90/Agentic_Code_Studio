from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from typing import Generator

# Configuration
SQLALCHEMY_DATABASE_URL = "sqlite:///./todo_app.db"

# Create the SQLAlchemy engine
# connect_args={"check_same_thread": False} is needed for SQLite when using multiple threads (FastAPI default)
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# Create a configured "Session" class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for declarative class definitions
Base = declarative_base()

def get_db() -> Generator:
    """
    Dependency function that yields a database session.
    Ensures the session is closed after the request is finished.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()