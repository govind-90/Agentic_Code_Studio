from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base

class User(Base):
    """SQLAlchemy model for Users."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    todos = relationship("ToDo", back_populates="owner")

class ToDo(Base):
    """SQLAlchemy model for ToDo items."""
    __tablename__ = "todos"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    description = Column(String, default="")
    completed = Column(Boolean, default=False)
    
    # Foreign key linking ToDo to User
    owner_id = Column(Integer, ForeignKey("users.id"))
    
    owner = relationship("User", back_populates="todos")