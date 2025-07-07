from fastapi import FastAPI, Query, Path, Depends
from fastapi.staticfiles import StaticFiles
from typing import Optional, List
from .schema import UserStatus, Profile, User


# Sample app with various route types
app = FastAPI(
    title="Test API",
    docs_url="/admin/docs",  # Custom docs URL
    redoc_url="/admin/redoc", # Custom redoc URL
    openapi_url="/api/schema.json"  # Custom OpenAPI URL
)
    
# User-defined routes
@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Hello World"}
    
@app.get("/users/{user_id}")
async def get_user(
    user_id: int = Path(..., description="User ID"),
    include_profile: bool = Query(False, description="Include user profile")
) -> User:
    """Get user by ID"""
    profile = Profile(bio="Test bio") if include_profile else None
    return User(id=user_id, name="Test User", profile=profile)
    
@app.post("/users")
async def create_user(user: User) -> User:
    """Create new user"""
    return user
    
@app.get("/users")
async def list_users(
    status: Optional[UserStatus] = Query(None),
    limit: int = Query(10, ge=1, le=100)
) -> List[User]:
    """List users with filtering"""
    return []
    
# Multi-method route
@app.api_route("/admin/users", methods=["GET", "POST"])
async def admin_users():
    """Admin users endpoint"""
    return {"admin": True}
