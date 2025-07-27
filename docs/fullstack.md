# Full-Stack Development with FluidKit

Complete guide to building unified Python + SvelteKit applications with FluidKit's automatic bridging.

## Core Concept

FluidKit makes your Python FastAPI functions directly importable in SvelteKit through automatic type-safe client generation and intelligent proxying. Write Python, import in Svelte, deploy as a unified application.

## File Organization Strategies

### Co-Location Strategy (Recommended)

Place API logic directly alongside your SvelteKit routes:

```
src/routes/
├── users/
│   ├── user.api.py          # 🐍 Python API logic
│   ├── user.api.ts          # 🔄 Auto-generated TypeScript client
│   └── +page.svelte         # 💚 SvelteKit page
└── products/
    ├── [id]/
    │   ├── details.api.py   # 🐍 Dynamic route API
    │   ├── details.api.ts   # 🔄 Auto-generated client
    │   └── +page.svelte     # 💚 Product details page
```

### Usage in SvelteKit

```svelte
<!-- src/routes/users/+page.svelte -->
<script>
  import { createUser, getUser, getRecommendations } from './user.api';
  
  let user = { name: '', email: '' };
  let recommendations = [];
  
  async function handleSubmit() {
    const result = await createUser(user);
    if (result.success) {
      recommendations = await getRecommendations(result.data.id);
    }
  }
</script>
```

### Mirror Strategy with Aliases

For projects preferring separation, use Vite aliases:

```javascript
// vite.config.js
export default {
  resolve: {
    alias: {
      '$fluidkit': './.fluidkit'
    }
  }
}
```

```svelte
<script>
  import { createUser } from '$fluidkit/routes/users/user.api';
</script>
```

## SvelteKit-Style Folder Routing

FluidKit supports SvelteKit routing conventions for automatic FastAPI route binding:

### Basic Routes

```
src/routes/users/user.api.py        → /users/*
src/routes/products/product.api.py  → /products/*
```

### Dynamic Parameters

```
src/routes/users/[id]/profile.api.py     → /users/{id}/*
src/routes/posts/[slug]/comments.api.py  → /posts/{slug}/*
```

**Parameter Validation**: FluidKit ensures your Python function includes the required path parameters:

```python
# src/routes/users/[id]/profile.api.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/details")
async def get_profile(id: int):  # ✅ Required 'id' parameter
    return {"user_id": id, "profile": "details"}

@router.post("/update")  
async def update_profile(id: int, data: ProfileData):  # ✅ 'id' required
    return update_user_profile(id, data)
```

### Rest Parameters

```
src/routes/files/[...path]/handler.api.py  → /files/{path:path}/*
```

```python
# src/routes/files/[...path]/handler.api.py
@router.get("/download")
async def download_file(path: str):  # ✅ Required 'path' parameter
    return {"file_path": path}
```

### Route Groups (Ignored in URLs)

```
src/routes/(admin)/users/manage.api.py      → /users/*  
src/routes/(app)/dashboard/stats.api.py     → /dashboard/*
```

Route groups organize code without affecting the URL structure.

## File Naming Conventions

FluidKit auto-discovers Python files using these patterns:

### Underscore Pattern
```
_api.py, _routes.py, _handlers.py
```

### Dot Pattern  
```
user.api.py, admin.routes.py, data.service.py
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

## Complete Example

### Python API Definition

```python
# src/routes/users/user.api.py
from fastapi import APIRouter
from pydantic import BaseModel
from uuid import UUID

router = APIRouter(prefix="/users")

class User(BaseModel):
    id: UUID
    name: str
    email: str

class CreateUserRequest(BaseModel):
    name: str
    email: str

@router.post("/")
async def create_user(data: CreateUserRequest) -> User:
    """Create a new user"""
    return User(id=uuid4(), name=data.name, email=data.email)

@router.get("/{user_id}")
async def get_user(user_id: UUID) -> User:
    """Get user by ID"""
    return fetch_user_from_db(user_id)

@router.get("/{user_id}/recommendations")
async def get_recommendations(user_id: UUID) -> list[Product]:
    """Get personalized recommendations"""
    return run_ml_recommendation_engine(user_id)
```

### Auto-Generated TypeScript Client

```typescript
// src/routes/users/user.api.ts (auto-generated)
import type { FluidTypes, ApiResult } from '$lib/.fluidkit/runtime';

export interface User {
  id: FluidTypes.UUID;
  name: string;
  email: string;
}

export interface CreateUserRequest {
  name: string;
  email: string;
}

/**
 * Create a new user
 */
export const create_user = async (
  data: CreateUserRequest,
  options?: RequestInit
): Promise<ApiResult<User>> => {
  // Environment-aware implementation
};

export const get_user = async (
  user_id: FluidTypes.UUID,
  options?: RequestInit  
): Promise<ApiResult<User>> => {
  // Auto-generated client implementation
};

export const get_recommendations = async (
  user_id: FluidTypes.UUID,
  options?: RequestInit
): Promise<ApiResult<Product[]>> => {
  // Type-safe client with ML results
};
```

### SvelteKit Page Usage

```svelte
<!-- src/routes/users/+page.svelte -->
<script>
  import { create_user, get_user, get_recommendations } from './user.api';
  
  let formData = { name: '', email: '' };
  let selectedUser = null;
  let recommendations = [];
  
  async function createUser() {
    const result = await create_user(formData);
    if (result.success) {
      selectedUser = result.data;
      loadRecommendations(result.data.id);
    }
  }
  
  async function loadRecommendations(userId) {
    const recs = await get_recommendations(userId);
    if (recs.success) {
      recommendations = recs.data;
    }
  }
</script>

<form on:submit|preventDefault={createUser}>
  <input bind:value={formData.name} placeholder="Name" />
  <input bind:value={formData.email} placeholder="Email" type="email" />
  <button type="submit">Create User</button>
</form>

{#if selectedUser}
  <h2>Welcome, {selectedUser.name}!</h2>
  
  {#if recommendations.length > 0}
    <h3>Recommended for you:</h3>
    {#each recommendations as product}
      <ProductCard {product} />
    {/each}
  {/if}
{/if}
```

## Environment-Aware Proxying

The same generated client works seamlessly in both SSR and browser:

- **Server-side rendering**: Direct FastAPI communication
- **Browser interactions**: Proxied through SvelteKit routes
- **Development**: Hot reload across Python and Svelte changes
- **Production**: Optimized builds with proper environment detection

## Integration Setup

```python
# Enable fullstack development
import fluidkit
fluidkit.integrate(app, enable_fullstack=True)
```

This automatically:
- Discovers `*.api.py` files in your SvelteKit routes
- Validates parameter signatures match folder structure  
- Generates TypeScript clients in the same locations
- Creates SvelteKit proxy routes for browser requests
- Enables hot reload for both Python and Svelte changes

The result: **Python functions become directly importable in SvelteKit with full type safety and optimal performance.**
