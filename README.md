Here's a comprehensive README that captures the FluidKit concept properly:

# FluidKit

**A framework that bridges Python FastAPI and SvelteKit, giving you the best of both ecosystems with a unified development experience.**

## The Concept

FluidKit lets you write backend logic in Python while keeping all the power of SvelteKit's frontend capabilities. Instead of maintaining separate frontend and backend codebases, you get:

- **Single codebase** with Python backend logic co-located with your SvelteKit routes
- **Auto-generated TypeScript clients** from your FastAPI route definitions
- **Unified mental model** - no context switching between different projects
- **Full ecosystem access** - use any Python library alongside any Node.js library

## How It Works

1. **Write FastAPI routes** in `page.py` files alongside your Svelte pages
2. **Auto-generate TypeScript clients** with full type safety from Pydantic models
3. **Proxy through SvelteKit** - FastAPI runs behind SvelteKit's dev server
4. **Use anywhere** - import generated functions in `+page.server.ts`, `+page.ts`, or components

```python
# src/routes/dashboard/page.py
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class Analytics(BaseModel):
    users: int
    revenue: float

@router.get("/", response_model=Analytics)
async def load():
    return Analytics(users=1250, revenue=45230.50)
```

```typescript
// Auto-generated: src/routes/dashboard/page.ts
export async function load(): Promise<ApiResult<Analytics>> {
    // Type-safe fetch wrapper automatically generated
}
```

```typescript
// src/routes/dashboard/+page.server.ts
import { load } from './page.js';

export const load: PageServerLoad = async () => {
    const result = await load();
    return result.data; // Fully typed!
};
```

## Architecture: Best of Both Worlds

FluidKit uses a **hybrid approach** that scales with your needs:

### 📁 Page-Specific Logic (Co-located)
Keep page-specific backend logic right next to your Svelte components:

```
src/routes/dashboard/
├── +page.svelte          # UI components
├── +page.server.ts       # SvelteKit server logic
├── page.py              # Dashboard FastAPI routes
├── page.ts              # Auto-generated client
└── components/          # Page-specific components
    ├── Chart.svelte
    └── Stats.svelte
```

### 🔄 Shared Utilities (Centralized)
Shared logic stays organized in lib folders:

```
src/lib/backend/
├── auth.py              # Authentication utilities
├── auth.ts              # Auto-generated auth client
├── database.py          # Database connections
└── validation.py        # Common validators
```

## Project Structure

```
project/
├── src/
│   ├── lib/
│   │   └── backend/         # Shared FastAPI utilities
│   │       ├── auth.py
│   │       ├── auth.ts      # Auto-generated
│   │       ├── database.py
│   │       └── validation.py
│   ├── routes/
│   │   ├── +layout.svelte
│   │   ├── +page.svelte
│   │   ├── page.py          # Homepage FastAPI routes
│   │   ├── page.ts          # Auto-generated client
│   │   ├── +page.server.ts  # SvelteKit server load
│   │   ├── dashboard/
│   │   │   ├── +page.svelte
│   │   │   ├── page.py      # Dashboard-specific logic
│   │   │   ├── page.ts      # Auto-generated client
│   │   │   └── +page.server.ts
│   │   └── api/
│   │       └── [...path]/
│   │           └── +server.ts   # FastAPI proxy
│   ├── app.html
│   └── main.py              # FastAPI app entry point
├── static/
├── package.json
├── svelte.config.js
├── vite.config.js
├── pyproject.toml           # Python dependencies
└── uv.lock
```

## Key Benefits

### 🎯 **Locality of Behavior**
```
src/routes/checkout/
├── +page.svelte      # Checkout UI
├── page.py          # Payment processing logic
└── page.ts          # Type-safe payment client
```
Everything for a feature lives together. No hunting across repositories.

### 🔒 **End-to-End Type Safety**
```python
# Python model
class User(BaseModel):
    id: int
    email: str
```

```typescript
// Auto-generated TypeScript
interface User {
    id: number;
    email: string;
}
```

### 🚀 **Best of Both Ecosystems**
- **Python**: ML libraries, data processing, mature backend ecosystem
- **Node.js**: Modern build tools, frontend packages, SvelteKit features
- **No compromise**: Use what's best for each task

### 🔄 **Unified Development**
- Single `dev` command runs both Python and Node.js
- Hot reloading for both frontend and backend changes
- Shared environment variables and configuration

## Current Status

**🎯 MVP Status**: Pydantic to TypeScript converter implemented

**✅ Working:**
- Pydantic model → TypeScript interface conversion
- `@interface` decorator for marking models to convert

**🚧 Coming Next:**
1. FastAPI route → TypeScript client generation
2. Automatic dependency graph analysis (no decorators needed)
3. Development server integration
4. CLI tooling for project scaffolding

## Quick Start

```bash
# Install dependencies
pip install uv
uv sync

# Test Pydantic → TypeScript conversion
uv run python test.py
```

## Vision

FluidKit aims to eliminate the artificial boundary between frontend and backend development. Write your application logic in Python, your UI in Svelte, and let the framework handle the bridging automatically.

**Mental Model**: One codebase, two runtimes, unified experience.

---

*FluidKit is in active development. Star and watch for updates!*
