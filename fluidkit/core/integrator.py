"""
FluidKit V2 App Integration

Config-driven integration API for FluidKit with FastAPI applications with multi-language support.
Orchestrates route collection, model discovery, and optional code generation supporting both normal flow
(client generation only) and full-stack flow (framework + proxying).
"""

import logging
from pathlib import Path
from fastapi import FastAPI
from fastapi.routing import APIRoute
from typing import List, Dict, Tuple, Optional

from fluidkit.introspection.routes import route_to_node
from fluidkit.introspection.models import discover_models_from_routes
from fluidkit.core.schema import FluidKitApp, RouteNode, LanguageType
from fluidkit.core.autodiscovery import auto_discover_and_bind_routes
from fluidkit.core.config import load_fluidkit_config, ensure_config_for_mode, FluidKitConfig


logger = logging.getLogger(__name__)


def integrate(
    app: FastAPI,
    enable_fullstack: bool = False,
    lang: Optional[str] = None,
    project_root: Optional[str] = None,
    verbose: bool = False,
    **options
) -> Tuple[FluidKitApp, Dict[str, str]]:
    """
    Integrate FluidKit with FastAPI app for TypeScript client generation.
    
    Supports two modes:
    - Code Generation: Generates portable TypeScript clients for any project
    - Full-Stack: Generates clients + SvelteKit proxy routes for unified development
    
    Args:
        app: FastAPI application instance to introspect
        enable_fullstack: Whether to enable full-stack SvelteKit integration
            - False (default): Generates TypeScript clients only
            - True: Generates clients + SvelteKit proxy routes + auto-discovery
        lang: Target language for code generation (defaults to "typescript")
        project_root: Project root directory (defaults to current directory)
        verbose: Enable detailed logging output
        **options: Additional options for backward compatibility:
            - strategy: "mirror" | "co-locate" (overrides config)
            - target: "development" | "production" (overrides config)
            - framework: "sveltekit" (overrides config)
            - auto_discovery: bool (overrides config)
            
    Returns:
        Tuple[FluidKitApp, Dict[str, str]]: 
            - FluidKitApp: Complete introspection results
            - Dict[str, str]: Generated files mapping (file_path -> content)
            
    Config File Behavior:
        - If no fluid.config.json exists: Creates appropriate config based on enable_fullstack
        - If config exists and enable_fullstack=True: Upgrades config without losing customizations
        - If config exists and enable_fullstack=False: Uses existing config as-is
        
    Examples:
        # Code generation only (simple)
        fluidkit.integrate(app)
        # Creates: .fluidkit/runtime.ts + generated TypeScript clients
        
        # Full-stack development
        fluidkit.integrate(app, enable_fullstack=True)
        # Creates: clients + SvelteKit proxy routes + auto-discovery
        
        # Custom configuration
        fluidkit.integrate(app, strategy="co-locate", verbose=True)
        
        # Upgrade existing simple config to full-stack
        fluidkit.integrate(app, enable_fullstack=True)  # Preserves existing settings
        
    Raises:
        NotImplementedError: If unsupported language specified
        ValueError: If configuration validation fails
        
    Note:
        The integrate() function is idempotent - calling it multiple times is safe.
        Config upgrades preserve user customizations (ports, paths, etc.).
    """
    if verbose:
        logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
    
    # Determine project root
    if project_root is None:
        project_root = str(Path.cwd().resolve())
    else:
        project_root = str(Path(project_root).resolve())
    
    # Load FluidKit configuration
    config = ensure_config_for_mode(enable_fullstack, project_root)
    
    # Override config with explicit parameters (backward compatibility)
    config_overrides = {
        'target': options.pop('target', None),
        'strategy': options.pop('strategy', None),
        'framework': options.pop('framework', None),
        'auto_discovery': options.pop('auto_discovery', None),
    }

    # Apply config overrides
    if config_overrides['target']:
        config.target = config_overrides['target']
    if config_overrides['framework']:
        config.framework = config_overrides['framework']
    if config_overrides['strategy']:
        config.output.strategy = config_overrides['strategy']
    if config_overrides['auto_discovery'] is not None:
        config.autoDiscovery.enabled = config_overrides['auto_discovery']
    
    # Remaining options are runtime config
    runtime_config = options
    
    if verbose:
        logger.info("Starting FluidKit integration")
        logger.debug(f"Project root: {project_root}")
        logger.debug(f"Config framework: {config.framework}")
        logger.debug(f"Output strategy: {config.output.strategy}")
        logger.debug(f"Output location: {config.output.location}")
        logger.debug(f"Target: {config.target}")
        logger.debug(f"Auto-discovery enabled: {config.autoDiscovery.enabled}")
    
    # Auto-discover and bind routes BEFORE collecting existing routes
    discovery_results = auto_discover_and_bind_routes(app, config, project_root, verbose)
    
    # Collect and convert routes (now includes auto-discovered + manual routes)
    api_routes = _collect_fastapi_routes(app)
    route_nodes = _convert_routes_to_nodes(api_routes)
    
    # Discover models (project types only)
    model_nodes = discover_models_from_routes(route_nodes, project_root)
    
    # Build FluidKitApp
    fluid_app = FluidKitApp(
        models=model_nodes,
        routes=route_nodes,
        app_instance=app,
        metadata={
            'project_root': project_root,
            'config': config,
            'discovery_results': discovery_results,
            **runtime_config
        }
    )
    
    if verbose:
        logger.info(f"Introspection complete: {len(route_nodes)} routes, {len(model_nodes)} models")
        if discovery_results:
            logger.info(f"Auto-discovery: {len(discovery_results)} routers discovered")
    
    # Generate client code
    target_lang = lang or "typescript"
    normalized_lang = _normalize_language(target_lang)
    
    if normalized_lang == LanguageType.TYPESCRIPT:
        generated_files = _generate_and_write_typescript(fluid_app, config, verbose, **runtime_config)
        
        if not verbose:
            file_count = len(generated_files)
            flow_type = "full-stack" if config.is_fullstack_config else "normal"
            print(f"FluidKit: Generated {file_count} TypeScript files ({flow_type} flow)")
        
        return fluid_app, generated_files
    
    else:
        raise NotImplementedError(f"Language '{lang}' not yet supported. Currently supported: typescript")


def _generate_and_write_typescript(
    fluid_app: FluidKitApp, 
    config: FluidKitConfig,
    verbose: bool,
    **options
) -> Dict[str, str]:
    """Generate TypeScript files using configuration settings."""
    from fluidkit.generators.typescript.pipeline import generate_typescript_files
    
    # Pass config to generation pipeline
    generated_files = generate_typescript_files(
        fluid_app=fluid_app,
        config=config,
        **options
    )
    
    _write_generated_files(generated_files, verbose)
    return generated_files


def _write_generated_files(generated_files: Dict[str, str], verbose: bool):
    """Write generated files to disk with auto-generated headers."""
    for file_path, content in generated_files.items():
        try:
            file_path_obj = Path(file_path)
            file_path_obj.parent.mkdir(parents=True, exist_ok=True)
            
            if file_path_obj.name == ".manifest.json":
                final_content = content
            else:
                header = _get_file_header(file_path_obj.suffix)
                final_content = header + content
            
            with open(file_path_obj, 'w', encoding='utf-8') as f:
                f.write(final_content)
            
            if verbose:
                logger.debug(f"Generated: {file_path}")
            
        except Exception as e:
            error_msg = f"Failed to write {file_path}: {e}"
            if verbose:
                logger.error(error_msg)
            else:
                print(error_msg)


def _get_file_header(file_extension: str) -> str:
    """Get auto-generated file header based on file type."""
    if file_extension == '.ts':
        return '''/**
 * Auto-generated by FluidKit from FastAPI routes and models - DO NOT EDIT
 * Changes will be overwritten on regeneration.
 */

'''
    elif file_extension == '.py':
        return '''"""
Auto-generated by FluidKit from FastAPI routes and models - DO NOT EDIT
Changes will be overwritten on regeneration.
"""

'''
    else:
        return '''/**
 * Auto-generated by FluidKit from FastAPI routes and models - DO NOT EDIT
 * Changes will be overwritten on regeneration.
 */

'''


def _normalize_language(lang: str) -> LanguageType:
    """Normalize language string to LanguageType enum."""
    lang_lower = lang.lower()
    
    if lang_lower in ["ts", "typescript"]:
        return LanguageType.TYPESCRIPT
    else:
        valid_langs = ["ts", "typescript"]
        raise ValueError(f"Unsupported language '{lang}'. Supported: {', '.join(valid_langs)}")


def _collect_fastapi_routes(app: FastAPI) -> List[APIRoute]:
    """Collect user-defined API routes from FastAPI app."""
    user_routes = []
    
    for route in app.routes:
        if isinstance(route, APIRoute) and _is_user_defined_route(route):
            user_routes.append(route)
    
    return user_routes


def _convert_routes_to_nodes(api_routes: List[APIRoute]) -> List[RouteNode]:
    """Convert FastAPI APIRoute objects to RouteNode objects."""
    route_nodes = []
    
    for route in api_routes:
        try:
            route_node = route_to_node(route)
            if route_node:
                route_nodes.append(route_node)
        except Exception as e:
            logger.warning(f"Failed to convert route {route.path}: {e}")
            continue
    
    return route_nodes


def _is_user_defined_route(route: APIRoute) -> bool:
    """Determine if route is user-defined using module-based filtering."""
    endpoint = route.endpoint
    
    if (not endpoint or not callable(endpoint) or 
        not hasattr(endpoint, '__name__') or endpoint.__name__ == '<lambda>' or
        not hasattr(endpoint, '__module__') or not route.methods):
        return False
    
    endpoint_module = endpoint.__module__
    system_prefixes = ('fastapi.', 'starlette.')
    
    if any(endpoint_module.startswith(prefix) for prefix in system_prefixes):
        return False
    
    valid_methods = {'GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS', 'TRACE'}
    if not any(method in valid_methods for method in route.methods):
        return False
    
    if hasattr(endpoint, 'app') and hasattr(endpoint, '__call__'):
        return False
    
    return True


# === CONVENIENCE FUNCTIONS === #

def introspect_only(app: FastAPI, project_root: Optional[str] = None, **options) -> FluidKitApp:
    """Convenience function for introspection only (no code generation)."""
    if project_root is None:
        project_root = str(Path.cwd().resolve())
    
    # Load config for consistency
    config = load_fluidkit_config(project_root)
    
    # Auto-discover routes if enabled
    discovery_results = auto_discover_and_bind_routes(app, config, project_root, options.get('verbose', False))
    
    api_routes = _collect_fastapi_routes(app)
    route_nodes = _convert_routes_to_nodes(api_routes)
    model_nodes = discover_models_from_routes(route_nodes, project_root)
    
    fluid_app = FluidKitApp(
        models=model_nodes,
        routes=route_nodes,
        app_instance=app,
        metadata={'project_root': project_root, 'config': config, 'discovery_results': discovery_results, **options}
    )
    
    flow_type = "full-stack" if config.is_fullstack_config else "normal"
    print(f"FluidKit: Introspected {len(route_nodes)} routes, {len(model_nodes)} models ({flow_type} flow)")
    return fluid_app


def generate_only(
    app: FastAPI, 
    project_root: Optional[str] = None, 
    **options
) -> Dict[str, str]:
    """Convenience function to generate files without writing to disk."""
    from fluidkit.generators.typescript.pipeline import generate_typescript_files
    
    if project_root is None:
        project_root = str(Path.cwd().resolve())
    
    # Load config for generation settings
    config = load_fluidkit_config(project_root)
    
    # Auto-discover routes if enabled
    discovery_results = auto_discover_and_bind_routes(app, config, project_root, options.get('verbose', False))
    
    api_routes = _collect_fastapi_routes(app)
    route_nodes = _convert_routes_to_nodes(api_routes)
    model_nodes = discover_models_from_routes(route_nodes, project_root)
    
    fluid_app = FluidKitApp(
        models=model_nodes,
        routes=route_nodes,
        app_instance=app,
        metadata={'project_root': project_root, 'config': config, 'discovery_results': discovery_results, **options}
    )
    
    generated_files = generate_typescript_files(
        fluid_app=fluid_app,
        config=config,
        **options
    )
    
    flow_type = "full-stack" if config.is_fullstack_config else "normal"
    print(f"FluidKit: Generated {len(generated_files)} TypeScript files ({flow_type} flow) - not written to disk")
    return generated_files


# === TESTING FUNCTION === #

def test_integration():
    """Test the updated integration with config system."""
    try:
        from tests.sample.app import app
        
        print("=== FLUIDKIT CONFIG-DRIVEN INTEGRATION TEST ===")
        
        # Test 1: Normal flow (default config creation)
        print("\n1. Normal flow integration:")
        fluid_app, files = integrate(app)
        
        # Test 2: Auto-discovery enabled
        print("\n2. Auto-discovery integration:")
        fluid_app, files = integrate(app, auto_discovery=True, verbose=True)
        
        # Test 3: Introspection only
        print("\n3. Introspection only:")
        fluid_app = introspect_only(app)
        
        print("\nAll integration tests passed!")
        
    except ImportError:
        print("Could not import test app - ensure test files exist")
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_integration()
