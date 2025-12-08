from pydantic import BaseModel, Field
from typing import Optional

# --- User Schemas ---

class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)

class User(UserBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True

# --- Todo Schemas ---

class TodoBase(BaseModel):
    title: str = Field(..., min_length=1)
    description: Optional[str] = None

class TodoCreate(TodoBase):
    pass

class TodoUpdate(TodoBase):
    completed: Optional[bool] = None

class Todo(TodoBase):
    id: int
    completed: bool
    owner_id: int

    class Config:
        from_attributes = True

# --- Auth Schemas ---

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    username: Optional[str] = None