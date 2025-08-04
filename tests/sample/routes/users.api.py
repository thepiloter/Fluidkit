import json
import asyncio
from typing import List, Optional, AsyncGenerator
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from sse_starlette import EventSourceResponse
from starlette.responses import StreamingResponse

from ..models.users import (
    User, UserResponse, UserListResponse, CreateUserRequest, 
    UserRole, UserStatus
)

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=UserListResponse)
async def list_users(
    page: int = 1,
    per_page: int = 10,
    role: Optional[UserRole] = None,
    status: Optional[UserStatus] = None,
    search: Optional[str] = None
) -> UserListResponse:
    """List users with filtering and pagination"""
    return UserListResponse(
        users=[],
        total=0,
        page=page,
        has_next=False
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    include_balance: bool = False
) -> UserResponse:
    """Get user by ID"""
    raise HTTPException(status_code=404, detail="User not found")


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: CreateUserRequest,
    send_welcome_email: bool = True
) -> UserResponse:
    """Create a new user"""
    raise HTTPException(status_code=400, detail="User creation failed")


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    username: Optional[str] = None,
    email: Optional[str] = None,
    role: Optional[UserRole] = None,
    send_notification: bool = False
) -> UserResponse:
    """Update user information"""
    raise HTTPException(status_code=404, detail="User not found")


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    hard_delete: bool = False
) -> None:
    """Delete user"""
    pass


# === STREAMING ENDPOINTS === #

async def generate_user_events(user_id: UUID) -> AsyncGenerator[str, None]:
    """Generate user activity events"""
    events = [
        {"type": "login", "user_id": str(user_id), "timestamp": datetime.now().isoformat()},
        {"type": "profile_update", "user_id": str(user_id), "changes": ["email"]},
        {"type": "logout", "user_id": str(user_id), "session_duration": "45m"}
    ]
    
    for event in events:
        yield f"data: {json.dumps(event)}\n\n"
        await asyncio.sleep(1)


@router.get("/{user_id}/events")
async def stream_user_events(user_id: UUID) -> EventSourceResponse:
    """Stream real-time user activity events"""
    return EventSourceResponse(generate_user_events(user_id))


async def generate_user_analytics() -> AsyncGenerator[bytes, None]:
    """Generate streaming user analytics data"""
    for i in range(5):
        data = {
            "timestamp": datetime.now().isoformat(),
            "active_users": 100 + i,
            "new_registrations": 5 + i,
            "session_count": 250 + i * 10
        }
        yield f"{json.dumps(data)}\n".encode()
        await asyncio.sleep(0.5)


@router.get("/analytics/stream")
async def stream_user_analytics() -> StreamingResponse:
    """Stream user analytics data"""
    return StreamingResponse(
        generate_user_analytics(),
        media_type="application/x-ndjson"
    )


async def generate_users_csv() -> AsyncGenerator[bytes, None]:
    """Generate CSV export of users"""
    yield b"id,username,email,role,status\n"
    
    sample_users = [
        ("1", "john_doe", "john@example.com", "USER", "ACTIVE"),
        ("2", "jane_admin", "jane@example.com", "ADMIN", "ACTIVE"),
        ("3", "bob_user", "bob@example.com", "USER", "PENDING"),
    ]
    
    for user_data in sample_users:
        yield f"{','.join(user_data)}\n".encode()
        await asyncio.sleep(0.2)


@router.get("/export/csv")
async def export_users_csv() -> StreamingResponse:
    """Export users as CSV file"""
    return StreamingResponse(
        generate_users_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=users.csv"}
    )
