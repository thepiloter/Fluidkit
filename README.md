# FluidKit

**Zero-configuration FastAPI to TypeScript code generation using runtime introspection.**

## What is FluidKit?

FluidKit automatically generates TypeScript clients from your FastAPI applications using runtime introspection. No decorators, no configuration files, no guesswork - just point it at your FastAPI app and get production-ready TypeScript code.

```python
# Your existing FastAPI app
from fastapi import FastAPI, Query, Path
from pydantic import BaseModel
from typing import Optional, List

class User(BaseModel):
    id: int
    name: str
    email: Optional[str] = None

app = FastAPI()

@app.get("/users/{user_id}")
async def get_user(user_id: int = Path(...), include_profile: bool = Query(False)) -> User:
    return User(id=user_id, name="John Doe")

@app.post("/users")
async def create_user(user: User) -> User:
    return user
```

```python
# Generate TypeScript clients
import fluidkit

# That's it - zero configuration needed
fluidkit.integrate(app)
```

```typescript
// Auto-generated: TypeScript clients with full type safety
export interface User {
  id: number;
  name: string;
  email?: string;
}

export const get_user = async (
  user_id: number, 
  include_profile?: boolean, 
  options?: RequestInit
): Promise<ApiResult<User>> => {
  // Environment-aware fetch implementation
}

export const create_user = async (
  user: User, 
  options?: RequestInit
): Promise<ApiResult<User>> => {
  // Complete fetch wrapper with JSON handling
}
```

## How It Works

FluidKit uses **runtime introspection** instead of static analysis:

1. **Introspects your FastAPI app** using FastAPI's internal dependency system
2. **Discovers Pydantic models** through recursive tree traversal from route types  
3. **Generates TypeScript code** with perfect parameter classification
4. **Writes files to disk** with automatic import resolution

**No decorators. No configuration. Just your existing FastAPI code.**

## Key Features

### Zero Configuration
```python
# Works with any existing FastAPI app
fluidkit.integrate(app)  # That's literally it
```

### Perfect FastAPI Compliance
- Uses FastAPI's own parameter classification (`Query`, `Path`, `Body`, etc.)
- Handles complex Pydantic models and inheritance
- Supports FastAPI security requirements
- Multi-method routes (`@app.api_route(methods=["GET", "POST"])`)

### Intelligent Type Generation
```python
# Python
def get_users(
    status: Optional[UserStatus] = Query(None),
    limit: int = Query(10, ge=1, le=100)
) -> List[User]:
```

```typescript
// Generated TypeScript with validation docs
export const get_users = async (
  status?: UserStatus,
  /** @minimum 1 @maximum 100 @default 10 */
  limit?: number,
  options?: RequestInit
): Promise<ApiResult<User[]>> => {
```

### Strategy-Based Generation
```python
# Co-locate: .ts files next to .py files
fluidkit.integrate(app, strategy="co-locate")

# Mirror: .ts files in .fluidkit/ directory  
fluidkit.integrate(app, strategy="mirror")
```

### Multi-Language Ready
```python
# Currently supports TypeScript
fluidkit.integrate(app, lang="typescript")

# Future: Python clients, Zod schemas, etc.
# fluidkit.integrate(app, lang="python") 
# fluidkit.integrate(app, lang="zod")
```

## Generated Code Quality

### Environment-Aware Communication
```typescript
// Same code works everywhere:
const result = await get_user(123);

// Browser: fetch('/api/users/123') → SvelteKit proxy → FastAPI
// Server: fetch('http://localhost:8000/users/123') → Direct FastAPI
```

### Complete Error Handling
```typescript
interface ApiResult<T> {
  data?: T;              // Successful response
  error?: string;        // Error message  
  status: number;        // HTTP status
  success: boolean;      // Convenience flag
}

const result = await create_user(userData);
if (result.success) {
  console.log("Created:", result.data);
} else {
  console.error("Error:", result.error);
}
```

### Smart Import Resolution
```typescript
// Auto-generated imports based on strategy
import { User, UserStatus } from './models';
import { ApiResult, getBaseUrl, handleResponse } from '../.fluidkit/runtime';
```

## Usage

### Basic Usage
```python
from fastapi import FastAPI
import fluidkit

app = FastAPI()
# ... define your routes and models

# Generate TypeScript clients
fluidkit.integrate(app)
```

### With Options
```python
# Mirror strategy (default)
fluidkit.integrate(app, strategy="mirror")

# Co-locate strategy
fluidkit.integrate(app, strategy="co-locate") 

# Verbose output
fluidkit.integrate(app, verbose=True)

# Custom runtime names
fluidkit.integrate(
    app,
    api_result_type="CustomApiResult",
    get_base_url_fn="customGetBaseUrl"
)
```

### Convenience Functions
```python
# Introspection only (no file generation)
fluid_app = fluidkit.introspect_only(app)

# Generate without writing files
files = fluidkit.generate_only(app, strategy="mirror")
```

## Generated File Structure

### Mirror Strategy (Default)
```
project/
├── your-fastapi-code.py
└── .fluidkit/                    # Generated TypeScript
    ├── your-fastapi-code.ts      # Mirrored structure  
    └── runtime.ts                # Shared utilities
```

### Co-locate Strategy  
```
project/
├── your-fastapi-code.py
├── your-fastapi-code.ts          # Next to Python files
└── .fluidkit/
    └── runtime.ts                # Shared utilities
```

## SvelteKit Integration

FluidKit works seamlessly with SvelteKit's proxy architecture:

```typescript
// Auto-configured: src/routes/api/[...path]/+server.ts
// Proxies /api/* requests to your FastAPI backend

// Use generated clients anywhere:
import { get_user } from '$lib/api/users';  // Mirror strategy
import { get_user } from './api';           // Co-locate strategy

export const load: PageServerLoad = async () => {
    const result = await get_user(123);
    return { user: result.data };
};
```

## Current Status

**Production Ready Core:**
- ✅ Runtime introspection of FastAPI apps
- ✅ Complete TypeScript generation pipeline  
- ✅ Strategy-based file generation
- ✅ Import resolution and file writing
- ✅ Multi-language architecture

**Coming Soon:**
- 🚧 CLI tooling (`fluidkit init`, `fluidkit dev`)
- 🚧 Project templates and scaffolding
- 🚧 Watch mode for development
- 🚧 Additional language support (Python, Zod, JavaScript)

## Requirements

- **Python 3.8+** with FastAPI and Pydantic
- **Node.js** (for TypeScript usage)

## Installation

```bash
# Currently install from source
git clone https://github.com/your-org/fluidkit
cd fluidkit
pip install -e .
```

## Why FluidKit?

**Traditional Approach:**
- Maintain separate OpenAPI specs
- Hand-write TypeScript clients  
- Keep types in sync manually
- Debug parameter classification issues

**FluidKit Approach:**
- Write FastAPI normally
- Run `fluidkit.integrate(app)`
- Get perfect TypeScript clients
- Zero maintenance overhead

FluidKit eliminates the gap between Python backend and TypeScript frontend development. Write your API once, use it everywhere with full type safety.

---

**FluidKit: Runtime introspection for seamless full-stack development.**
