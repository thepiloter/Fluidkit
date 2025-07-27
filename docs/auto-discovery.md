# Auto-Discovery

FluidKit automatically discovers and binds APIRouters using SvelteKit-style folder conventions, enabling intuitive file-based routing for FastAPI.

## File Naming Patterns

Auto-discovery scans for Python files matching configurable patterns:

### Underscore Pattern
```
_api.py       # API routes
_routes.py    # Route handlers  
_handlers.py  # Request handlers
```

### Dot Pattern
```
user.api.py         # User API
admin.routes.py     # Admin routes
data.service.py     # Data service
auth.middleware.py  # Auth middleware
```

### Configuration
```json
{
  "autoDiscovery": {
    "enabled": true,
    "filePatterns": ["_*.py", "*.*.py"]
  }
}
```

## Folder-to-Route Mapping

FluidKit translates folder structures to FastAPI route patterns:

### Basic Routes

```
src/routes/users/_api.py              → /users/*
src/routes/products/catalog.api.py    → /products/*  
src/routes/auth/login.routes.py       → /auth/*
```

### Dynamic Parameters

```
src/routes/users/[id]/profile.api.py       → /users/{id}/*
src/routes/posts/[slug]/comments.api.py    → /posts/{slug}/*
src/routes/shop/[category]/items.api.py    → /shop/{category}/*
```

### Rest Parameters

```
src/routes/files/[...path]/handler.api.py  → /files/{path:path}/*
src/routes/docs/[...slug]/content.api.py   → /docs/{slug:path}/*
```

### Route Groups (Ignored in URLs)

```
src/routes/(admin)/users/manage.api.py     → /users/*
src/routes/(app)/dashboard/stats.api.py    → /dashboard/*
src/routes/(auth)/login/verify.api.py      → /login/*
```

Route groups organize code without affecting URL structure.

## Parameter Validation

FluidKit validates that function signatures match folder parameters:

### ✅ Valid Examples

```python
# src/routes/users/[id]/profile.api.py
@router.get("/details")
async def get_profile(id: int):  # ✅ 'id' parameter present
    return {"user_id": id}

@router.post("/update")
async def update_profile(id: int, data: ProfileData):  # ✅ 'id' included
    return update_user_profile(id, data)
```

```python
# src/routes/files/[...path]/handler.api.py  
@router.get("/download")
async def download_file(path: str):  # ✅ 'path' parameter present
    return serve_file(path)
```

### ❌ Invalid Examples

```python
# src/routes/users/[id]/profile.api.py
@router.get("/details") 
async def get_profile():  # ❌ Missing required 'id' parameter
    return {"error": "Missing user ID"}

@router.post("/update")
async def update_profile(data: ProfileData):  # ❌ Missing 'id' parameter
    return {"error": "Cannot update without user ID"}
```

**FluidKit will raise validation errors** during startup for missing parameters.

## Complete Examples

### E-commerce API Structure

```
src/routes/
├── products/
│   ├── catalog.api.py              # /products/* 
│   ├── [id]/
│   │   ├── details.api.py          # /products/{id}/*
│   │   └── reviews.api.py          # /products/{id}/*  
│   └── [category]/
│       └── items.api.py            # /products/{category}/*
├── users/
│   ├── _api.py                     # /users/*
│   └── [id]/
│       ├── profile.api.py          # /users/{id}/*
│       └── orders.api.py           # /users/{id}/*
├── orders/
│   ├── _api.py                     # /orders/*
│   └── [id]/
│       └── tracking.api.py         # /orders/{id}/*
└── (admin)/
    ├── products/
    │   └── manage.api.py           # /products/* (admin group)
    └── users/
        └── moderate.api.py         # /users/* (admin group)
```

### API Implementation

```python
# src/routes/products/[id]/details.api.py
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class ProductDetails(BaseModel):
    id: int
    name: str
    description: str
    price: float

@router.get("/")
async def get_product(id: int) -> ProductDetails:
    """Get product details by ID"""
    return fetch_product_from_db(id)

@router.get("/specifications") 
async def get_specifications(id: int) -> dict:
    """Get product specifications"""
    return fetch_product_specs(id)

@router.get("/availability")
async def check_availability(id: int, location: str = "US") -> dict:
    """Check product availability"""
    return check_stock(id, location)
```

### Generated Client Usage

```typescript
// Auto-generated from folder structure
import { 
  get_product, 
  get_specifications, 
  check_availability 
} from './products/[id]/details.api';

// Type-safe usage
const product = await get_product(123);
const specs = await get_specifications(123);
const stock = await check_availability(123, "US");
```

## Scan Configuration

### Include/Exclude Patterns

```json
{
  "include": [
    "src/**/*.py",
    "lib/**/*.py",
    "modules/**/*.py"
  ],
  "exclude": [
    "**/__pycache__/**",
    "**/*.test.py",
    "**/*.spec.py",
    "**/migrations/**"
  ]
}
```

### Multiple File Patterns

```json
{
  "autoDiscovery": {
    "enabled": true,
    "filePatterns": [
      "_*.py",           # _api.py, _routes.py
      "*.api.py",        # user.api.py, admin.api.py
      "*.service.py",    # data.service.py, auth.service.py
      "*.handlers.py"    # event.handlers.py
    ]
  }
}
```

## Router Requirements

Auto-discovered files must export an `APIRouter` instance:

```python
# ✅ Valid - exports 'router'
from fastapi import APIRouter

router = APIRouter(prefix="/users")

@router.get("/")
async def list_users():
    return []
```

```python
# ✅ Valid - any variable name works
from fastapi import APIRouter

api = APIRouter(prefix="/products")
user_routes = APIRouter()
```

```python  
# ❌ Invalid - no APIRouter export
from fastapi import FastAPI

app = FastAPI()  # This won't be discovered

@app.get("/")
async def root():
    return {"message": "hello"}
```

## Benefits

- **Zero Boilerplate**: No manual router imports or registration
- **Intuitive Organization**: File structure mirrors URL structure
- **Parameter Safety**: Automatic validation of path parameters
- **IDE-Friendly**: Clear file organization with predictable patterns
- **SvelteKit Familiar**: Same conventions as SvelteKit routing

Auto-discovery makes large FastAPI applications feel organized and maintainable while preserving the flexibility of manual router configuration when needed.
