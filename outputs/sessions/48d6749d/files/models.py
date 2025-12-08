from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base

class User(Base):
    """SQLAlchemy model for Users."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    # Relationship to Todos
    todos = relationship("Todo", back_populates="owner", cascade="all, delete-orphan")

class Todo(Base):
    """SQLAlchemy model for Todo items."""
    __tablename__ = "todos"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    description = Column(String, default="")
    completed = Column(Boolean, default=False)
    
    # Foreign key linking Todo to its owner (User)
    owner_id = Column(Integer, ForeignKey("users.id"))

    # Relationship to User
    owner = relationship("User", back_populates="todos")