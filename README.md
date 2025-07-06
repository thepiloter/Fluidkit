# FluidKit

**A framework that bridges Python FastAPI and SvelteKit, giving you the best of both ecosystems with complete development freedom.**

## The Concept

FluidKit eliminates the artificial boundary between frontend and backend development. Write your application logic in Python, your UI in Svelte, and get automatic TypeScript clients with full type safety. No restrictions, no conventions - just seamless integration.

- **Write FastAPI anywhere** - lib folders, route folders, wherever makes sense
- **Auto-generated TypeScript clients** with full type safety from Pydantic models  
- **Environment-aware communication** - proxy in browser, direct on server
- **Enforce FastAPI best practices** for reliable TypeScript generation
- **Full ecosystem access** - tap into Python ML/data and Node.js frontend ecosystems selectively

## How It Works

1. **Write FastAPI routes anywhere** using proper FastAPI patterns
2. **Mark models with `@interface`** decorator for TypeScript generation
3. **Auto-generate TypeScript clients** - same filename, same location as Python files
4. **Import and use** - environment-aware fetch wrappers work everywhere

```python
# src/lib/api/users.py (or anywhere you want)
from fastapi import APIRouter, Query
from pydantic import BaseModel
from core.ast_utils import interface

router = APIRouter()

@interface
class User(BaseModel):
    id: int
    name: str
    email: str

@router.get("/users/{user_id}")
async def get_user(user_id: int, include_profile: bool = Query(False)):
    return User(id=user_id, name="John", email="john@example.com")
```

```typescript
// Auto-generated: src/lib/api/users.ts
import { ApiResult, getBaseUrl, handleResponse } from '../../.fluidkit/fluidkit';

export interface User {
  id: number;
  name: string;
  email: string;
}

export async function get_user(
  user_id: number, 
  include_profile?: boolean, 
  options?: RequestInit
): Promise<ApiResult<User>> {
  // Environment-aware: proxy in browser, direct on server
}
```

```typescript
// Use anywhere - +page.server.ts, +page.ts, or components
import { get_user } from '$lib/api/users';

export const load: PageServerLoad = async () => {
    const result = await get_user(123, true);
    if (result.success) {
        return { user: result.response };
    }
    // Handle errors...
};
```

## Architecture: Freedom with Best Practices

FluidKit follows established full-stack patterns - similar to Next.js API routes or SvelteKit's approach:

### 📁 Recommended Structure (But Not Required)

```
src/
├── lib/
│   ├── api/                 # Shared API logic
│   │   ├── auth.py         # Authentication
│   │   ├── auth.ts         # Auto-generated
│   │   ├── users.py        # User management  
│   │   ├── users.ts        # Auto-generated
│   │   └── payments.py     # Payment processing
│   └── shared/             # Shared utilities
├── routes/
│   ├── dashboard/
│   │   ├── +page.svelte    # UI
│   │   ├── +page.server.ts # Load data using generated clients
│   │   ├── api.py          # Page-specific API logic (optional)
│   │   └── api.ts          # Auto-generated (if api.py exists)
│   └── api/
│       └── [...path]/
│           └── +server.ts  # FastAPI proxy (auto-configured)
└── .fluidkit/
    └── fluidkit.ts         # Auto-generated runtime utilities
```

### 🎯 Development Patterns

**API-First Development:**
```python
# src/lib/api/analytics.py - Pure business logic
@router.get("/analytics")
async def get_analytics(date_range: DateRange = Query(...)):
    # Complex analytics logic
    return AnalyticsResult(...)
```

**Page-Specific Logic:**
```python
# src/routes/dashboard/data.py - Page-specific data loading
@router.get("/dashboard-data") 
async def load_dashboard(user_id: int = Depends(get_current_user_id)):
    # Combine multiple data sources for this specific page
    return DashboardData(...)
```

## Key Benefits

### 🚀 **Complete Development Freedom**
- **No file naming restrictions** - name your files whatever makes sense
- **No location requirements** - organize your code however you prefer  
- **Follow your team's patterns** - lib/, api/, wherever you want

### 🔒 **Type Safety Without Compromise**
```python
@interface
class CreateUserRequest(BaseModel):
    name: str = Field(..., min_length=2)
    email: EmailStr
    role: UserRole = UserRole.USER
```

```typescript
// Generated with full validation info in JSDoc
export interface CreateUserRequest {
  /** @minLength 2 */
  name: string;
  email: string;
  role?: UserRole;
}
```

### 🌐 **Environment-Aware Communication**
```typescript
// Same code works everywhere:
const user = await get_user(123);

// In browser: → fetch('/api/users/123') → SvelteKit proxy → FastAPI
// In +page.server.ts: → fetch('http://localhost:8000/users/123') → Direct FastAPI
```

### ⚡ **Best Practices Enforcement**
- **Explicit FastAPI annotations** required for reliable generation
- **Pydantic models** for automatic TypeScript interfaces
- **Consistent error handling** with generic `ApiResult<T>` type
- **Authentication-ready** with `options` parameter on every function

## FastAPI Integration

FluidKit works with standard FastAPI - no magic, no vendor lock-in:

```python
# Any FastAPI app structure works
from fastapi import FastAPI
from src.lib.api.users import router as users_router
from src.routes.dashboard.data import router as dashboard_router

app = FastAPI()
app.include_router(users_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")
```

**SvelteKit Proxy (Auto-configured):**
```typescript
// src/routes/api/[...path]/+server.ts
export { GET, POST, PUT, DELETE } from '$lib/fluidkit/proxy';
```

## Current Status

**🎯 Production Ready**: Complete TypeScript generation pipeline

**✅ Working:**
- Full FastAPI → TypeScript client generation
- Complex type conversion (generics, unions, optionals)
- Enum support (string & numeric)
- File-scoped symbol resolution
- Environment-aware communication
- Validation constraint documentation

**🚧 Coming Soon:**
- CLI tooling for project initialization
- Development server integration
- Watch mode for automatic regeneration
- Advanced authentication patterns

## Quick Start

<!-- ```bash
# Generate TypeScript clients from your FastAPI code
python -m fluidkit.generate src/lib/api/users.py src/routes/dashboard/data.py

# Or process entire directories
python -m fluidkit.generate src/ --watch
``` -->
Try out running test.py

> Note: After CLI implemented we will have a comprehensive documentation

<!-- ```typescript
// Use generated clients immediately
import { create_user, get_user } from '$lib/api/users';

const result = await create_user({
    name: "Alice",
    email: "alice@example.com"
});

if (result.success) {
    console.log("User created:", result.response);
} else {
    console.error("Error:", result.error);
}
``` -->

## Philosophy

FluidKit believes in **developer freedom** over framework constraints. Whether you prefer:
- Co-located API routes next to pages (like the original vision)
- Centralized API layers in lib/ folders (like Next.js)  
- Domain-driven folder structures
- Monolithic api.py files

**FluidKit adapts to your workflow**, not the other way around.

**Core Principle**: Write FastAPI the way you want, get TypeScript clients for free.

---

*FluidKit: Where Python backend meets TypeScript frontend, naturally.*
