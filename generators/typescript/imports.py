# v2/generators/import_generator.py

"""
FluidKit V2 Import Generator

Pure code generation for TypeScript import statements with strategy awareness,
OS-independent path handling, and configurable FluidKit runtime imports.
"""


from pathlib import Path
from dataclasses import dataclass
from typing import Union, Set, Dict, List, Optional

from core.constants import FluidKitRuntime
from core.schema import RouteNode, ModelNode, ModuleLocation, FluidKitApp


@dataclass
class ImportContext:
    """Context for import generation"""
    source_location: ModuleLocation
    strategy: str  # "co-locate" or "mirror" 
    project_root: str


def analyze_node_references(node: Union[RouteNode, ModelNode]) -> Set[str]:
    """
    Extract all custom type names referenced by a node.
    
    Args:
        node: RouteNode or ModelNode to analyze
        
    Returns:
        Set of custom type names (e.g., {"User", "UserStatus"})
    """
    return node.get_referenced_types()


def resolve_type_locations(
    referenced_types: Set[str], 
    fluid_app: FluidKitApp
) -> Dict[str, ModuleLocation]:
    """
    Map type names to their source locations.
    
    Args:
        referenced_types: Set of type names to resolve
        fluid_app: FluidKitApp containing all discovered models
        
    Returns:
        Dict mapping type_name -> ModuleLocation where it's defined
    """
    type_locations = {}
    
    for type_name in referenced_types:
        model = fluid_app.find_model_by_name(type_name)
        if model:
            type_locations[type_name] = model.location
        # Skip types that aren't found (external types become 'any')
    
    return type_locations


def get_generated_file_path(location: ModuleLocation, strategy: str, project_root: str) -> Path:
    """
    Convert ModuleLocation to actual generated TypeScript file path (OS-independent).
    
    Args:
        location: Source module location
        strategy: "co-locate" or "mirror"
        project_root: Project root directory
        
    Returns:
        Absolute path to generated TypeScript file
    """
    if not location.file_path:
        raise ValueError(f"ModuleLocation {location.module_path} has no file_path")
    
    project_root_path = Path(project_root).resolve()
    py_file_path = Path(location.file_path).resolve()
    
    if strategy == "co-locate":
        # .py file → .ts file in same location
        return py_file_path.with_suffix('.ts')
    
    elif strategy == "mirror":
        # .py file → .ts file in .fluidkit mirror structure
        try:
            relative_to_project = py_file_path.relative_to(project_root_path)
            return project_root_path / '.fluidkit' / relative_to_project.with_suffix('.ts')
        except ValueError:
            # File is outside project root - fallback to co-locate
            return py_file_path.with_suffix('.ts')
    
    else:
        raise ValueError(f"Unknown strategy: {strategy}")


def calculate_import_path(
    source_location: ModuleLocation,
    target_location: ModuleLocation, 
    context: ImportContext
) -> Optional[str]:
    """
    Calculate relative import path between two locations (strategy-aware, OS-independent).
    
    Returns None if types are in same file (no import needed).
    """
    try:
        # Get generated file paths for both locations
        source_file = get_generated_file_path(source_location, context.strategy, context.project_root)
        target_file = get_generated_file_path(target_location, context.strategy, context.project_root)
        
        # Same file detection
        if source_file.resolve() == target_file.resolve():
            return None
        
        # Calculate relative path from source directory to target file
        source_dir = source_file.parent
        
        # Use os.path.relpath for proper relative path calculation (works with any paths)
        import os
        relative_path = os.path.relpath(target_file, source_dir)
        
        # Convert to Path object and remove extension
        relative_path = Path(relative_path).with_suffix('')
        
        # Convert to TypeScript import format
        import_path = str(relative_path).replace('\\', '/')
        
        # Add ./ prefix if needed (TypeScript requires explicit relative imports)
        if not import_path.startswith('../'):
            import_path = './' + import_path
        
        return import_path
        
    except (ValueError, OSError) as e:
        # Fallback: use module-based path if file path calculation fails
        print(f"Warning: Failed to calculate import path, using module fallback: {e}")
        return f"./{target_location.module_path.replace('.', '/')}"


def get_fluidkit_runtime_path(context: ImportContext) -> str:
    """
    Get import path to FluidKit runtime from source location.
    
    Runtime is always at .fluidkit/runtime.ts for both strategies.
    """
    try:
        source_file = get_generated_file_path(context.source_location, context.strategy, context.project_root)
        runtime_file = Path(context.project_root).resolve() / '.fluidkit' / 'runtime.ts'
        
        # Calculate relative path from source directory to runtime
        source_dir = source_file.parent
        
        # Use os.path.relpath for proper relative path calculation
        import os
        relative_path = os.path.relpath(runtime_file, source_dir)
        
        # Convert to Path object and remove extension
        relative_path = Path(relative_path).with_suffix('')
        
        # Convert to TypeScript import format
        import_path = str(relative_path).replace('\\', '/')
        
        # Add ./ prefix if needed
        if not import_path.startswith('../'):
            import_path = './' + import_path
        
        return import_path
        
    except (ValueError, OSError) as e:
        # Fallback to reasonable default
        print(f"Warning: Failed to calculate runtime path, using fallback: {e}")
        return './.fluidkit/runtime'


def generate_type_import_statements(
    type_locations: Dict[str, ModuleLocation],
    context: ImportContext
) -> List[str]:
    """
    Generate type import statements with barrel imports.
    
    Args:
        type_locations: Dict mapping type_name -> ModuleLocation
        context: Import generation context
        
    Returns:
        List of import statements like ["import { User, UserStatus } from './models/user';"]
    """
    if not type_locations:
        return []
    
    # Group types by their import paths (barrel imports)
    imports_by_path: Dict[str, List[str]] = {}
    
    for type_name, location in type_locations.items():
        import_path = calculate_import_path(context.source_location, location, context)
        
        # Skip if same file (no import needed)
        if import_path is None:
            continue
        
        if import_path not in imports_by_path:
            imports_by_path[import_path] = []
        imports_by_path[import_path].append(type_name)
    
    # Generate import statements
    import_statements = []
    for import_path in sorted(imports_by_path.keys()):
        types = sorted(imports_by_path[import_path])  # Alphabetical order
        types_str = ', '.join(types)
        import_statements.append(f"import {{ {types_str} }} from '{import_path}';")
    
    return import_statements


def generate_runtime_import_statement(
    context: ImportContext,
    api_result_type: str = FluidKitRuntime.API_RESULT_TYPE,
    get_base_url_fn: str = FluidKitRuntime.GET_BASE_URL_FN, 
    handle_response_fn: str = FluidKitRuntime.HANDLE_RESPONSE_FN
) -> Optional[str]:
    """
    Generate FluidKit runtime import statement.
    
    Returns None if runtime imports not needed for this context.
    """
    runtime_path = get_fluidkit_runtime_path(context)
    
    # Create import statement with configurable names
    runtime_imports = [api_result_type, get_base_url_fn, handle_response_fn]
    runtime_imports_str = ', '.join(runtime_imports)
    
    return f"import {{ {runtime_imports_str} }} from '{runtime_path}';"


def generate_imports_for_file(
    nodes: List[Union[RouteNode, ModelNode]],
    context: ImportContext,
    fluid_app: FluidKitApp,
    needs_runtime: bool = False,
    **runtime_config
) -> str:
    """
    Main function: Generate complete import block for a TypeScript file.
    
    Args:
        nodes: List of RouteNode/ModelNode that will be in this file
        context: Import generation context  
        fluid_app: Complete app model for type resolution
        needs_runtime: Whether to include FluidKit runtime imports
        **runtime_config: api_result_type, get_base_url_fn, handle_response_fn
        
    Returns:
        Complete import statements as string (empty if no imports needed)
    """
    all_import_statements = []
    
    # 1. Collect all referenced types from all nodes
    all_referenced_types: Set[str] = set()
    for node in nodes:
        all_referenced_types.update(analyze_node_references(node))
    
    # 2. Resolve type locations
    type_locations = resolve_type_locations(all_referenced_types, fluid_app)
    
    # 3. Generate type import statements
    type_imports = generate_type_import_statements(type_locations, context)
    all_import_statements.extend(type_imports)
    
    # 4. Generate runtime import statement if needed
    if needs_runtime:
        runtime_import = generate_runtime_import_statement(context, **runtime_config)
        if runtime_import:
            all_import_statements.append(runtime_import)
    
    # 5. Join all imports with newlines
    if all_import_statements:
        return '\n'.join(all_import_statements)
    else:
        return ''


# === TESTING HELPERS === #

def test_import_generation():
    """Test import generation with various scenarios."""
    from core.schema import (
        RouteNode, ModelNode, Field, FieldAnnotation, ModuleLocation, 
        FluidKitApp, BaseType, ParameterType, FieldConstraints
    )
    
    # Create test locations
    route_location = ModuleLocation(
        module_path="routes.users.page", 
        file_path="/project/routes/users/page.py"
    )
    
    model_location = ModuleLocation(
        module_path="models.user",
        file_path="/project/models/user.py"
    )
    
    # Create test models
    user_model = ModelNode(
        name="User",
        fields=[],
        location=model_location
    )
    
    # Create test route that references User
    route = RouteNode(
        name="getUser",
        methods=["GET"],
        path="/users/{id}",
        parameters=[
            Field(
                name="id",
                annotation=FieldAnnotation(base_type=BaseType.NUMBER),
                constraints=FieldConstraints(parameter_type=ParameterType.PATH)
            )
        ],
        location=route_location,
        return_type=FieldAnnotation(custom_type="User")
    )
    
    # Create FluidKitApp
    fluid_app = FluidKitApp(models=[user_model], routes=[route])
    
    # Test both strategies
    strategies = ["co-locate", "mirror"]
    
    for strategy in strategies:
        print(f"\n=== Testing {strategy.upper()} Strategy ===")
        
        context = ImportContext(
            source_location=route_location,
            strategy=strategy,
            project_root="/project"
        )
        
        # Test type imports only
        print("Type imports only:")
        imports = generate_imports_for_file(
            nodes=[route],
            context=context,
            fluid_app=fluid_app,
            needs_runtime=False
        )
        print(imports or "(no imports needed)")
        
        # Test with runtime imports
        print("\nWith runtime imports:")
        imports = generate_imports_for_file(
            nodes=[route],
            context=context,
            fluid_app=fluid_app,
            needs_runtime=True
        )
        print(imports)
        
        # Test with custom runtime names
        print("\nWith custom runtime names:")
        imports = generate_imports_for_file(
            nodes=[route],
            context=context,
            fluid_app=fluid_app,
            needs_runtime=True,
            api_result_type="CustomApiResult",
            get_base_url_fn="customGetBaseUrl",
            handle_response_fn="customHandleResponse"
        )
        print(imports)
    
    # Test same-file scenario
    print(f"\n=== Testing Same-File Scenario ===")
    same_file_context = ImportContext(
        source_location=model_location,  # Model importing from its own file
        strategy="co-locate",
        project_root="/project"
    )
    
    imports = generate_imports_for_file(
        nodes=[user_model],  # User model in its own file
        context=same_file_context,
        fluid_app=fluid_app,
        needs_runtime=False
    )
    print(imports or "(no imports needed - same file)")


if __name__ == "__main__":
    test_import_generation()
