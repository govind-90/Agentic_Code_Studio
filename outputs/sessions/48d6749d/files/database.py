import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from typing import Generator

# Define the database URL. Uses SQLite for simplicity.
# The path is relative to the container's working directory (/app).
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./todo_app.db")

# Create the SQLAlchemy Engine
# connect_args is needed for SQLite to allow multiple threads to access the database
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# Create a configured "SessionLocal" class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for declarative class definitions
Base = declarative_base()

# Dependency to get the database session
def get_db() -> Generator:
    """
    Provides a database session and ensures it is closed after the request is finished.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()