from pydantic import BaseModel, Field
from typing import Optional
from core.ast_utils import interface

@interface
class User(BaseModel):
    id: int
    name: str = Field(..., description="User name")
    email: Optional[str] = None

@interface
class Product(BaseModel):
    name: str
    price: float
