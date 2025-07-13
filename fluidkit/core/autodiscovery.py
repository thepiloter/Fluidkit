"""
FluidKit Auto-Discovery System

Discovers +*.py files and automatically binds their APIRouters to FastAPI app.
"""

import sys
import hashlib
import importlib.util
from pathlib import Path
from fnmatch import fnmatch
from typing import List, Tuple, Dict, Any
from fastapi import FastAPI, APIRouter

from fluidkit.core.config import FluidKitConfig


def auto_discover_and_bind_routes(app: FastAPI, config: FluidKitConfig, project_root: str, verbose: bool = False) -> List[Dict[str, Any]]:
    """
    Auto-discover +*.py files and bind their APIRouters to FastAPI app.
    
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
            # Import the module dynamically
            module, module_name = _import_file_as_module(file_path, project_path)
            
            # Find APIRouter instances
            routers = _find_routers_in_module(module)
            
            if not routers:
                if verbose:
                    print(f"No APIRouters found in {file_path}")
                continue
            
            # Bind each router to FastAPI app (no prefix - predictable behavior)
            for router_var_name, router_instance in routers:
                app.include_router(router_instance)  # No prefix
                
                discovery_results.append({
                    "file": str(file_path),
                    "module_name": module_name,
                    "router_var": router_var_name,
                    "routes": len(router_instance.routes)
                })
                
                if verbose:
                    print(f"Bound {router_var_name} from {file_path} ({len(router_instance.routes)} routes)")
        
        except Exception as e:
            raise ImportError(f"Failed to import auto-discovered file {file_path}: {e}") from e
    
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
            # Absolute pattern
            search_path = Path(include_pattern[1:])
        else:
            # Relative to project root
            search_path = project_path / include_pattern
        
        # Handle glob patterns
        if '*' in str(search_path):
            # Extract base path and pattern
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
                
                # Use rglob for recursive patterns
                if '**' in pattern:
                    for file_path in base_path.rglob(pattern.replace('**/', '')):
                        if file_path.suffix == '.py':
                            candidates.append(file_path)
                else:
                    for file_path in base_path.glob(pattern):
                        if file_path.suffix == '.py':
                            candidates.append(file_path)
        else:
            # Direct path
            if search_path.exists() and search_path.suffix == '.py':
                candidates.append(search_path)
    
    # Filter by auto-discovery file pattern
    pattern_matched = []
    for file_path in candidates:
        if fnmatch(file_path.name, config.autoDiscovery.filePattern):
            pattern_matched.append(file_path)
    
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


def _import_file_as_module(file_path: Path, project_path: Path) -> Tuple[Any, str]:
    """Import Python file as module with readable unique name."""
    module_name = _file_path_to_module_name(file_path, project_path)
    
    # Check if already loaded (avoid re-import)
    if module_name in sys.modules:
        return sys.modules[module_name], module_name
    
    # Dynamic import
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None:
        raise ImportError(f"Could not create spec for {file_path}")
    
    module = importlib.util.module_from_spec(spec)
    
    # Add metadata for debugging
    module.__fluidkit_source__ = str(file_path)
    module.__fluidkit_hash__ = module_name.split('.')[-1]
    
    # Register and execute
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    
    return module, module_name


def _file_path_to_module_name(file_path: Path, project_path: Path) -> str:
    """Convert file path to readable, unique, consistent module name."""
    import re
    
    # Get relative path
    try:
        rel_path = file_path.relative_to(project_path)
    except ValueError:
        rel_path = file_path
    
    # Remove extension
    path_without_ext = rel_path.with_suffix('')
    
    # Sanitize each part
    sanitized_parts = []
    for part in path_without_ext.parts:
        # Remove special characters, keep alphanumeric
        clean_part = re.sub(r'[^\w]', '', part)  # Remove [, ], (, ), +, etc.
        
        # Ensure starts with letter if it starts with digit
        if clean_part and clean_part[0].isdigit():
            clean_part = f"m{clean_part}"
        
        if clean_part:  # Only add non-empty parts
            sanitized_parts.append(clean_part.lower())
    
    # Create base module name
    base_name = '.'.join(sanitized_parts) if sanitized_parts else 'unknown'
    
    # Generate consistent hash from original path
    original_path_str = str(rel_path)
    path_hash = hashlib.md5(original_path_str.encode()).hexdigest()[:8]
    
    # Combine: fluidkit.readable.name.hash
    return f"fluidkit.{base_name}.{path_hash}"


def _find_routers_in_module(module) -> List[Tuple[str, APIRouter]]:
    """Find all APIRouter instances in a module."""
    routers = []
    for attr_name in dir(module):
        if not attr_name.startswith('_'):  # Skip private attributes
            try:
                attr_value = getattr(module, attr_name)
                if isinstance(attr_value, APIRouter):
                    routers.append((attr_name, attr_value))
            except Exception:
                # Skip attributes that can't be accessed
                continue
    return routers


# === TESTING HELPERS === #

def test_autodiscovery():
    """Test the auto-discovery system."""
    from fastapi import FastAPI
    from fluidkit.core.config import FluidKitConfig, AutoDiscoveryConfig
    
    print("=== TESTING AUTO-DISCOVERY ===")
    
    app = FastAPI()
    
    # Test config with auto-discovery enabled
    config = FluidKitConfig()
    config.autoDiscovery = AutoDiscoveryConfig(enabled=True, filePattern="+*.py")
    config.include = ["src/**/*.py", "test/**/*.py"]
    
    project_root = str(Path.cwd())
    
    print(f"Testing auto-discovery in: {project_root}")
    print(f"Include patterns: {config.include}")
    print(f"File pattern: {config.autoDiscovery.filePattern}")
    
    # Run auto-discovery
    results = auto_discover_and_bind_routes(app, config, project_root, verbose=True)
    
    print(f"\nDiscovery results: {len(results)} routers found")
    for result in results:
        print(f"  {result['file']} -> {result['router_var']} ({result['routes']} routes)")
    
    print(f"\nTotal FastAPI routes after auto-discovery: {len(app.routes)}")
    
    print("\nAuto-discovery test completed!")


if __name__ == "__main__":
    test_autodiscovery()
