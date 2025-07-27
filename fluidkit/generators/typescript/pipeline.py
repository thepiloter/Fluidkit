"""
FluidKit V2 Generation Pipeline

Orchestrates import generation, interface generation, and client wrapper generation
into complete TypeScript files with proper import statements.
"""

import json
from pathlib import Path
from typing import Dict, List, Union, Optional

from fluidkit.core.config import get_version
from fluidkit.core.config import FluidKitConfig
from fluidkit.core.schema import FluidKitApp, RouteNode, ModelNode
from fluidkit.generators.typescript.interfaces import generate_interface
from fluidkit.generators.typescript.clients import generate_client_wrapper
from fluidkit.generators.typescript.imports import ImportContext, generate_imports_for_file


def generate_typescript_files(
    fluid_app: FluidKitApp,
    config: FluidKitConfig,
    **runtime_config
) -> Dict[str, str]:
    """
    Generate complete TypeScript files from FluidKitApp using configuration.
    
    Args:
        fluid_app: Complete FluidKit app model
        config: FluidKit configuration object
        **runtime_config: Override runtime function names (for advanced use)
        
    Returns:
        Dict mapping file_path -> generated_content
    """
    # Set runtime defaults (can be overridden)
    runtime_config.setdefault('api_result_type', 'ApiResult')
    runtime_config.setdefault('get_base_url_fn', 'getBaseUrl')
    runtime_config.setdefault('handle_response_fn', 'handleResponse')

    project_root = fluid_app.metadata.get('project_root', str(Path.cwd().resolve()))
    
    # Load previous manifest and cleanup stale files
    previous_manifest = _load_previous_manifest(config, project_root)
    
    # Group nodes by their generated file locations
    files_to_generate = _group_nodes_by_generated_files(fluid_app, config, project_root)
    
    generated_files = {}
    
    # Generate TypeScript content files
    for ts_file_path, file_content in files_to_generate.items():
        content = _generate_file_content(
            file_content, 
            config, 
            project_root, 
            fluid_app,
            **runtime_config
        )
        
        if content.strip():
            generated_files[ts_file_path] = content
    
    # Generate FluidKit runtime with streaming support
    runtime_path = _get_runtime_file_path(config, project_root)
    generated_files[runtime_path] = _generate_fluidkit_runtime(config, fluid_app)
    
    # Generate proxy files for framework flow
    if config.should_generate_proxy:
        proxy_files = _generate_proxy_files(config, project_root)
        generated_files.update(proxy_files)

    # Create new manifest
    manifest = _create_generation_manifest(fluid_app, generated_files, config, project_root)
    manifest_path = str(Path(project_root) / config.output.location / ".manifest.json")
    generated_files[manifest_path] = json.dumps(manifest, indent=2)
    
    # Cleanup stale files after we know what we're generating
    if previous_manifest:
        _cleanup_stale_files(previous_manifest, generated_files)
    
    return generated_files


def _group_nodes_by_generated_files(
    fluid_app: FluidKitApp, 
    config: FluidKitConfig,
    project_root: str
) -> Dict[str, Dict[str, List[Union[RouteNode, ModelNode]]]]:
    """Group models and routes by their generated TypeScript file locations."""
    files_content = {}
    
    # Group models
    for model in fluid_app.models:
        ts_file_path = _get_generated_file_path(model.location, config, project_root)
        
        if ts_file_path not in files_content:
            files_content[ts_file_path] = {"models": [], "routes": []}
        files_content[ts_file_path]["models"].append(model)
    
    # Group routes
    for route in fluid_app.routes:
        ts_file_path = _get_generated_file_path(route.location, config, project_root)
        
        if ts_file_path not in files_content:
            files_content[ts_file_path] = {"models": [], "routes": []}
        files_content[ts_file_path]["routes"].append(route)
    
    return files_content


def _generate_file_content(
    file_content: Dict[str, List[Union[RouteNode, ModelNode]]],
    config: FluidKitConfig,
    project_root: str,
    fluid_app: FluidKitApp,
    **runtime_config
) -> str:
    """Generate complete TypeScript file content."""
    models = file_content["models"]
    routes = file_content["routes"]
    
    if not models and not routes:
        return ""

    all_nodes = models + routes
    source_location = all_nodes[0].location
    
    context = ImportContext(
        config=config,
        project_root=project_root,
        source_location=source_location,
    )
    
    # Check if we need runtime imports and collect used types
    needs_runtime = len(routes) > 0
    all_used_runtime_types = set()
    
    sections = []
    
    # Generate client wrappers and collect used types
    if routes:
        client_sections = []
        for route in routes:
            client_content, used_types = generate_client_wrapper(route, **runtime_config)
            if client_content:
                client_sections.append(client_content)
                all_used_runtime_types.update(used_types)
        
        imports = generate_imports_for_file(
            nodes=all_nodes,
            context=context,
            fluid_app=fluid_app,
            needs_runtime=needs_runtime,
            runtime_types_used=list(all_used_runtime_types),
            **runtime_config
        )
        if imports:
            sections.append(imports)
        
        if client_sections:
            sections.append("\n\n".join(client_sections))
    else:
        # No routes, just generate regular imports for models
        imports = generate_imports_for_file(
            nodes=all_nodes,
            context=context,
            fluid_app=fluid_app,
            needs_runtime=False,
            **runtime_config
        )
        if imports:
            sections.append(imports)
    
    # Generate interfaces
    if models:
        interface_sections = []
        for model in models:
            interface_content = generate_interface(model)
            if interface_content:
                interface_sections.append(interface_content)
        if interface_sections:
            sections.append("\n\n".join(interface_sections))
    
    return "\n\n".join(sections)


def _get_generated_file_path(location, config: FluidKitConfig, project_root: str) -> str:
    """Convert ModuleLocation to generated TypeScript file path using config."""
    if not location.file_path:
        raise ValueError(f"ModuleLocation {location.module_path} has no file_path")
    
    project_root_path = Path(project_root).resolve()
    py_file_path = Path(location.file_path).resolve()
    
    if config.output.strategy == "co-locate":
        return str(py_file_path.with_suffix('.ts'))
    elif config.output.strategy == "mirror":
        try:
            relative_to_project = py_file_path.relative_to(project_root_path)
            mirror_path = project_root_path / config.output.location / relative_to_project.with_suffix('.ts')
            return str(mirror_path)
        except ValueError:
            # Fallback if file is outside project
            return str(py_file_path.with_suffix('.ts'))
    else:
        raise ValueError(f"Unknown strategy: {config.output.strategy}")


def _get_runtime_file_path(config: FluidKitConfig, project_root: str) -> str:
    """Get the runtime.ts file path based on configuration."""
    runtime_dir = Path(project_root) / config.output.location
    return str(runtime_dir / "runtime.ts")


def _generate_fluidkit_runtime(config: FluidKitConfig, fluid_app: FluidKitApp) -> str:
    """Generate environment-aware FluidKit TypeScript runtime with streaming support."""
    
    # Check if we have any streaming routes
    has_streaming_routes = any(route.is_streaming for route in fluid_app.routes)
    
    # Generate base runtime
    base_runtime = _generate_base_runtime(config)
    
    # Add streaming runtime if needed
    if has_streaming_routes:
        streaming_runtime = _generate_streaming_runtime()
        return base_runtime + streaming_runtime
    else:
        return base_runtime


def _generate_base_runtime(config: FluidKitConfig) -> str:
    """Generate base FluidKit runtime utilities."""
    
    # Generate getBaseUrl function based on flow type
    if config.is_fullstack_config:
        base_url_fn = _generate_framework_aware_base_url(config)
    else:
        base_url_fn = _generate_normal_flow_base_url(config)

    common_types_exports = _generate_common_types_exports()
    
    return f'''/**
 * FluidKit Runtime Utilities
 * Auto-generated TypeScript utilities for FluidKit client wrappers
 */

export interface ApiResult<T = any> {{
  data?: T;
  error?: string;
  status: number;
  success: boolean;
}}

{common_types_exports}

{base_url_fn}

export async function handleResponse<T = any>(response: Response): Promise<ApiResult<T>> {{
  const status = response.status;
  const success = response.ok;
  
  if (!success) {{
    let error: string;
    try {{
      const errorBody = await response.json();
      error = errorBody.detail || errorBody.message || response.statusText;
    }} catch {{
      error = response.statusText || `HTTP ${{status}}`;
    }}
    return {{ error, status, success: false }};
  }}
  
  try {{
    const responseData = await response.json();
    return {{ data: responseData, status, success: true }};
  }} catch (e) {{
    return {{ 
      error: 'Failed to parse response JSON', 
      status, 
      success: false 
    }};
  }}
}}

'''


def _generate_common_types_exports() -> str:
    return '''// === COMMON EXTERNAL TYPES === //

export namespace FluidTypes {
  /**
   * UUID string type
   * @external Python uuid.UUID -> string
   */
  export type UUID = string;

  /**
   * Decimal number type  
   * @external Python decimal.Decimal -> number
   */
  export type Decimal = number;

  /**
   * DateTime string type (ISO format)
   * @external Python datetime.datetime -> string
   */
  export type DateTime = string;

  /**
   * Date string type (ISO format)
   * @external Python datetime.date -> string  
   */
  export type Date = string;

  /**
   * File path string type
   * @external Python pathlib.Path -> string
   */
  export type Path = string;

  /**
   * Email string type
   * @external Pydantic EmailStr -> string
   */
  export type EmailStr = string;

  /**
   * HTTP URL string type
   * @external Pydantic HttpUrl -> string
   */
  export type HttpUrl = string;

  /**
   * Payment card number string type
   * @external pydantic_extra_types.PaymentCardNumber -> string
   */
  export type PaymentCardNumber = string;
}

'''


def _generate_streaming_runtime() -> str:
    """Generate streaming-specific runtime utilities."""
    
    return '''
// === STREAMING TYPES AND UTILITIES === //

/**
 * Callbacks for Server-Sent Events (SSE) endpoints
 */
export interface SSECallbacks {
  onMessage?: (event: MessageEvent) => void;
  onError?: (event: Event) => void;
  onOpen?: (event: Event) => void;
  onClose?: () => void;
}

/**
 * SSE connection control interface
 */
export interface SSEConnection {
  close(): void;
  readyState: number;
  url: string;
  addEventListener(type: string, listener: EventListener): void;
  removeEventListener(type: string, listener: EventListener): void;
}

/**
 * Extended options for SSE connections
 */
export interface SSERequestInit extends EventSourceInit {
  headers?: Record<string, string>;
  timeout?: number;
  reconnectAttempts?: number;
  reconnectDelay?: number;
}

/**
 * Callbacks for JSON/data streaming endpoints
 */
export interface StreamingCallbacks<T> {
  onChunk?: (chunk: T) => void;
  onError?: (error: Error) => void;
  onComplete?: () => void;
}

/**
 * Callbacks for text streaming endpoints
 */
export interface TextStreamCallbacks {
  onChunk?: (text: string) => void;
  onError?: (error: Error) => void;
  onComplete?: () => void;
}
'''


def _generate_framework_aware_base_url(config: FluidKitConfig) -> str:
    """Generate getBaseUrl for framework flow with environment awareness."""
    target_env = config.get_environment(config.target)
    
    # Check if we need client/server detection
    has_unified_mode = any(
        env.mode == "unified" 
        for env in config.environments.values()
    )
    
    if has_unified_mode:
        # Framework flow with proxy detection
        return f'''export function getBaseUrl(): string {{
  // Detect if running in browser (client) vs server
  if (typeof window !== 'undefined') {{
    // Browser environment - use proxy routes
    return '{target_env.apiUrl}';
  }}
  
  // Server environment - direct communication
  return 'http://{config.backend.host}:{config.backend.port}';
}}'''
    else:
        # Framework flow but all separate mode
        return f'''export function getBaseUrl(): string {{
  // Production build - direct communication
  return '{target_env.apiUrl}';
}}'''


def _generate_normal_flow_base_url(config: FluidKitConfig) -> str:
    """Generate getBaseUrl for normal flow (simple URL switching)."""
    target_env = config.get_environment(config.target)
    
    return f'''export function getBaseUrl(): string {{
  // Using target environment: {config.target}
  return '{target_env.apiUrl}';
}}'''


def _generate_proxy_files(config: FluidKitConfig, project_root: str) -> Dict[str, str]:
    """Generate framework-specific proxy files for unified mode."""
    proxy_files = {}
    
    # Only generate proxy for target environment if it uses unified mode
    target_env = config.get_environment(config.target)
    if target_env.mode == "unified":
        if config.framework == "sveltekit":
            proxy_files.update(_generate_sveltekit_proxy(target_env, project_root, config))
        elif config.framework == "nextjs":
            proxy_files.update(_generate_nextjs_proxy(target_env, project_root, config))
    
    return proxy_files


def _generate_sveltekit_proxy(env_config, project_root: str, config: FluidKitConfig) -> Dict[str, str]:
    """Generate a transparent SvelteKit API proxy route."""
    # Extract API path from URL (e.g., "/api" -> "api")
    api_path = env_config.apiUrl.lstrip('/')
    
    # Generate proxy route path
    proxy_route_path = Path(project_root) / "src" / "routes" / api_path / "[...path]" / "+server.ts"
    
    proxy_content = f'''import type {{ RequestHandler, RequestEvent }} from '@sveltejs/kit';

const FASTAPI_URL = 'http://{config.backend.host}:{config.backend.port}';

// Only skip headers that would BREAK the request
const SKIP_HEADERS = new Set<string>([
    'host'  // Would point to SvelteKit instead of FastAPI
]);

/**
 * Transparent proxy - forwards requests to FastAPI as-is
 * Preserves: streaming, FormData, JSON, auth headers, CORS, etc.
 */
async function proxyRequest(event: RequestEvent): Promise<Response> {{
    const {{ params, request, url }} = event;
    const path = params.path || '';
    const backendUrl = `${{FASTAPI_URL}}/${{path}}${{url.search}}`;
    
    // Forward headers as-is (except problematic ones)
    const headers = new Headers();
    for (const [key, value] of request.headers) {{
        if (!SKIP_HEADERS.has(key.toLowerCase())) {{
            headers.set(key, value);
        }}
    }}
    
    try {{
        // Forward request exactly as received
        const response = await fetch(backendUrl, {{
            method: request.method,
            headers,
            body: request.body,      // Preserves FormData, JSON, binary, streams
            signal: request.signal   // Preserves cancellation
        }});
        
        // Optional development logging
        if (import.meta.env.DEV) {{
            console.log(`🔄 ${{request.method}} /{api_path}/${{path}} → ${{response.status}} ${{response.statusText}}`);
        }}
        
        // Return response exactly as received from FastAPI
        return response;
        
    }} catch (error) {{
        // Only catch NETWORK failures (server down, timeout, etc.)
        // HTTP 4xx/5xx errors are valid responses, not exceptions
        console.error('FastAPI network error:', {{
            url: backendUrl,
            method: request.method,
            error: error instanceof Error ? error.message : 'Unknown error'
        }});
        
        return new Response('Backend service unavailable', {{
            status: 502,
            statusText: 'Bad Gateway',
            headers: {{
                'Content-Type': 'text/plain'
            }}
        }});
    }}
}}

// All HTTP methods use the same transparent proxy logic
export const GET: RequestHandler = proxyRequest;
export const POST: RequestHandler = proxyRequest;
export const PUT: RequestHandler = proxyRequest;
export const PATCH: RequestHandler = proxyRequest;
export const DELETE: RequestHandler = proxyRequest;
export const OPTIONS: RequestHandler = proxyRequest;
export const HEAD: RequestHandler = proxyRequest;
'''

    return {str(proxy_route_path): proxy_content}


def _generate_nextjs_proxy(env_config, project_root: str, config: FluidKitConfig) -> Dict[str, str]:
    """Generate Next.js API proxy route."""
    # TODO: Implement Next.js proxy generation
    pass


def _load_previous_manifest(config: FluidKitConfig, project_root: str) -> Optional[Dict]:
    """Load previous generation manifest."""
    manifest_path = Path(project_root) / config.output.location / ".manifest.json"
    
    if manifest_path.exists():
        try:
            with open(manifest_path, 'r') as f:
                return json.load(f)
        except Exception:
            return None
    return None


def _cleanup_stale_files(previous_manifest: Dict, generated_files: Dict[str, str]):
    """Remove files that were generated previously but not in current generation."""
    current_files = set(generated_files.keys())
    previous_files = set(previous_manifest.get("generatedFiles", []))
    stale_files = previous_files - current_files
        
    for stale_file in stale_files:
        if not stale_file.endswith(".manifest.json"):
            path_obj = Path(stale_file)
            if path_obj.exists():
                try:
                    path_obj.unlink()
                except Exception:
                    pass


def _create_generation_manifest(
    fluid_app: FluidKitApp, 
    generated_files: Dict[str, str], 
    config: FluidKitConfig, 
    project_root: str
) -> Dict:
    """Create manifest tracking all generated files."""
    from datetime import datetime
    
    # Get auto-discovered files
    discovery_results = fluid_app.metadata.get('discovery_results', [])
    auto_discovered = [r['file'] for r in discovery_results]
    
    # Map source files to generated files
    source_to_generated = {}
    
    for model in fluid_app.models:
        if model.location.file_path:
            ts_file = _get_generated_file_path(model.location, config, project_root)
            source_to_generated[model.location.file_path] = [ts_file]
    
    for route in fluid_app.routes:
        if route.location.file_path:
            ts_file = _get_generated_file_path(route.location, config, project_root)
            if route.location.file_path not in source_to_generated:
                source_to_generated[route.location.file_path] = []
            if ts_file not in source_to_generated[route.location.file_path]:
                source_to_generated[route.location.file_path].append(ts_file)
    
    return {
        "version": get_version(),
        "lastGenerated": datetime.now().isoformat(),
        "sourceToGenerated": source_to_generated,
        "generatedFiles": list(generated_files.keys()),
        "autoDiscoveredFiles": auto_discovered,
        "hasStreamingRoutes": any(route.is_streaming for route in fluid_app.routes)
    }


# === TESTING HELPERS === #

def test_config_driven_generation():
    """Test the config-driven generation pipeline."""
    try:
        from tests.sample.app import app
        from fluidkit.core.integrator import integrate
        
        print("=== TESTING CONFIG-DRIVEN GENERATION WITH STREAMING ===")
        
        # Test normal flow
        print("\n1. Testing normal flow generation:")
        fluid_app, files = integrate(app)
        
        print(f"Generated {len(files)} files:")
        for file_path in sorted(files.keys()):
            print(f"  {Path(file_path).name}")
        
        # Test runtime content
        runtime_files = [f for f in files.keys() if 'runtime.ts' in f]
        if runtime_files:
            print("\n2. Runtime content preview:")
            runtime_content = files[runtime_files[0]]
            
            # Check for streaming support
            has_sse_types = 'SSECallbacks' in runtime_content
            has_streaming_types = 'StreamingCallbacks' in runtime_content
            
            print(f"   Has SSE types: {has_sse_types}")
            print(f"   Has streaming types: {has_streaming_types}")
            
            lines = runtime_content.split('\n')
            for i, line in enumerate(lines[:20]):
                print(f"   {i+1:2d}: {line}")
            if len(lines) > 20:
                print(f"       ... ({len(lines)-20} more lines)")
        
        print("\nConfig-driven generation with streaming support test passed!")
        
    except ImportError:
        print("Could not import test app")
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_config_driven_generation()
