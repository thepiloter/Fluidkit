from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Optional, List, Union
from uuid import UUID

from pydantic import BaseModel, Field, EmailStr, HttpUrl
from pydantic_extra_types.payment import PaymentCardNumber


class UserRole(str, Enum):
    """User role enumeration"""
    ADMIN = "admin"
    USER = "user" 
    MODERATOR = "moderator"


class UserStatus(str, Enum):
    """User account status"""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    PENDING = "pending"
    DELETED = "deleted"


class Address(BaseModel):
    """Address information"""
    street: str = Field(..., min_length=5, max_length=200)
    city: str = Field(..., min_length=2, max_length=100)
    state: Optional[str] = Field(None, max_length=50)
    postal_code: str = Field(..., pattern=r"^\d{5}(-\d{4})?$")
    country: str = Field(default="US", max_length=2)


class ContactInfo(BaseModel):
    """Contact information with external types"""
    primary_email: EmailStr
    backup_emails: List[EmailStr] = Field(default_factory=list)
    phone: Optional[str] = Field(None, pattern=r"^\+?1?\d{9,15}$")
    website: Optional[HttpUrl] = None


class PaymentMethod(BaseModel):
    """Payment method information"""
    id: UUID = Field(..., description="Payment method ID")
    card_number: PaymentCardNumber = Field(..., description="Encrypted card number")
    expiry_month: int = Field(..., ge=1, le=12)
    expiry_year: int = Field(..., ge=2024, le=2050)
    billing_address: Address
    is_default: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.now)


class UserPreferences(BaseModel):
    """User preferences and settings"""
    timezone: str = Field(default="UTC")
    language: str = Field(default="en", max_length=5)
    currency: str = Field(default="USD", max_length=3)
    newsletter_enabled: bool = Field(default=True)
    notifications_enabled: bool = Field(default=True)
    theme: str = Field(default="light", pattern=r"^(light|dark|auto)$")


class UserProfile(BaseModel):
    """Extended user profile information"""
    bio: Optional[str] = Field(None, max_length=500)
    avatar_url: Optional[HttpUrl] = None
    birth_date: Optional[date] = None
    location: Optional[str] = Field(None, max_length=100)
    social_links: List[HttpUrl] = Field(default_factory=list)
    interests: List[str] = Field(default_factory=list)
    profile_image_path: Optional[Path] = None


class User(BaseModel):
    """Main user model with complex relationships"""
    id: UUID = Field(..., description="Unique user identifier")
    username: str = Field(..., min_length=3, max_length=30, pattern=r"^[a-zA-Z0-9_]+$")
    email: EmailStr = Field(..., description="Primary email address")
    
    # Complex nested models
    contact_info: ContactInfo
    profile: Optional[UserProfile] = None
    addresses: List[Address] = Field(default_factory=list)
    payment_methods: List[PaymentMethod] = Field(default_factory=list)
    preferences: UserPreferences = Field(default_factory=UserPreferences)
    
    # Enums and status
    role: UserRole = Field(default=UserRole.USER)
    status: UserStatus = Field(default=UserStatus.PENDING)
    
    # Timestamps with external datetime
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    email_verified_at: Optional[datetime] = None
    
    # Metrics
    login_count: int = Field(default=0, ge=0)
    account_balance: Decimal = Field(default=Decimal("0.00"), max_digits=10, decimal_places=2)


class CreateUserRequest(BaseModel):
    """Request model for user creation"""
    username: str = Field(..., min_length=3, max_length=30)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    contact_info: ContactInfo
    profile: Optional[UserProfile] = None
    role: UserRole = Field(default=UserRole.USER)


class UpdateUserRequest(BaseModel):
    """Request model for user updates"""
    username: Optional[str] = Field(None, min_length=3, max_length=30)
    email: Optional[EmailStr] = None
    contact_info: Optional[ContactInfo] = None
    profile: Optional[UserProfile] = None
    preferences: Optional[UserPreferences] = None
    status: Optional[UserStatus] = None


class UserResponse(BaseModel):
    """Response model for user data (excluding sensitive info)"""
    id: UUID
    username: str
    email: EmailStr
    contact_info: ContactInfo
    profile: Optional[UserProfile]
    role: UserRole
    status: UserStatus
    created_at: datetime
    updated_at: Optional[datetime]
    last_login: Optional[datetime]
    login_count: int
    account_balance: Decimal


class UserListResponse(BaseModel):
    """Paginated user list response"""
    users: List[UserResponse]
    total: int = Field(..., ge=0)
    page: int = Field(..., ge=1)
    per_page: int = Field(..., ge=1, le=100)
    has_next: bool
    has_prev: bool
