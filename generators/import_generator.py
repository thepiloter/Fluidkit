from pathlib import Path
from typing import Dict, Set
from core.nodes import CompilationUnit, ImportRegistry

def generate_imports(compilation_unit: CompilationUnit, import_registry: ImportRegistry) -> str:
    """
    Generate import statements for a single file's dependencies.
    
    Args:
        compilation_unit: Single file's parsed content
        import_registry: Resolved symbol information across project
        
    Returns:
        TypeScript import statements as string, or empty string if no imports needed
    """
    
    # Find all custom types referenced in this compilation unit
    referenced_types = compilation_unit.get_all_referenced_types()
    
    # Find types defined locally (don't need to import these)
    local_types = compilation_unit.get_exported_types()
    
    # Types we need to import = referenced - local
    types_to_import = referenced_types - local_types
    
    if not types_to_import:
        return ""
    
    # Group imports by source module using file-scoped resolution
    imports_by_module: Dict[str, Set[str]] = {}
    source_file = compilation_unit.source_file
    
    for type_name in types_to_import:
        if _should_exclude_from_imports(type_name, import_registry):
            continue
        resolved_symbol = import_registry.resolve_symbol_in_file(type_name, source_file)
        if resolved_symbol:
            # Convert Python module path to TypeScript import path
            module_path = resolved_symbol.full_path.rsplit('.', 1)[0]  # "models.user.User" -> "models.user"
            ts_import_path = _convert_module_to_ts_import_path(module_path, source_file, import_registry.project_root)
            
            if ts_import_path:
                if ts_import_path not in imports_by_module:
                    imports_by_module[ts_import_path] = set()
                imports_by_module[ts_import_path].add(type_name)
    
    if not imports_by_module:
        return ""
    
    # Generate import statements using list operations
    import_lines = []
    
    for import_path in sorted(imports_by_module.keys()):
        symbols = imports_by_module[import_path]
        symbols_str = ", ".join(sorted(symbols))
        import_lines.append(f"import {{ {symbols_str} }} from '{import_path}';")
    
    return "\n".join(import_lines)

def _should_exclude_from_imports(type_name: str, import_registry: ImportRegistry) -> bool:
    """Exclude Python runtime types that shouldn't appear in TypeScript."""
    # python_runtime_types = {"BaseModel", "Field", "Depends", "Query", "Path", "Body", "Header"}
    python_runtime_types = {"BaseModel"}
    return type_name in python_runtime_types

def _convert_module_to_ts_import_path(module_path: str, current_file: str, project_root: str) -> str:
    """
    Convert Python module path to TypeScript import path.
    
    Args:
        module_path: Python module path like "models.user" or "shared.auth"
        current_file: Current file path (for relative imports)
        project_root: Project root directory
        
    Returns:
        TypeScript import path like "./models/user" or "../shared/auth"
    """
    if not module_path:
        return ""
    
    try:
        # Convert module path to file system path
        project_root_path = Path(project_root)
        current_file_path = Path(current_file)
        
        # Build target file path from module parts
        module_parts = module_path.split('.')
        target_file_path = project_root_path
        for part in module_parts:
            target_file_path = target_file_path / part
        
        # Add .ts extension (assuming generated TypeScript files)
        target_file_path = target_file_path.with_suffix('.ts')
        
        # Calculate relative path from current file to target file
        try:
            current_dir = current_file_path.parent
            relative_path = target_file_path.relative_to(current_dir)
            
            # Convert to TypeScript import format
            ts_path = str(relative_path.with_suffix(''))  # Remove .ts extension
            ts_path = ts_path.replace('\\', '/')  # Normalize separators
            
            # Add ./ prefix if it doesn't start with ../
            if not ts_path.startswith('../'):
                ts_path = './' + ts_path
            
            return ts_path
            
        except ValueError:
            # Files are not in relative path relationship, use absolute module path
            # Convert to relative from project root
            try:
                relative_to_project = target_file_path.relative_to(project_root_path)
                ts_path = str(relative_to_project.with_suffix(''))
                ts_path = ts_path.replace('\\', '/')
                return './' + ts_path
            except ValueError:
                return ""
    
    except Exception as e:
        print(f"Warning: Failed to convert module path {module_path} to TypeScript import: {e}")
        return ""

# === TESTING HELPER ===
def test_generate_imports():
    """Simple test for import generation"""
    
    # Create a mock CompilationUnit
    from core.nodes import CompilationUnit, ModelNode, Field, FieldAnnotation, BaseType, SourceLocation, ImportRegistry, ResolvedSymbol
    
    # Mock a model that references "User" and "Product" types
    user_field = Field(
        name="user", 
        annotation=FieldAnnotation(custom_type="User")
    )
    product_field = Field(
        name="product",
        annotation=FieldAnnotation(custom_type="Product") 
    )
    
    # Model that references external types
    order_model = ModelNode(
        name="Order",
        fields=[user_field, product_field],
        location=SourceLocation(file="test.py", line=1, column=0),
        ast_node=None
    )
    
    unit = CompilationUnit(
        models=[order_model],
        routes=[],
        imports=[],
        source_file="examples/test_project/orders.py"
    )
    
    # Mock ImportRegistry with file-scoped symbols
    import_registry = ImportRegistry(
        symbols={},
        file_symbols={
            "examples/test_project/orders.py": {
                "User": ResolvedSymbol(
                    name="User",
                    full_path="models.User", 
                    source_file="examples/test_project/models.py"
                ),
                "Product": ResolvedSymbol(
                    name="Product", 
                    full_path="models.Product",
                    source_file="examples/test_project/models.py"
                )
            }
        },
        modules={},
        fastapi_symbols=set(),
        pydantic_symbols=set(),
        project_root="examples/test_project"
    )
    
    # Test the function
    result = generate_imports(unit, import_registry)
    
    print("=== IMPORT GENERATION TEST ===")
    print(f"Source file: {unit.source_file}")
    print(f"Referenced types: {unit.get_all_referenced_types()}")
    print(f"Local types: {unit.get_exported_types()}")
    print("\nGenerated imports:")
    print(result)
    print("=" * 30)

# Run the test
if __name__ == "__main__":
    test_generate_imports()