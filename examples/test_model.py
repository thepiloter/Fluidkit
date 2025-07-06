from enum import Enum
from typing import Optional, List, Dict, Union
from pydantic import BaseModel, Field
from core.ast_utils import interface
from fastapi import FastAPI

app = FastAPI()


@interface
class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    BANNED = "banned"

@interface
class Priority(int, Enum):
    LOW = 1
    HIGH = 2

@interface
class User(BaseModel):
    priority: Priority = Priority.LOW
    field2: Optional[UserStatus] = UserStatus.ACTIVE


@interface
class CompleteTest(BaseModel):
    """Complete test interface"""
    name: str = Field("aswanth", description="The user's name")
    data: Dict[str, List[Optional[Union[str, int]]]]
    result: Optional[Union[str, int, None]] = None

@interface
class Manager(BaseModel):
    name: str = "aswanth"

@app.post("/users")
async def create_user(user_data: CompleteTest, status: UserStatus = UserStatus.ACTIVE, priority: Priority = Priority.LOW):
    return {"success": True}
