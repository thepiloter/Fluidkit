# v2/generators/import_generator.py

"""
FluidKit V2 Import Generator

Pure code generation for TypeScript import statements with strategy awareness,
OS-independent path handling, and configurable FluidKit runtime imports.
"""

import os
from pathlib import Path
from dataclasses import dataclass
from typing import Union, Set, Dict, List, Optional

from fluidkit.core.schema import *
from fluidkit.core.constants import FluidKitRuntime


@dataclass
class ImportContext:
    """Context for import generation"""
    source_location: ModuleLocation
    strategy: str  # "co-locate" or "mirror" 
    project_root: str

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
    
    # Collect all referenced types from all nodes
    all_referenced_types: Set[str] = set()
    for node in nodes:
        all_referenced_types.update(node.get_referenced_types())
    
    # Resolve type locations (project types only)
    type_locations = {}
    for type_name in all_referenced_types:
        model = fluid_app.find_model_by_name(type_name)
        if model:  # Only project types will be found
            type_locations[type_name] = model.location
    
    # Generate type import statements
    type_imports = _generate_type_import_statements(type_locations, context)
    all_import_statements.extend(type_imports)
    
    # Generate runtime import statement if needed
    if needs_runtime:
        runtime_import = _generate_runtime_import_statement(context, **runtime_config)
        if runtime_import:
            all_import_statements.append(runtime_import)
    
    if all_import_statements:
        return '\n'.join(all_import_statements)
    else:
        return ''


def _generate_type_import_statements(
    type_locations: Dict[str, ModuleLocation],
    context: ImportContext
) -> List[str]:
    """Generate type import statements for project types."""
    if not type_locations:
        return []
    
    imports_by_path: Dict[str, List[str]] = {}
    
    for type_name, location in type_locations.items():
        import_path = _calculate_import_path(context.source_location, location, context)
        
        if import_path is None:  # Same file
            continue
        
        if import_path not in imports_by_path:
            imports_by_path[import_path] = []
        imports_by_path[import_path].append(type_name)
    
    import_statements = []
    for import_path in sorted(imports_by_path.keys()):
        types = sorted(imports_by_path[import_path])
        types_str = ', '.join(types)
        import_statements.append(f"import {{ {types_str} }} from '{import_path}';")
    
    return import_statements


def _generate_runtime_import_statement(
    context: ImportContext,
    api_result_type: str = FluidKitRuntime.API_RESULT_TYPE,
    get_base_url_fn: str = FluidKitRuntime.GET_BASE_URL_FN, 
    handle_response_fn: str = FluidKitRuntime.HANDLE_RESPONSE_FN
) -> Optional[str]:
    """Generate FluidKit runtime import statement."""
    runtime_path = _get_runtime_import_path(context)
    
    type_import = f"import type {{ {api_result_type} }} from '{runtime_path}';"
    value_import = f"import {{ {get_base_url_fn}, {handle_response_fn} }} from '{runtime_path}';"

    return f"{type_import}\n{value_import}"


def _calculate_import_path(
    source_location: ModuleLocation,
    target_location: ModuleLocation, 
    context: ImportContext
) -> Optional[str]:
    """Calculate relative import path between two project locations."""
    try:
        source_file = _get_generated_file_path(source_location, context.strategy, context.project_root)
        target_file = _get_generated_file_path(target_location, context.strategy, context.project_root)
        
        if source_file.resolve() == target_file.resolve():
            return None
        
        source_dir = source_file.parent
        
        import os
        relative_path = os.path.relpath(target_file, source_dir)
        relative_path = Path(relative_path).with_suffix('')
        import_path = str(relative_path).replace('\\', '/')
        
        if not import_path.startswith('../'):
            import_path = './' + import_path
        
        return import_path
        
    except Exception:
        return f"./{target_location.module_path.replace('.', '/')}"


def _get_runtime_import_path(context: ImportContext) -> str:
    """Get import path to FluidKit runtime."""
    try:
        source_file = _get_generated_file_path(context.source_location, context.strategy, context.project_root)
        runtime_file = Path(context.project_root).resolve() / '.fluidkit' / 'runtime.ts'
        
        source_dir = source_file.parent
        
        import os
        relative_path = os.path.relpath(runtime_file, source_dir)
        relative_path = Path(relative_path).with_suffix('')
        import_path = str(relative_path).replace('\\', '/')
        
        if not import_path.startswith('../'):
            import_path = './' + import_path
        
        return import_path
        
    except Exception:
        return '../.fluidkit/runtime'


def _get_generated_file_path(location: ModuleLocation, strategy: str, project_root: str) -> Path:
    """Convert ModuleLocation to generated TypeScript file path."""
    if not location.file_path:
        raise ValueError(f"ModuleLocation {location.module_path} has no file_path")
    
    project_root_path = Path(project_root).resolve()
    py_file_path = Path(location.file_path).resolve()
    
    if strategy == "co-locate":
        return py_file_path.with_suffix('.ts')
    elif strategy == "mirror":
        try:
            relative_to_project = py_file_path.relative_to(project_root_path)
            return project_root_path / '.fluidkit' / relative_to_project.with_suffix('.ts')
        except ValueError:
            return py_file_path.with_suffix('.ts')
    else:
        raise ValueError(f"Unknown strategy: {strategy}")


# === TESTING HELPERS === #

def test_import_generation():
    """Test import generation with various scenarios."""
    from fluidkit.core.schema import (
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
