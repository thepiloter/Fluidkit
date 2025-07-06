# test_imports.py
import fastapi
import pydantic
from fastapi import APIRouter, Query, Path, Body, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Union
from .models import User, Session
from ..shared.auth import get_current_user
