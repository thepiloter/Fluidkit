# FluidKit

<div align="center">
  <img src="https://azure-deliberate-dog-514.mypinata.cloud/ipfs/bafkreiay74jzankyzj2zh4zemmpidafbsrcr4hwjxnl5e3qk32xyi6t3hi" alt="FluidKit Logo" width="125">
</div>

**Web development for the pythoniers**

FluidKit provides tooling for building modern, highly optimized fullstack web applications with Python + the power of SvelteKit. Automatic type-safe client generation and environment-aware proxying make FastAPI + SvelteKit feel like a unified framework.

```bash
pip install fluidkit
```

## Build Modern Web Apps with Python

Access the JavaScript ecosystem for UI while keeping all your business logic in Python. No Node.js backend knowledge required.

### 📦 **Client Generation** - For any project setup
```python
import fluidkit
fluidkit.integrate(app)  # Generates portable TypeScript clients
```

### 🌐 **Full-Stack Development** - Python + SvelteKit unified
```python
import fluidkit
fluidkit.integrate(app, enable_fullstack=True)  # Complete fullstack tooling
```

## 🚀 Full-Stack Get Started

**Prerequisites:** Node.js, [uv](https://docs.astral.sh/uv/) (preferred) or Poetry

```bash
# 1. Create SvelteKit project
npx sv create my-app
cd my-app

# 2. Initialize Python environment
uv init  # or: poetry init
uv add fluidkit  # or: poetry add fluidkit

# 3. Create Python backend
```

**Folder structure:**
```
src/routes/
├── +page.svelte  # Svelte component
├── app.api.py    # Python API logic  
└── app.api.ts    # Auto-generated client (by FluidKit)
```

**Create `src/app.py`:**
```python
import fluidkit
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

fluidkit.integrate(app, enable_fullstack=True)

if __name__ == "__main__":
  import uvicorn
  uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
```

**Create `src/routes/hello.api.py`:**
```python
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class Message(BaseModel):
    text: str

@router.get("/hello")
async def get_message() -> Message:
    return Message(text="Hello from Python!")
```

**Use in `src/routes/+page.svelte`:**
```svelte
<script>
  import { get_message } from './hello.api';
  
  let message = $state('');
  
  get_message().then(result => {
    if (result.success) message = result.data.text;
  });
</script>

<h1>{message}</h1>
```

```bash
# 4. Start development
uv run python src/app.py  # Start Python backend
npm run dev  # Start SvelteKit (separate terminal)
```

**You're ready!** Visit `http://localhost:5173` to see your full-stack app. Visit `http://localhost:5173/proxy/docs` to see fastapi swagger UI.


## The FluidKit Experience

**Write your backend in Python:**
```python
from uuid import UUID
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class User(BaseModel):
    id: UUID
    name: str
    email: str

@app.get("/users/{user_id}")
async def get_user(user_id: UUID) -> User:
    # Your Python logic - database, validation, etc.
    return fetch_user_from_database(user_id)

import fluidkit
fluidkit.integrate(app, enable_fullstack=True)
```

**Use directly in SvelteKit like local functions:**
```svelte
<script>
  import { get_user } from './users.api';
  
  let userId = $state('');
  let user = $state(null);
  let error = $state('');
  
  function loadUser() {
    error = '';
    get_user(userId).then(result => {
      if (result.success) {
        user = result.data;
      } else {
        error = result.error;
      }
    });
  }
</script>

<input bind:value={userId} placeholder="Enter user ID" />
<button onclick={loadUser}>Load User</button>

{#if error}
  <p style="color: red;">{error}</p>
{/if}

{#if user}
  <div>
    <h3>{user.name}</h3>
    <p>{user.email}</p>
  </div>
{/if}
```

**FluidKit automatically generates:**
```typescript
// Full type safety from Python → TypeScript
export interface User {
  id: FluidTypes.UUID;
  name: string;
  email: string;
}

export const get_user = async (user_id: FluidTypes.UUID): Promise<ApiResult<User>> => {
  // Environment-aware: direct FastAPI in SSR, proxied in browser
};
```

## ✨ What's New in v0.2.7

- 🔄 **[Streaming Support](docs/streaming.md)** - Server-Sent Events, file downloads, JSON streaming
- 🏷️ **[FluidTypes Namespace](docs/types.md)** - Clean handling of external types (UUID, Decimal, DateTime)
- 📁 **[Enhanced Auto-Discovery](docs/auto-discovery.md)** - SvelteKit-style folder routing with parameter validation
- ⚡ **Simplified Configuration** - Zero config for client generation, rich config for fullstack

## 🚀 Key Features

- **Unified Development Experience** - Write Python, get modern SvelteKit web apps
- **Complete Type Safety** - Python types → TypeScript interfaces automatically  
- **Environment-Aware Proxying** - Same client works in SSR and browser seamlessly
- **Streaming First-Class** - SSE, file downloads, JSON streaming support
- **Smart External Types** - UUID, Decimal, DateTime via clean `FluidTypes` namespace
- **Auto-Discovery** - SvelteKit-style file-based routing patterns
- **Zero Node.js Knowledge Required** - Pure Python backend development
- **Highly Optimized** - SvelteKit's SSR, hydration, code splitting, and performance

## 🛠️ Two Development Modes

### **Client Generation Only**
Perfect for existing projects, microservices, or when frontend/backend deploy separately:

```python
# Generates portable TypeScript clients
fluidkit.integrate(app)
```
- Clean `.fluidkit/` output directory
- Copy generated clients to any frontend project  
- Works with React, Vue, vanilla TypeScript, etc.
- Full type safety across the API boundary

### **Full-Stack Development**
Unified Python + SvelteKit development with seamless integration:

```python
# Enables complete fullstack tooling
fluidkit.integrate(app, enable_fullstack=True)
```
- Auto-generated SvelteKit proxy routes
- Environment-aware client (SSR + browser)
- Hot reload across frontend and backend
- Production deployment optimization
- Auto-discovery of API routes

## 📚 Documentation

| Guide | Description |
|-------|-------------|
| **[Full-Stack Development](docs/fullstack.md)** | Complete SvelteKit integration, deployment, environment setup |
| **[Streaming Clients](docs/streaming.md)** | SSE, file downloads, JSON streaming patterns |
| **[Configuration](docs/configuration.md)** | Config reference, strategies, environments |
| **[Auto-Discovery](docs/auto-discovery.md)** | File patterns, routing conventions, parameter validation |
| **[Type System](docs/types.md)** | FluidTypes namespace, external type handling |

## 🛣️ Roadmap

- ✅ **TypeScript Client Generation** (current)
- ✅ **SvelteKit Full-Stack Integration** (current)  
- 🚧 **CLI Tooling** - Project templates, deployment orchestration
- 🚧 **Python Client Generation** - Full Python ecosystem
- 🚧 **Advanced Streaming** - WebSockets, real-time features


**Build modern, type-safe web applications using the Python ecosystem you know + the SvelteKit performance you want.**
