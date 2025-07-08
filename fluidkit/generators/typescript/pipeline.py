# v2/generators/pipeline.py

"""
FluidKit V2 Generation Pipeline

Orchestrates import generation, interface generation, and fetch wrapper generation
into complete TypeScript files with proper import statements.
"""

from pathlib import Path
from typing import Dict, List, Union

from fluidkit.core.schema import FluidKitApp, RouteNode, ModelNode
from fluidkit.core.constants import FluidKitRuntime, GenerationPaths
from fluidkit.generators.typescript.interfaces import generate_interface
from fluidkit.generators.typescript.clients import generate_fetch_wrapper
from fluidkit.generators.typescript.imports import ImportContext, generate_imports_for_file


def generate_typescript_files(
    fluid_app: FluidKitApp,
    strategy: str = "mirror",
    **runtime_config
) -> Dict[str, str]:
    """
    Generate complete TypeScript files from FluidKitApp.
    
    Simplified: Only generates project files, no external folder.
    """
    runtime_config.setdefault('api_result_type', FluidKitRuntime.API_RESULT_TYPE)
    runtime_config.setdefault('get_base_url_fn', FluidKitRuntime.GET_BASE_URL_FN)
    runtime_config.setdefault('handle_response_fn', FluidKitRuntime.HANDLE_RESPONSE_FN)

    project_root = str(Path.cwd().resolve())
    
    # Group nodes by their generated file locations
    files_to_generate = _group_nodes_by_generated_files(fluid_app, strategy, project_root)
    
    generated_files = {}
    
    for ts_file_path, file_content in files_to_generate.items():
        content = _generate_file_content(
            file_content, 
            strategy, 
            project_root, 
            fluid_app,
            **runtime_config
        )
        
        if content.strip():
            generated_files[ts_file_path] = content
    
    # Always generate FluidKit runtime
    runtime_path = str(Path.cwd() / GenerationPaths.FLUIDKIT_DIR / GenerationPaths.TYPESCRIPT_RUNTIME)
    generated_files[runtime_path] = _generate_fluidkit_runtime()
    
    return generated_files


def _group_nodes_by_generated_files(
    fluid_app: FluidKitApp, 
    strategy: str, 
    project_root: str
) -> Dict[str, Dict[str, List[Union[RouteNode, ModelNode]]]]:
    """Group models and routes by their generated TypeScript file locations."""
    files_content = {}
    
    for model in fluid_app.models:
        ts_file_path = _get_generated_file_path(model.location, strategy, project_root)
        
        if ts_file_path not in files_content:
            files_content[ts_file_path] = {"models": [], "routes": []}
        files_content[ts_file_path]["models"].append(model)
    
    for route in fluid_app.routes:
        ts_file_path = _get_generated_file_path(route.location, strategy, project_root)
        
        if ts_file_path not in files_content:
            files_content[ts_file_path] = {"models": [], "routes": []}
        files_content[ts_file_path]["routes"].append(route)
    
    return files_content


def _generate_file_content(
    file_content: Dict[str, List[Union[RouteNode, ModelNode]]],
    strategy: str,
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
        source_location=source_location,
        strategy=strategy,
        project_root=project_root
    )
    
    needs_runtime = len(routes) > 0
    
    sections = []
    
    # Generate imports
    imports = generate_imports_for_file(
        nodes=all_nodes,
        context=context,
        fluid_app=fluid_app,
        needs_runtime=needs_runtime,
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
    
    # Generate fetch wrappers
    if routes:
        fetch_sections = []
        for route in routes:
            fetch_content = generate_fetch_wrapper(route, **runtime_config)
            if fetch_content:
                fetch_sections.append(fetch_content)
        if fetch_sections:
            sections.append("\n\n".join(fetch_sections))
    
    return "\n\n".join(sections)


def _get_generated_file_path(location, strategy: str, project_root: str) -> str:
    """Convert ModuleLocation to generated TypeScript file path."""
    if not location.file_path:
        raise ValueError(f"ModuleLocation {location.module_path} has no file_path")
    
    project_root_path = Path(project_root).resolve()
    py_file_path = Path(location.file_path).resolve()
    
    if strategy == "co-locate":
        return str(py_file_path.with_suffix('.ts'))
    elif strategy == "mirror":
        try:
            relative_to_project = py_file_path.relative_to(project_root_path)
            return str(project_root_path / '.fluidkit' / relative_to_project.with_suffix('.ts'))
        except ValueError:
            return str(py_file_path.with_suffix('.ts'))
    else:
        raise ValueError(f"Unknown strategy: {strategy}")


def _generate_fluidkit_runtime() -> str:
    """Generate the FluidKit TypeScript runtime template."""
    return '''/**
 * FluidKit Runtime Utilities
 * Auto-generated TypeScript utilities for FluidKit fetch wrappers
 */

export interface ApiResult<T = any> {
  data?: T;
  error?: string;
  status: number;
  success: boolean;
}

export function getBaseUrl(): string {
  if (typeof window !== 'undefined') {
    return '/api';
  }
  return process.env.FASTAPI_URL || 'http://localhost:8000';
}

export async function handleResponse<T = any>(response: Response): Promise<ApiResult<T>> {
  const status = response.status;
  const success = response.ok;
  
  if (!success) {
    let error: string;
    try {
      const errorBody = await response.json();
      error = errorBody.detail || errorBody.message || response.statusText;
    } catch {
      error = response.statusText || `HTTP ${status}`;
    }
    return { error, status, success: false };
  }
  
  try {
    const responseData = await response.json();
    return { data: responseData, status, success: true };
  } catch (e) {
    return { 
      error: 'Failed to parse response JSON', 
      status, 
      success: false 
    };
  }
}'''

# === INTEGRATION WITH APP_INTEGRATOR === #

def integrate_with_generation(app, strategy: str = "mirror", **options):
    """
    Enhanced integrate function that includes TypeScript generation.
    
    Uses current working directory as project root.
    """
    from fluidkit.core.integrator import integrate
    
    # Step 1: Perform FluidKit introspection (pass None to use auto-detection)
    fluid_app = integrate(app, project_root=None, **options)
    
    # Step 2: Generate TypeScript files
    generated_files = generate_typescript_files(
        fluid_app=fluid_app,
        strategy=strategy,
        **options
    )
    
    # Step 3: Print generation summary
    project_root = Path.cwd()
    print(f"\n=== TYPESCRIPT GENERATION COMPLETE ===")
    print(f"Strategy: {strategy}")
    print(f"Project root: {project_root}")
    print(f"Generated {len(generated_files)} TypeScript files:")
    
    for file_path in sorted(generated_files.keys()):
        try:
            relative_path = Path(file_path).relative_to(project_root)
        except ValueError:
            relative_path = Path(file_path)  # Fallback to absolute
        
        content = generated_files[file_path]
        lines_count = len(content.splitlines())
        print(f"  📄 {relative_path} ({lines_count} lines)")
    
    return fluid_app, generated_files


# === TESTING FUNCTION === #

def test_with_examples():
    """Test the complete pipeline with examples in v2/examples directory"""
    import sys
    from pathlib import Path
    
    try:
        # Import the test FastAPI app from v2/examples
        from tests.sample.app import app
        
        print("=== TESTING COMPLETE PIPELINE ===")
        print(f"Working directory: {Path.cwd()}")
        
        # Test both strategies
        for strategy in ["co-locate", "mirror"]:
            print(f"\n--- Testing {strategy.upper()} Strategy ---")
            
            fluid_app, generated_files = integrate_with_generation(
                app=app,
                strategy=strategy
            )
            
            # Show preview of generated content
            print(f"\n📋 Content Preview for {strategy}:")
            for file_path, content in generated_files.items():
                try:
                    relative_path = Path(file_path).relative_to(Path.cwd())
                except ValueError:
                    relative_path = Path(file_path)
                
                print(f"\n--- {relative_path} ---")
                
                # Show first 10 lines of each file
                lines = content.splitlines()
                for i, line in enumerate(lines[:10]):
                    print(f"{i+1:2d}: {line}")
                if len(lines) > 10:
                    print(f"    ... ({len(lines)-10} more lines)")
        
    except ImportError as e:
        print(f"❌ Failed to import examples: {e}")
        print("Please ensure v2/examples/test.py and v2/examples/schema.py exist")
        print(f"Current directory: {Path.cwd()}")
        print("Looking for: v2.examples.test")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_with_examples()
