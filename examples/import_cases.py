# Absolute imports
from fastapi import FastAPI, APIRouter
# → ImportNode(module="fastapi", names=["FastAPI", "APIRouter"], is_relative=False)

from pydantic import BaseModel
# → ImportNode(module="pydantic", names=["BaseModel"], is_relative=False)

# Relative imports
from .models import User, Config  
# → ImportNode(module=".models", names=["User", "Config"], is_relative=True)

from ..shared.auth import get_current_user
# → ImportNode(module="..shared.auth", names=["get_current_user"], is_relative=True)

from ...utils import logger
# → ImportNode(module="...utils", names=["logger"], is_relative=True)

# Star imports  
from fastapi import *
# → ImportNode(module="fastapi", names=["*"], import_type=STAR_IMPORT, is_relative=False)

# Edge case - relative import without module
from . import something
# → ImportNode(module=".", names=["something"], is_relative=True)
