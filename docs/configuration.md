# Configuration

FluidKit's configuration system adapts to your development needs with automatic config generation and intelligent defaults.

## Configuration Modes

### Simple Mode (Code Generation Only)

```python
# Generates minimal config for portable TypeScript clients
fluidkit.integrate(app)
```

**Generated config:**
```json
{
  "target": "development",
  "output": {
    "strategy": "mirror",
    "location": ".fluidkit"
  },
  "backend": {
    "host": "localhost",
    "port": 8000
  },
  "frontend": {
    "host": "localhost",
    "port": 5173
  },
  "environments": {
    "development": {
      "mode": "separate",
      "apiUrl": "http://localhost:8000"
    },
    "production": {
      "mode": "separate",
      "apiUrl": ""
    }
  }
}
```

**Use case**: Generate TypeScript clients for existing projects, microservices, or separate frontend deployments.

### Full-Stack Mode (SvelteKit Integration)

```python
# Generates complete config for unified development
fluidkit.integrate(app, enable_fullstack=True)
```

**Generated config:**
```json
{
  "framework": "sveltekit",
  "target": "development",
  "output": {
    "strategy": "mirror", 
    "location": ".fluidkit"
  },
  "backend": {
    "host": "localhost",
    "port": 8000
  },
  "frontend": {
    "host": "localhost",
    "port": 5173
  },
  "environments": {
    "development": {
      "mode": "unified",
      "apiUrl": "/api"
    },
    "production": {
      "mode": "separate",
      "apiUrl": "https://api.example.com"
    }
  },
  "autoDiscovery": {
    "enabled": true,
    "filePatterns": ["_*.py", "*.*.py"]
  },
  "include": ["src/**/*.py"],
  "exclude": ["**/__pycache__/**", "**/*.test.py", "**/*.spec.py"]
}
```

**Use case**: Unified Python + SvelteKit development with auto-discovery and proxying.

## Configuration Upgrade

Existing configs automatically upgrade when switching to full-stack:

```python
# Week 1: Start simple
fluidkit.integrate(app)  # Creates simple config

# Week 3: Add custom settings
# User modifies: port: 3001, location: "generated/"

# Week 5: Upgrade to full-stack
fluidkit.integrate(app, enable_fullstack=True)
# Preserves: port: 3001, location: "generated/"
# Adds: framework, autoDiscovery, unified mode
```

## Configuration Reference

### Core Settings

| Field | Values | Description |
|-------|--------|-------------|
| `target` | `"development"` \| `"production"` | Active environment |
| `framework` | `"sveltekit"` \| `null` | Framework integration |

### Output Configuration

| Field | Values | Description |
|-------|--------|-------------|
| `output.strategy` | `"mirror"` \| `"co-locate"` | File placement strategy |
| `output.location` | `".fluidkit"` \| `"src/lib"` | Output directory |

#### Strategy Comparison

**Mirror Strategy** (default):
```
src/                    # Python code (unchanged)
├── routes/users.py
└── models/user.py

.fluidkit/             # Generated TypeScript
├── runtime.ts
├── routes/users.ts
└── models/user.ts
```

**Co-locate Strategy**:
```
src/
├── routes/
│   ├── users.py       # Python
│   └── users.ts       # Generated TypeScript
└── models/
    ├── user.py
    └── user.ts
```

### Environment Configuration

| Field | Values | Description |
|-------|--------|-------------|
| `mode` | `"unified"` \| `"separate"` | Deployment architecture |
| `apiUrl` | URL string | API base URL for environment |

#### Mode Explanation

**Unified Mode**: Same codebase, proxied requests
- Development: SvelteKit proxies to FastAPI
- Same client works in SSR and browser
- Single deployment artifact

**Separate Mode**: Independent deployments  
- Frontend and backend deploy separately
- Direct API communication
- CORS handling required

### Auto-Discovery (Full-Stack Only)

| Field | Values | Description |
|-------|--------|-------------|
| `autoDiscovery.enabled` | `true` \| `false` | Enable file-based route discovery |
| `autoDiscovery.filePatterns` | `["_*.py", "*.*.py"]` | File patterns to discover |
| `include` | `["src/**/*.py"]` | Paths to scan |
| `exclude` | `["**/__pycache__/**"]` | Exclude patterns |

## Environment Examples

### Development Setup

```json
{
  "target": "development",
  "framework": "sveltekit",
  "environments": {
    "development": {
      "mode": "unified",
      "apiUrl": "/api"
    }
  }
}
```

**Result**: Local development with hot reload, SvelteKit proxy to FastAPI.

### Production Setup

```json
{
  "target": "production", 
  "environments": {
    "production": {
      "mode": "separate",
      "apiUrl": "https://api.yourdomain.com"
    }
  }
}
```

**Result**: Direct API calls to production backend, optimized for CDN deployment.

### Multi-Environment

```json
{
  "environments": {
    "development": {
      "mode": "unified",
      "apiUrl": "/api"
    },
    "staging": {
      "mode": "separate", 
      "apiUrl": "https://staging-api.yourdomain.com"
    },
    "production": {
      "mode": "separate",
      "apiUrl": "https://api.yourdomain.com"
    }
  }
}
```

Switch environments by changing `target`:

```python
# Deploy to staging
fluidkit.integrate(app, target="staging")
```

## Override Configuration

Override settings without modifying config files:

```python
# Temporary overrides
fluidkit.integrate(
    app,
    enable_fullstack=True,
    strategy="co-locate",
    target="staging"
)
```

Useful for:
- CI/CD pipelines
- Testing different configurations
- Environment-specific builds

## Server Configuration

### Backend Configuration

```json
{
  "backend": {
    "host": "localhost",
    "port": 8000
  }
}
```

### Frontend Configuration

```json
{
  "frontend": {
    "host": "localhost", 
    "port": 5173
  }
}
```

Used for:
- **Backend**: FastAPI server location for proxy target and direct communication
- **Frontend**: SvelteKit dev server location for unified mode server-side requests
- **Auto-generated URLs**: Environment-aware runtime generation
- **Local development**: Coordination between frontend and backend servers

## Best Practices

### Start Simple
```python
# Begin with minimal config
fluidkit.integrate(app)

# Upgrade when needed
fluidkit.integrate(app, enable_fullstack=True)
```

### Environment Separation
- **Development**: `unified` mode for seamless development
- **Production**: `separate` mode for scalability
- **Staging**: Match production architecture

### Output Strategy
- **Mirror**: Clean separation, better for teams
- **Co-locate**: Tighter integration, good for small projects

The configuration system grows with your project needs while maintaining backward compatibility and preserving customizations.
