from pydantic import BaseModel, Field
from typing import Optional

# --- Authentication Schemas ---

class Token(BaseModel):
    """Schema for JWT token response."""
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    """Schema for data contained within the JWT."""
    username: Optional[str] = None

# --- User Schemas ---

class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)

class UserResponse(UserBase):
    id: int

    class Config:
        from_attributes = True # Allows mapping ORM objects to Pydantic models

# --- Todo Schemas ---

class TodoBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    completed: bool = False

class TodoCreate(TodoBase):
    pass

class TodoUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    completed: Optional[bool] = None

class TodoResponse(TodoBase):
    id: int
    owner_id: int

    class Config:
        from_attributes = True