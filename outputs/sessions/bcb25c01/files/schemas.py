from pydantic import BaseModel, Field
from typing import Optional

# --- User Schemas ---

class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)

class UserResponse(UserBase):
    id: int

    class Config:
        from_attributes = True # Enable ORM mode

# --- ToDo Schemas ---

class ToDoBase(BaseModel):
    title: str = Field(..., min_length=1)
    description: Optional[str] = None
    completed: bool = False

class ToDoCreate(ToDoBase):
    pass

class ToDoUpdate(ToDoBase):
    # Allow partial updates
    title: Optional[str] = None
    description: Optional[str] = None
    completed: Optional[bool] = None

class ToDoResponse(ToDoBase):
    id: int
    owner_id: int

    class Config:
        from_attributes = True

# --- Auth Schemas ---

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None