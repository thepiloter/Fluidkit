from fastapi import Depends
from ..models import User

def get_current_user() -> User:
    return User(id=1, name="test")
