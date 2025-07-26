import sys, ast
import importlib.util
import importlib.metadata
from pathlib import Path
from dataclasses import dataclass
from typing import Literal, Optional, List, Any

from fluidkit.core.schema import ContainerType, FieldAnnotation, ModuleLocation


ModuleType = Literal['project', 'external', 'builtin', 'not_found']


@dataclass
class ModuleInfo:
    """Complete module classification information."""
    name: str
    type: ModuleType
    project_root: str
    path: Optional[str] = None
    relative_path: Optional[str] = None
    package_name: Optional[str] = None
    version: Optional[str] = None
    error: Optional[str] = None


class FunctionReturnDetector(ast.NodeVisitor):
    """
    Scope-aware AST visitor that finds return statements belonging to a specific function.
    
    Handles nested functions properly by tracking function scope entry/exit.
    """
    
    def __init__(self, target_function_name: str):
        self.target_function_name = target_function_name
        self.returns = []
        self.in_target_function = False
    
    def visit_FunctionDef(self, node):
        self._visit_function(node)
    
    def visit_AsyncFunctionDef(self, node):
        self._visit_function(node)
    
    def _visit_function(self, node):
        if node.name == self.target_function_name:
            # Entering target function scope
            old_state = self.in_target_function
            self.in_target_function = True
            self.generic_visit(node)  # Visit children
            self.in_target_function = old_state
        else:
            # Different function - don't enter its scope
            pass
    
    def visit_Return(self, node):
        if self.in_target_function:
            self.returns.append(node)


def find_function_returns(func) -> list:
    """
    Find all return statements that belong to a specific function using scope-aware AST analysis.
    
    Args:
        func: Function to analyze
        
    Returns:
        List of ast.Return nodes that belong to the function
    """
    import inspect
    
    try:
        source = inspect.getsource(func)
        tree = ast.parse(source)
        
        detector = FunctionReturnDetector(func.__name__)
        detector.visit(tree)
        
        return detector.returns
    except Exception:
        return []


def classify_module(module_name: str, project_root: Optional[str] = None) -> ModuleType:
    """
    Classify module type for FluidKit introspection strategy.
    
    Args:
        module_name: Python module name (e.g., 'pydantic.main')
        project_root: Project root directory (defaults to current working directory)
    
    Returns:
        'project' - Local project code (full introspection)
        'external' - Installed packages (one-layer introspection) 
        'builtin' - Built-ins/stdlib (use 'any' type)
        'not_found' - Module doesn't exist
    """
    if project_root is None:
        project_root = Path.cwd().resolve()
    else:
        project_root = Path(project_root).resolve()
    
    # 1. Check builtin modules
    if module_name in sys.builtin_module_names:
        return 'builtin'
    
    # 2. Special case for __main__ - context-aware detection
    if module_name == '__main__':
        try:
            import __main__
            if hasattr(__main__, '__file__') and __main__.__file__:
                main_file = Path(__main__.__file__).resolve()
                
                # Check if main script is within project boundaries
                try:
                    main_file.relative_to(project_root)
                    
                    # Additional validation: ensure it's not in external paths via sys.path
                    if not _is_external_via_syspath(main_file, project_root):
                        return 'project'
                except ValueError:
                    # Main script is outside project root
                    pass
        except (AttributeError, OSError):
            # Can't determine main file location
            pass
        
        # If we can't validate __main__ as project code, treat as external
        return 'external'
    
    # 3. Get module spec using Python's import mechanism
    try:
        spec = importlib.util.find_spec(module_name)
    except (ImportError, ValueError, ModuleNotFoundError):
        return 'not_found'
    
    if spec is None:
        return 'not_found'
    
    # 4. Check if it's an installed package (most reliable for external detection)
    if _is_installed_package(module_name):
        return 'external'
    
    # 5. Handle modules with file origins
    if spec.origin:
        module_path = Path(spec.origin).resolve()
        
        # Check if it's part of Python standard library
        if _is_stdlib_module(module_path):
            return 'builtin'
        
        # Check if module is in project directory
        try:
            module_path.relative_to(project_root)
            # Verify it's not actually external via sys.path resolution
            if not _is_external_via_syspath(module_path, project_root):
                return 'project'
        except ValueError:
            pass  # Module is outside project root
    
    # 6. Handle namespace packages and modules without file origin
    if spec.submodule_search_locations:
        locations = [Path(loc).resolve() for loc in spec.submodule_search_locations]
        for loc in locations:
            try:
                loc.relative_to(project_root)
                # Double-check if this location is also in an installed package
                if _is_installed_package_location(module_name):
                    return 'external'
                return 'project'
            except ValueError:
                continue
    
    # Default to external for anything we can't clearly classify
    return 'external'


def get_module_info(module_name: str, project_root: Optional[str] = None) -> ModuleInfo:
    """
    Get detailed classification information about a module.
    
    Args:
        module_name: Python module name
        project_root: Project root directory
        
    Returns:
        ModuleInfo dataclass with complete classification details
    """
    if project_root is None:
        project_root = Path.cwd().resolve()
    else:
        project_root = Path(project_root).resolve()
    
    classification = classify_module(module_name, project_root)
    
    info = ModuleInfo(
        name=module_name,
        type=classification,
        project_root=str(project_root)
    )
    
    try:
        spec = importlib.util.find_spec(module_name)
        if spec and spec.origin:
            info.path = spec.origin
            if classification == 'project':
                try:
                    info.relative_path = str(Path(spec.origin).relative_to(project_root))
                except ValueError:
                    pass
        
        # Add package info for external modules
        if classification == 'external' and _is_installed_package(module_name):
            try:
                root_module = module_name.split('.')[0]
                dist = importlib.metadata.distribution(root_module)
                info.package_name = dist.metadata['Name']
                info.version = dist.version
            except importlib.metadata.PackageNotFoundError:
                pass
                
    except Exception as e:
        info.error = str(e)
    
    return info


def format_annotation_for_display(annotation: FieldAnnotation) -> str:
    """Format FieldAnnotation for readable display."""
    if annotation.container == ContainerType.OPTIONAL and annotation.args:
        inner = format_annotation_for_display(annotation.args[0])
        return f"Optional[{inner}]"
    elif annotation.container == ContainerType.ARRAY and annotation.args:
        inner = format_annotation_for_display(annotation.args[0])
        return f"Array[{inner}]"
    elif annotation.container == ContainerType.UNION and annotation.args:
        inner_types = [format_annotation_for_display(arg) for arg in annotation.args]
        return f"Union[{', '.join(inner_types)}]"
    elif annotation.custom_type:
        return annotation.custom_type
    elif annotation.base_type:
        return annotation.base_type.value
    else:
        return "unknown"


def create_module_location_from_object(obj: Any, is_external: bool = False) -> ModuleLocation:
    """
    Create ModuleLocation from Python object with simple file path extraction.
    
    No classification logic - caller must determine is_external flag.
    
    Args:
        obj: Python class, function, or any object with __module__
        is_external: Whether this object is from external library
        
    Returns:
        ModuleLocation with extracted module path and file path
    """
    module_path = getattr(obj, '__module__', 'unknown')
    file_path = extract_file_path_from_object(obj)
    
    return ModuleLocation(
        module_path=module_path,
        file_path=file_path,
        is_external=is_external
    )


def extract_file_path_from_object(obj: Any) -> Optional[str]:
    """
    Simple file path extraction from Python object.
    
    Args:
        obj: Python object to inspect
        
    Returns:
        Absolute file path or None if not determinable
    """
    try:
        # Use inspect to get the actual file path
        import inspect
        file_path = inspect.getfile(obj)
        return str(Path(file_path).resolve())
    except (TypeError, OSError):
        return None


# FluidKit-specific helper functions    
def is_project_module(module_name: str, project_root: Optional[str] = None) -> bool:
    """Check if module should get full FluidKit introspection."""
    return classify_module(module_name, project_root) == 'project'


def should_introspect_external(module_name: str, project_root: Optional[str] = None) -> bool:
    """Check if external module should get one-layer introspection."""
    return classify_module(module_name, project_root) == 'external'


def should_use_any_type(module_name: str, project_root: Optional[str] = None) -> bool:
    """Check if module should become 'any' type in TypeScript."""
    return classify_module(module_name, project_root) in ('builtin', 'not_found')


def get_external_modules_info(module_names: List[str], project_root: Optional[str] = None) -> List[ModuleInfo]:
    """
    Get info for multiple modules, filtering to only external ones.
    Useful for batch processing external dependencies.
    """
    external_modules = []
    for module_name in module_names:
        info = get_module_info(module_name, project_root)
        if info.type == 'external':
            external_modules.append(info)
    return external_modules


def _is_installed_package(module_name: str) -> bool:
    """Check if module is an installed package via metadata."""
    try:
        # Check the root package name
        root_module = module_name.split('.')[0]
        importlib.metadata.distribution(root_module)
        return True
    except importlib.metadata.PackageNotFoundError:
        return False


def _is_installed_package_location(module_name: str) -> bool:
    """Check if any part of module path belongs to installed package."""
    parts = module_name.split('.')
    for i in range(len(parts)):
        try:
            package_name = '.'.join(parts[:i+1])
            importlib.metadata.distribution(package_name)
            return True
        except importlib.metadata.PackageNotFoundError:
            continue
    return False


def _is_stdlib_module(module_path: Path) -> bool:
    """Check if module is part of Python standard library."""
    # Get Python's installation prefixes
    python_prefix = Path(sys.prefix).resolve()
    python_exec_prefix = Path(sys.exec_prefix).resolve()
    
    # Standard library is typically in {prefix}/lib/python{version}/
    stdlib_paths = [
        python_prefix / 'lib',
        python_exec_prefix / 'lib',
    ]
    
    # On Windows, also check DLLs directory
    if sys.platform == 'win32':
        stdlib_paths.extend([
            python_prefix / 'DLLs',
            python_exec_prefix / 'DLLs',
        ])
    
    for stdlib_path in stdlib_paths:
        try:
            module_path.relative_to(stdlib_path)
            # Make sure it's not in site-packages (pip installed packages)
            if 'site-packages' not in str(module_path):
                return True
        except ValueError:
            continue
    return False


def _is_external_via_syspath(module_path: Path, project_root: Path) -> bool:
    """
    Check if module path resolves via sys.path entries that are external to project.
    This handles cases where modules might be in project root but actually external.
    """
    # Get the directory containing the module
    module_dir = module_path.parent
    
    # Check each sys.path entry
    for path_entry in sys.path:
        if not path_entry:  # Skip empty strings
            continue
            
        path_obj = Path(path_entry).resolve()
        
        # Skip if this path entry is the project root or under it
        try:
            path_obj.relative_to(project_root)
            continue  # This is a project-local path entry
        except ValueError:
            pass  # This is an external path entry
        
        # Check if module is under this external path
        try:
            module_dir.relative_to(path_obj)
            return True  # Module found via external sys.path entry
        except ValueError:
            continue
    
    return False


def print_module_classification(module_names: List[str], project_root: Optional[str] = None):
    """Debug helper to print classification of multiple modules."""
    print("=== Module Classification ===")
    if project_root:
        print(f"Project root: {project_root}")
    else:
        print(f"Project root: {Path.cwd()}")
    print()
    
    for module_name in module_names:
        info = get_module_info(module_name, project_root)
        print(f"{module_name}:")
        print(f"  Type: {info.type}")
        if info.path:
            print(f"  Path: {info.path}")
        if info.relative_path:
            print(f"  Relative: {info.relative_path}")
        if info.package_name:
            print(f"  Package: {info.package_name} v{info.version}")
        if info.error:
            print(f"  Error: {info.error}")
        print()

# Usage example and testing
if __name__ == "__main__":
    # Test with common modules
    test_modules = [
        'sys', 'os', 'json',           # stdlib/builtin
        'pydantic', 'fastapi',         # external packages
        'fluidkit', 'tests'            # local project (if they exist)
    ]
    
    print_module_classification(test_modules)
    
    # Test FluidKit-specific helpers
    print("=== FluidKit Classification Helpers ===")
    for module in test_modules:
        print(f"{module}:")
        print(f"  is_project_module: {is_project_module(module)}")
        print(f"  should_introspect_external: {should_introspect_external(module)}")
        print(f"  should_use_any_type: {should_use_any_type(module)}")
        print()
