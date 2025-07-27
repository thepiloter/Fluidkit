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
    bio: str

@app.post("/users")
async def create_user(user: User) -> User:
    # Your Python logic - pandas, ML, databases, etc.
    return save_user_to_database(user)

@app.get("/users/{user_id}/recommendations")  
async def get_recommendations(user_id: UUID) -> list[Product]:
    # Complex ML/AI logic in Python
    return run_recommendation_engine(user_id)

import fluidkit
fluidkit.integrate(app, enable_fullstack=True)
```

**Use directly in SvelteKit like local functions:**
```svelte
<script>
  import { createUser, getRecommendations } from '$lib/api/users';
  
  let user = { name: '', bio: '' };
  let recommendations = [];
  
  async function handleSubmit() {
    // Feels like calling a local function, but it's your Python FastAPI
    const result = await createUser(user);
    if (result.success) {
      // Type-safe throughout - full IDE autocomplete
      recommendations = await getRecommendations(result.data.id);
    }
  }
</script>

<form on:submit|preventDefault={handleSubmit}>
  <input bind:value={user.name} placeholder="Name" />
  <textarea bind:value={user.bio} placeholder="Bio"></textarea>
  <button type="submit">Create User</button>
</form>

{#each recommendations.data || [] as product}
  <ProductCard {product} />
{/each}
```

**FluidKit automatically generates:**
```typescript
// Full type safety from Python → TypeScript
export interface User {
  id: FluidTypes.UUID;
  name: string;
  bio: string;
}

export const createUser = async (user: User): Promise<ApiResult<User>> => {
  // Environment-aware: direct FastAPI in SSR, proxied in browser
};
```

## ✨ What's New in v0.2.4

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

## Quick Start

```python
# 1. Install FluidKit
pip install fluidkit

# 2. Add to your FastAPI app
import fluidkit
fluidkit.integrate(app, enable_fullstack=True)

# 3. Start developing
# - Your Python API functions become importable in SvelteKit as co-located ts files will be created with client code
# - Full type safety throughout
# - Environment-aware proxying handles SSR/CSR automatically
# - Access entire JavaScript ecosystem for UI
```

---

**Build modern, type-safe web applications using the Python ecosystem you know + the SvelteKit performance you want.**
