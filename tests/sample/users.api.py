from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Query, Path, Depends, HTTPException, status
from fastapi.security import HTTPBearer

from tests.sample.models.users import (
    User, UserResponse, UserListResponse, CreateUserRequest, 
    UpdateUserRequest, UserRole, UserStatus
)

router = APIRouter(prefix="/users", tags=["users"])
security = HTTPBearer()


@router.get("/", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    role: Optional[UserRole] = Query(None, description="Filter by role"),
    status: Optional[UserStatus] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, min_length=2, max_length=100, description="Search query"),
    created_after: Optional[datetime] = Query(None, description="Created after timestamp"),
    token: str = Depends(security)
) -> UserListResponse:
    """List users with filtering and pagination"""
    # Mock implementation
    return UserListResponse(
        users=[],
        total=0,
        page=page,
        per_page=per_page,
        has_next=False,
        has_prev=False
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID = Path(..., description="User ID"),
    include_balance: bool = Query(False, description="Include account balance"),
    token: str = Depends(security)
) -> UserResponse:
    """Get user by ID"""
    # Mock implementation
    raise HTTPException(status_code=404, detail="User not found")


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: CreateUserRequest,
    send_welcome_email: bool = Query(True, description="Send welcome email"),
    token: str = Depends(security)
) -> UserResponse:
    """Create a new user"""
    # Mock implementation
    raise HTTPException(status_code=400, detail="User creation failed")


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_data: UpdateUserRequest,
    user_id: UUID,
    send_notification: bool = Query(False, description="Send update notification"),
    token: str = Depends(security)
) -> UserResponse:
    """Update user information"""
    # Mock implementation
    raise HTTPException(status_code=404, detail="User not found")


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID = Path(..., description="User ID"),
    hard_delete: bool = Query(False, description="Permanently delete user"),
    token: str = Depends(security)
) -> None:
    """Delete or deactivate user"""
    # Mock implementation
    pass


@router.post("/{user_id}/addresses", response_model=UserResponse)
async def add_user_address(
    address_data: dict,
    user_id: UUID = Path(..., description="User ID"),
    make_default: bool = Query(False, description="Make this the default address"),
    token: str = Depends(security)
) -> UserResponse:
    """Add address to user"""
    # Mock implementation
    raise HTTPException(status_code=404, detail="User not found")


@router.get("/search/by-email/{email}")
async def search_user_by_email(
    email: str = Path(..., description="Email address to search"),
    exact_match: bool = Query(True, description="Exact email match"),
    token: str = Depends(security)
) -> UserResponse:
    """Search user by email address"""
    # Mock implementation
    raise HTTPException(status_code=404, detail="User not found")
