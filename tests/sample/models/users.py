from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, EmailStr


class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"
    MODERATOR = "moderator"


class UserStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    PENDING = "pending"


class Address(BaseModel):
    street: str
    city: str
    state: Optional[str] = None
    postal_code: str
    country: str = "US"


class ContactInfo(BaseModel):
    primary_email: EmailStr
    phone: Optional[str] = None


class User(BaseModel):
    id: UUID
    username: str
    email: EmailStr
    contact_info: ContactInfo
    addresses: List[Address] = []
    role: UserRole = UserRole.USER
    status: UserStatus = UserStatus.PENDING
    created_at: datetime
    updated_at: Optional[datetime] = None
    account_balance: Decimal = Decimal("0.00")


class CreateUserRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    contact_info: ContactInfo
    role: UserRole = UserRole.USER


class UserResponse(BaseModel):
    id: UUID
    username: str
    email: EmailStr
    contact_info: ContactInfo
    role: UserRole
    status: UserStatus
    created_at: datetime
    account_balance: Decimal


class UserListResponse(BaseModel):
    users: List[UserResponse]
    total: int
    page: int
    has_next: bool
