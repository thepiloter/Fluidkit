"""
FluidKit Auto-Discovery System

Discovers files matching multiple patterns and automatically binds their APIRouters to FastAPI app.
Supports SvelteKit-style folder structures with parameter validation.
"""

import re
import sys
import inspect
import importlib.util
from pathlib import Path
from fnmatch import fnmatch
from fastapi.routing import APIRoute
from fastapi import FastAPI, APIRouter
from typing import List, Tuple, Dict, Any, Set, Optional

from fluidkit.core.config import FluidKitConfig


def auto_discover_and_bind_routes(app: FastAPI, config: FluidKitConfig, project_root: str, verbose: bool = False) -> List[Dict[str, Any]]:
    """
    Auto-discover files matching configured patterns and bind their APIRouters to FastAPI app.
    
    Args:
        app: FastAPI application instance
        config: FluidKit configuration
        project_root: Project root directory
        verbose: Enable detailed logging
        
    Returns:
        List of discovery info dictionaries
    """
    if not config.autoDiscovery.enabled:
        if verbose:
            print("Auto-discovery disabled in config")
        return []
    
    project_path = Path(project_root).resolve()
    discovered_files = _find_autodiscovery_files(project_path, config, verbose)
    
    discovery_results = []
    
    for file_path in discovered_files:
        try:
            # Import the module dynamically with proper context
            module, module_name = _import_file_with_context(file_path, project_path)
            
            # Find APIRouter instances
            routers = _find_routers_in_module(module)
            
            if not routers:
                if verbose:
                    print(f"No APIRouters found in {file_path}")
                continue
            
            # Extract path parameters from file structure
            path_parameters = _extract_path_parameters(file_path, project_path)
            auto_prefix = _calculate_auto_prefix(file_path, project_path)
            
            # Validate and bind each router
            for router_var_name, router_instance in routers:
                try:
                    # Validate router routes against path parameters
                    _validate_router_routes(router_instance, path_parameters, file_path, project_path)
                    
                    # Calculate final prefix and bind to app
                    final_prefix = _combine_prefixes(auto_prefix, getattr(router_instance, 'prefix', ''))
                    app.include_router(router_instance, prefix=final_prefix)
                    
                    discovery_results.append({
                        "file": str(file_path),
                        "module_name": module_name,
                        "router_var": router_var_name,
                        "routes": len(router_instance.routes),
                        "auto_prefix": auto_prefix,
                        "final_prefix": final_prefix
                    })
                    
                    if verbose:
                        readable_path = _decode_path_for_display(file_path, project_path)
                        print(f"Bound {router_var_name} from {readable_path} ({len(router_instance.routes)} routes) with prefix: {final_prefix}")
                
                except ValidationError as e:
                    readable_path = _decode_path_for_display(file_path, project_path)
                    raise ValidationError(f"Validation failed for {readable_path}: {e}") from e
        
        except Exception as e:
            readable_path = _decode_path_for_display(file_path, project_path)
            raise ImportError(f"Failed to process auto-discovered file {readable_path}: {e}") from e
    
    if discovery_results and not verbose:
        total_routers = len(discovery_results)
        total_routes = sum(r["routes"] for r in discovery_results)
        print(f"FluidKit: Auto-discovered {total_routers} routers with {total_routes} routes")
    
    return discovery_results


def _find_autodiscovery_files(project_path: Path, config: FluidKitConfig, verbose: bool = False) -> List[Path]:
    """Find files matching auto-discovery patterns."""
    candidates = []
    
    # Find files matching include patterns
    for include_pattern in config.include:
        if include_pattern.startswith('/'):
            search_path = Path(include_pattern[1:])
        else:
            search_path = project_path / include_pattern
        
        # Handle glob patterns
        if '*' in str(search_path):
            parts = search_path.parts
            base_parts = []
            pattern_parts = []
            found_wildcard = False
            
            for part in parts:
                if '*' in part or found_wildcard:
                    found_wildcard = True
                    pattern_parts.append(part)
                else:
                    base_parts.append(part)
            
            if base_parts:
                base_path = Path(*base_parts)
            else:
                base_path = project_path
            
            if base_path.exists():
                pattern = '/'.join(pattern_parts) if pattern_parts else '**/*.py'
                
                if '**' in pattern:
                    for file_path in base_path.rglob(pattern.replace('**/', '')):
                        if file_path.suffix == '.py':
                            candidates.append(file_path)
                else:
                    for file_path in base_path.glob(pattern):
                        if file_path.suffix == '.py':
                            candidates.append(file_path)
        else:
            if search_path.exists() and search_path.suffix == '.py':
                candidates.append(search_path)
    
    # Filter by auto-discovery file patterns (only x.y.py patterns, not x.y.z.py)
    pattern_matched = []
    for file_path in candidates:
        for pattern in config.autoDiscovery.filePatterns:
            if fnmatch(file_path.name, pattern):
                pattern_matched.append(file_path)
                break
    
    # Apply exclude patterns
    filtered_files = []
    for file_path in pattern_matched:
        excluded = False
        
        try:
            relative_path = str(file_path.relative_to(project_path))
        except ValueError:
            relative_path = str(file_path)
        
        for exclude_pattern in config.exclude:
            if fnmatch(relative_path, exclude_pattern) or fnmatch(file_path.name, exclude_pattern):
                excluded = True
                break
        
        if not excluded:
            filtered_files.append(file_path)
    
    if verbose and filtered_files:
        print(f"Found {len(filtered_files)} auto-discovery files:")
        for file_path in filtered_files:
            print(f"  {file_path}")
    
    return filtered_files


def _import_file_with_context(file_path: Path, project_path: Path) -> Tuple[Any, str]:
    """Import Python file with proper context for relative imports."""
    module_name = _encode_path_to_module_name(file_path, project_path)
    
    # Check if already loaded
    if module_name in sys.modules:
        return sys.modules[module_name], module_name
    
    # Set up import context
    file_dir = file_path.parent
    original_path = sys.path.copy()
    path_added = False
    
    # Add project root to sys.path for absolute imports
    project_root_str = str(project_path)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)
        path_added = True
    
    try:
        # Create module spec
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None:
            raise ImportError(f"Could not create spec for {file_path}")
        
        module = importlib.util.module_from_spec(spec)
        
        # Set up module context for relative imports
        module.__package__ = module_name.rpartition('.')[0] if '.' in module_name else None
        module.__fluidkit_source__ = str(file_path)
        module.__fluidkit_encoded_name__ = module_name
        
        # Register and execute
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        
        return module, module_name
        
    except ModuleNotFoundError as e:
        error_msg = str(e)
        if "No module named" in error_msg:
            readable_path = _decode_path_for_display(file_path, project_path)
            raise ImportError(
                f"Auto-discovered file '{readable_path}' contains relative imports that cannot be resolved. "
                f"Ensure all imports use absolute paths from project root. "
                f"Original error: {e}"
            ) from e
        raise
        
    finally:
        # Clean up sys.path
        if path_added and project_root_str in sys.path:
            sys.path.remove(project_root_str)


def _encode_path_to_module_name(file_path: Path, project_path: Path) -> str:
    """Encode file path using FluidKit convention."""
    try:
        relative_path = file_path.relative_to(project_path)
    except ValueError:
        relative_path = file_path
    
    encoded_parts = []
    for part in relative_path.parts:
        encoded_parts.append(_encode_element(part))
    
    return ".".join(encoded_parts)


def _encode_element(element: str) -> str:
    """Encode a single path element using FluidKit convention."""
    # Handle files (contains dots)
    if '.' in element and element.endswith('.py'):
        return element.replace('.', 'fkitDot')
    
    # Handle parameters [id] → fkit1Paramidfkit0Param
    if element.startswith('[') and element.endswith(']'):
        inner = element[1:-1]
        if inner.startswith('...'):
            # Rest parameter [...path] → fkit1Restpathfkit0Rest
            return f"fkit1Rest{inner[3:]}fkit0Rest"
        else:
            # Regular parameter [id] → fkit1Paramidfkit0Param
            return f"fkit1Param{inner}fkit0Param"
    
    # Handle groups (app) → fkit1Groupappfkit0Group
    if element.startswith('(') and element.endswith(')'):
        return f"fkit1Group{element[1:-1]}fkit0Group"
    
    # Check for unsupported characters
    unsupported_chars = ['*', '+', '?', '!', '@', '#', '$', '%', '^', '&']
    if any(char in element for char in unsupported_chars):
        raise ValueError(f"Unsupported characters in path element '{element}'. FluidKit only supports [param], [...rest], (group), and regular folder names.")
    
    # Regular folder - no encoding needed
    return element


def _decode_path_for_display(file_path: Path, project_path: Path) -> str:
    """Decode encoded path back to readable format for error messages."""
    try:
        return str(file_path.relative_to(project_path))
    except ValueError:
        return str(file_path)


def _extract_path_parameters(file_path: Path, project_path: Path) -> Set[str]:
    """Extract path parameters from folder structure."""
    try:
        relative_path = file_path.relative_to(project_path)
    except ValueError:
        return set()
    
    parameters = set()
    for part in relative_path.parts[:-1]:  # Exclude filename
        if part.startswith('[') and part.endswith(']'):
            inner = part[1:-1]
            if inner.startswith('...'):
                # Rest parameter [...path]
                parameters.add(inner[3:])
            else:
                # Regular parameter [id]
                parameters.add(inner)
    
    return parameters


def _calculate_auto_prefix(file_path: Path, project_path: Path) -> str:
    """Calculate auto-generated prefix from folder structure."""
    try:
        relative_path = file_path.relative_to(project_path)
    except ValueError:
        return ""
    
    prefix_parts = []
    for part in relative_path.parts[:-1]:  # Exclude filename
        if part.startswith('(') and part.endswith(')'):
            # Skip route groups - they don't affect URL
            continue
        elif part.startswith('[') and part.endswith(']'):
            inner = part[1:-1]
            if inner.startswith('...'):
                # Rest parameter [...path] → {path:path}
                prefix_parts.append(f"{{{inner[3:]}:path}}")
            else:
                # Regular parameter [id] → {id}
                prefix_parts.append(f"{{{inner}}}")
        else:
            # Regular folder
            prefix_parts.append(part)
    
    return "/" + "/".join(prefix_parts) if prefix_parts else ""


def _combine_prefixes(auto_prefix: str, router_prefix: str) -> str:
    """Combine auto-generated prefix with router prefix."""
    if not auto_prefix and not router_prefix:
        return ""
    if not auto_prefix:
        return router_prefix
    if not router_prefix:
        return auto_prefix
    
    # Ensure no double slashes
    combined = auto_prefix.rstrip('/') + '/' + router_prefix.lstrip('/')
    return combined.rstrip('/')


def _validate_router_routes(router: APIRouter, required_parameters: Set[str], file_path: Path, project_path: Path):
    """Validate that router routes have required path parameters."""
    if not required_parameters:
        return  # No validation needed
    
    for route in router.routes:
        if isinstance(route, APIRoute):
            endpoint = route.endpoint
            if not endpoint or not callable(endpoint):
                continue
            
            try:
                # Get function signature
                sig = inspect.signature(endpoint)
                function_params = set(sig.parameters.keys())
                
                # Remove common FastAPI parameters that aren't path parameters
                function_params.discard('request')
                function_params.discard('response')
                function_params.discard('background_tasks')
                
                # Check if all required parameters are present
                missing_params = required_parameters - function_params
                if missing_params:
                    readable_path = _decode_path_for_display(file_path, project_path)
                    raise ValidationError(
                        f"Function '{endpoint.__name__}' in {readable_path} missing required path parameters: {', '.join(missing_params)}. "
                        f"Path structure requires: {', '.join(required_parameters)}"
                    )
                    
            except Exception as e:
                if isinstance(e, ValidationError):
                    raise
                # If signature inspection fails, skip validation for this route
                continue


def _find_routers_in_module(module) -> List[Tuple[str, APIRouter]]:
    """Find all APIRouter instances in a module."""
    routers = []
    for attr_name in dir(module):
        if not attr_name.startswith('_'):
            try:
                attr_value = getattr(module, attr_name)
                if isinstance(attr_value, APIRouter):
                    routers.append((attr_name, attr_value))
            except Exception:
                continue
    return routers


class ValidationError(Exception):
    """Custom exception for route validation errors."""
    pass


# === TESTING HELPERS === #

def test_autodiscovery():
    """Test the enhanced auto-discovery system."""
    from fastapi import FastAPI
    from fluidkit.core.config import FluidKitConfig, AutoDiscoveryConfig
    
    print("=== TESTING ENHANCED AUTO-DISCOVERY ===")
    
    app = FastAPI()
    
    config = FluidKitConfig()
    config.autoDiscovery = AutoDiscoveryConfig(
        enabled=True, 
        filePatterns=["*.*.py"]
    )
    config.include = ["routes/**/*.py"]
    
    project_root = str(Path.cwd())
    
    print(f"Testing auto-discovery in: {project_root}")
    print(f"Include patterns: {config.include}")
    print(f"File patterns: {config.autoDiscovery.filePatterns}")
    
    try:
        results = auto_discover_and_bind_routes(app, config, project_root, verbose=True)
        
        print(f"\nDiscovery results: {len(results)} routers found")
        for result in results:
            print(f"  {result['file']} -> {result['router_var']} ({result['routes']} routes)")
            print(f"    Auto prefix: {result['auto_prefix']}")
            print(f"    Final prefix: {result['final_prefix']}")
        
        print(f"\nTotal FastAPI routes after auto-discovery: {len(app.routes)}")
        print("Enhanced auto-discovery test completed successfully!")
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_autodiscovery()
