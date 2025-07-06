# generators/pipeline.py
from pathlib import Path
from typing import Dict, List
from core.nodes import CompilationUnit, ImportRegistry
from generators.import_generator import generate_imports
from generators.interface_generator import generate_interface  
from generators.fetch_wrapper_generator import generate_fetch_wrapper

def generate_file(compilation_unit: CompilationUnit, import_registry: ImportRegistry) -> str:
    """
    Generate complete TypeScript file by orchestrating specialized generators.
    
    Args:
        compilation_unit: Single file's parsed content
        import_registry: Resolved symbol information
        
    Returns:
        Complete TypeScript file content
    """
    sections = []
    
    # 1. Generate ALL imports at the top
    import_sections = []
    
    # 1a. Dependencies from other files
    referenced_types = compilation_unit.get_all_referenced_types()
    if referenced_types:
        imports = generate_imports(compilation_unit, import_registry)
        if imports:
            import_sections.append(imports)
    
    # 1b. FluidKit runtime import (if we have routes)
    if compilation_unit.routes:
        runtime_import = _generate_fluidkit_runtime_import(compilation_unit.source_file, import_registry.project_root)
        import_sections.append(runtime_import)
    
    # Add all imports as first section
    if import_sections:
        sections.append("\n".join(import_sections))
    
    # 2. Generate interfaces (models)
    if compilation_unit.models:
        interface_sections = []
        for model in compilation_unit.models:
            interface_output = generate_interface(model)
            if interface_output:
                interface_sections.append(interface_output)
        if interface_sections:
            sections.append("\n\n".join(interface_sections))
    
    # 3. Generate fetch wrappers (routes) - NO IMPORT LOGIC HERE
    if compilation_unit.routes:
        fetch_sections = []
        for route in compilation_unit.routes:
            fetch_output = generate_fetch_wrapper(route)
            if fetch_output:
                fetch_sections.append(fetch_output)
        if fetch_sections:
            sections.append("\n\n".join(fetch_sections))
    
    return "\n\n".join(sections)


def _generate_fluidkit_runtime_import(source_file: str, project_root: str) -> str:
    """
    Generate FluidKit runtime import with correct relative path to .fluidkit/fluidkit.ts (OS-independent).
    
    Args:
        source_file: Current file path (e.g., "project/routes/users/page.py")
        project_root: Project root directory
        
    Returns:
        Import statement with correct relative path to .fluidkit/fluidkit.ts
    """
    try:
        # Convert paths to Path objects for OS-independent handling
        source_path = Path(source_file).resolve()
        project_root_path = Path(project_root).resolve()
        
        # Calculate where the generated TypeScript file will be
        relative_source = source_path.relative_to(project_root_path)
        ts_file_path = project_root_path / relative_source.with_suffix('.ts')
        
        # FluidKit runtime is at project_root/.fluidkit/fluidkit.ts
        runtime_path = project_root_path / '.fluidkit' / 'fluidkit.ts'
        
        # Calculate relative path from generated TS file to runtime
        ts_file_dir = ts_file_path.parent
        relative_to_runtime = runtime_path.relative_to(ts_file_dir)
        
        # Convert to TypeScript import format (remove .ts, normalize separators)
        import_path = str(relative_to_runtime.with_suffix(''))
        import_path = import_path.replace('\\', '/')  # Normalize for TypeScript
        
        # Add ./ prefix if needed (TypeScript requires explicit relative imports)
        if not import_path.startswith('../'):
            import_path = './' + import_path
        
        return f"import {{ ApiResult, getBaseUrl, handleResponse }} from '{import_path}';"
        
    except Exception as e:
        print(f"Warning: Failed to calculate FluidKit runtime import path: {e}")
        # Fallback to reasonable default
        return "import { ApiResult, getBaseUrl, handleResponse } from '../.fluidkit/fluidkit';"


def generate_project_files(validated_units: Dict[str, CompilationUnit], import_registry: ImportRegistry) -> Dict[str, str]:
    """
    Generate TypeScript files for all compilation units.
    
    Args:
        validated_units: All validated compilation units
        import_registry: Resolved symbol information
        
    Returns:
        Dict mapping output_file_path -> generated_content
    """
    generated_files = {}
    
    # Generate TypeScript file for each compilation unit
    for source_file, compilation_unit in validated_units.items():
        # Convert Python file path to TypeScript file path
        ts_file_path = _convert_py_to_ts_path(source_file, import_registry.project_root)
        
        # Generate file content
        ts_content = generate_file(compilation_unit, import_registry)
        
        if ts_content.strip():  # Only include non-empty files
            generated_files[ts_file_path] = ts_content
    
    # Always generate FluidKit runtime utilities in .fluidkit hidden folder
    runtime_path = str(Path(import_registry.project_root) / '.fluidkit' / 'fluidkit.ts')
    generated_files[runtime_path] = generate_fluidkit_runtime()
    
    return generated_files


def _convert_py_to_ts_path(py_file_path: str, project_root: str) -> str:
    """
    Convert Python file path to TypeScript file path (OS-independent).
    
    Args:
        py_file_path: Python source file path
        project_root: Project root directory
        
    Returns:
        TypeScript file path maintaining same relative structure
    """
    try:
        py_path = Path(py_file_path).resolve()
        project_root_path = Path(project_root).resolve()
        
        # Get relative path and convert extension
        relative_path = py_path.relative_to(project_root_path)
        ts_path = project_root_path / relative_path.with_suffix('.ts')
        
        return str(ts_path)
        
    except Exception as e:
        print(f"Warning: Failed to convert {py_file_path} to TypeScript path: {e}")
        # Fallback: just change extension
        return py_file_path.replace('.py', '.ts')


def generate_fluidkit_runtime() -> str:
    """Generate the FluidKit runtime utilities file."""
    return '''/**
 * FluidKit Runtime Utilities
 * Auto-generated TypeScript utilities for FluidKit fetch wrappers
 */

export interface ApiResult<T = any> {
  response?: T;           // Successful response data
  error?: string;         // Error message if request failed
  status: number;         // HTTP status code
  success: boolean;       // Convenience property
}

/**
 * Get base URL for API requests
 * Environment-aware: SvelteKit proxy in browser, direct FastAPI on server
 */
export function getBaseUrl(): string {
  if (typeof window !== 'undefined') {
    // Client-side: SvelteKit proxy
    return '/api';
  }
  // Server-side: Direct FastAPI
  return process.env.FASTAPI_URL || 'http://localhost:8000';
}

/**
 * Handle fetch response with typed error handling
 * Non-throwing approach for predictable error handling
 */
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
    return { response: responseData, status, success: true };
  } catch (e) {
    return { 
      error: 'Failed to parse response JSON', 
      status, 
      success: false 
    };
  }
}'''


# === COMPLETE FLUIDKIT PIPELINE ===

def generate_fluidkit_project(file_paths: List[str]) -> Dict[str, str]:
    """
    Complete FluidKit pipeline: Discovery → Resolution → Validation → Generation.
    
    Args:
        file_paths: List of Python files to process
        
    Returns:
        Dict mapping output_file_path -> generated_typescript_content
    """
    # Import the validation pipeline
    from transformers.validation_transformer import process_fluidkit_project
    from transformers.resolution_transformer import ImportResolver
    from transformers.discovery_transformer import DiscoveryTransformer
    
    # Stage 1-3: Discovery, Resolution, Validation
    print("Processing FluidKit project...")
    validated_units = process_fluidkit_project(file_paths)
    
    # Create import registry for generation stage
    resolver = ImportResolver(file_paths)
    # Re-run resolution to get fresh import_registry with project_root
    compilation_units = {}
    for file_path in file_paths:
        transformer = DiscoveryTransformer(file_path)
        with open(file_path, 'r') as f:
            code = f.read()
        compilation_units[file_path] = transformer.transform(code)
    
    import_registry = resolver.resolve(compilation_units)
    
    # Stage 4: TypeScript Generation
    print("Generating TypeScript files...")
    generated_files = generate_project_files(validated_units, import_registry)
    
    print(f"✅ Generated {len(generated_files)} TypeScript files")
    return generated_files

def write_generated_files(generated_files: Dict[str, str]) -> None:
    """
    Write generated TypeScript files to disk.
    
    Args:
        generated_files: Dict mapping file_path -> content
    """
    for file_path, content in generated_files.items():
        try:
            # Create directory if it doesn't exist
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Write file content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"📝 Generated: {file_path}")
            
        except Exception as e:
            print(f"❌ Failed to write {file_path}: {e}")


# === TESTING HELPER ===

def test_pipeline_with_project():
    """Test complete pipeline with real project files."""
    
    # Test with your existing test project
    file_paths = [
        "examples/test_project/main.py",
        "examples/test_project/models.py",
        "examples/test_project/shared/auth.py"
    ]
    
    # Generate all TypeScript files
    generated_files = generate_fluidkit_project(file_paths)
    
    # Print generated file paths and preview content
    print("\n=== GENERATED FILES ===")
    for file_path, content in generated_files.items():
        print(f"\n📁 {file_path}")
        print(f"📄 {len(content.splitlines())} lines")
        # Show first few lines as preview
        lines = content.splitlines()
        for i, line in enumerate(lines[:5]):
            print(f"   {i+1:2d}: {line}")
        if len(lines) > 5:
            print(f"   ... ({len(lines)-5} more lines)")
    
    return generated_files


if __name__ == "__main__":
    # Test the complete pipeline
    generated_files = test_pipeline_with_project()
    
    # Optionally write files to disk
    # write_generated_files(generated_files)
