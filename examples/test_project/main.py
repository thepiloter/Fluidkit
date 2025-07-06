from fastapi import FastAPI, Query, Depends
from pydantic import BaseModel
from .models import User, Product
from .shared.auth import get_current_user
import redis

app = FastAPI()

@app.get("/users/{user_id}")
async def get_user(user_id: int, q: str = Query(None)):
    return {"user_id": user_id}

@app.post("/users")
async def create_user(user: User, current_user = Depends(get_current_user)):
    return user
