from typing import Optional
from enum import Enum
from pydantic import BaseModel

class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    
class Profile(BaseModel):
    bio: str
    website: Optional[str] = None
    
class User(BaseModel):
    id: int
    name: str
    status: UserStatus = UserStatus.ACTIVE
    profile: Optional[Profile] = None
