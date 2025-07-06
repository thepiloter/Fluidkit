from pydantic import BaseModel, Field
from typing import Optional, List
from core.ast_utils import interface

@interface
class User(BaseModel):
    """User model with validation"""
    id: int
    name: str = Field(..., description="User's full name")
    email: Optional[str] = None
    age: int = Field(25, ge=18, le=100)
    tags: List[str] = []

@interface  
class CreateUserRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)
    email: str = Field(..., regex=r"^[\\w\\.-]+@[\\w\\.-]+\\.\\w+$")

# This should be ignored - no @interface
class NotAnInterface(BaseModel):
    data: str

@interface
class SimpleModel:
    """Simple model without BaseModel inheritance"""
    title: str = "default"
    count = 42  # No type annotation
