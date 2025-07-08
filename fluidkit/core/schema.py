"""
FluidKit V2 Data Models for Runtime Introspection

Simplified data structures optimized for FastAPI runtime introspection while
maintaining compatibility with existing TypeScript generators. Removes AST-specific
complexity and focuses on module-based location tracking for distributed generation.
"""

import inspect
from enum import Enum
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set

# === TYPE SYSTEM === #

class BaseType(Enum):
    """Primitive TypeScript types for code generation."""
    ANY = "any"
    NULL = "null"
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    UNKNOWN = "unknown"


class ContainerType(Enum):
    """Container types for complex TypeScript structures."""
    ARRAY = "array"        # List[T] -> T[]
    UNION = "union"        # Union[A, B] -> A | B
    TUPLE = "tuple"        # Tuple[A, B] -> [A, B]
    OBJECT = "object"      # Dict[str, T] -> Record<string, T>
    LITERAL = "literal"    # Literal["a", "b"] -> "a" | "b"
    OPTIONAL = "optional"  # Optional[T] -> T | null


class ParameterType(Enum):
    """Classification of FastAPI function parameters for client generation."""
    
    # Include in generated fetch client
    PATH = "path"          # Path parameters from URL
    QUERY = "query"        # Query string parameters  
    BODY = "body"          # Request body (JSON)
    FORM = "form"          # Form data
    FILE = "file"          # File uploads
    
    # Document in JSDoc but skip in fetch client (authentication/headers)
    HEADER = "header"      # HTTP headers
    COOKIE = "cookie"      # Cookie values
    SECURITY = "security"  # OAuth, API keys, etc.
    
    # Ignore completely (server-side only)
    # DEPENDENCY = "dependency"  # Dependency injection
    # REQUEST = "request"        # FastAPI Request object
    # BACKGROUND = "background"  # Background tasks
    # UNKNOWN = "unknown"        # Unclassified parameters


class LanguageType(Enum):
    """Supported code generation languages."""
    TYPESCRIPT = "typescript"
    TS = "ts"  # Alias for TypeScript
    
    # Future language support:
    # PYTHON = "python" 
    # PY = "py"
    # JAVASCRIPT = "javascript"
    # JS = "js"
    # ZOD = "zod"
    # GO = "go"


# === ANNOTATIONS === #

@dataclass
class FieldAnnotation:
    """
    Recursive type annotation representation supporting complex Python type hints.
    
    This is the core type system used throughout FluidKit for representing
    Python type annotations and generating their TypeScript equivalents.
    
    Examples:
        str -> FieldAnnotation(base_type=BaseType.STRING)
        List[User] -> FieldAnnotation(container=ContainerType.ARRAY, args=[FieldAnnotation(custom_type="User")])
        Optional[int] -> FieldAnnotation(container=ContainerType.OPTIONAL, args=[FieldAnnotation(base_type=BaseType.NUMBER)])
    """
    base_type: Optional[BaseType] = None               # Primitive type (str, int, bool, etc.)
    container: Optional[ContainerType] = None          # Container type (List, Union, Optional, etc.)
    args: List['FieldAnnotation'] = None               # Generic type arguments
    literal_values: List[str] = None                   # Values for Literal types
    custom_type: Optional[str] = None                  # Custom class/enum names
    class_reference: Optional[Any] = None              # Reference to custom class/enum
    
    def __post_init__(self):
        """Initialize default empty lists for mutable fields."""
        if self.args is None:
            self.args = []
        if self.literal_values is None:
            self.literal_values = []

    def is_simple(self) -> bool:
        """
        Check if this is a simple primitive type with no containers or custom types.
        
        Returns:
            True for types like str, int, bool. False for List[str], User, etc.
        """
        return self.container is None and self.custom_type is None

    def is_optional(self) -> bool:
        """
        Check if this type includes None/optional semantics.
        
        Returns:
            True for Optional[T] or Union[T, None] types.
        """
        return self.container == ContainerType.OPTIONAL

    def get_referenced_types(self) -> Set[str]:
        """
        Get all custom type names referenced in this annotation tree.
        
        Returns:
            Set of custom type names that need to be imported/defined.
        """
        types = set()
        if self.custom_type:
            types.add(self.custom_type)
        for arg in self.args:
            types.update(arg.get_referenced_types())
        return types


# === CONSTRAINTS  === #

@dataclass
class FieldConstraints:
    """
    Expandable constraints for fields and parameters.
    
    This structure holds FastAPI-specific metadata, validation rules,
    and custom constraints that can be extended as needed.
    """
    
    # FastAPI-specific constraints
    parameter_type: Optional[ParameterType] = None      # Where parameter goes in HTTP request
    fastapi_annotation: Optional[str] = None            # Original FastAPI annotation name
    
    # Validation constraints (from Pydantic Field() calls)
    min_value: Optional[float] = None                   # ge, gt constraints
    max_value: Optional[float] = None                   # le, lt constraints
    min_length: Optional[int] = None                    # String/array minimum length
    max_length: Optional[int] = None                    # String/array maximum length
    regex_pattern: Optional[str] = None                 # String regex validation
    
    # HTTP-specific constraints
    media_type: Optional[str] = None                    # MIME type for files
    include_in_schema: Optional[bool] = None            # OpenAPI schema inclusion
    deprecated: Optional[bool] = None                   # Mark as deprecated
    
    # Custom metadata (extensible for future features)
    custom: Optional[Dict[str, Any]] = None             # Arbitrary key-value metadata
    
    def __post_init__(self):
        """Initialize default empty dict for custom constraints."""
        if self.custom is None:
            self.custom = {}


# === LOCATION SYSTEM === #

@dataclass
class ModuleLocation:
    """
    Module location for distributed generation and import path calculation.
    
    Simplified for project-only introspection approach.
    """
    module_path: str                    # "routes.users.page" or "models.user"
    file_path: Optional[str] = None     # "/project/routes/users/page.py" (derived)
    is_external: bool = False           # Whether this is an external library module
    
    def get_typescript_file_path(self) -> Optional[str]:
        """Get corresponding TypeScript file path for generation."""
        if self.file_path:
            return self.file_path.replace('.py', '.ts')
        return None

    def calculate_relative_import_path(self, target_location: 'ModuleLocation') -> Optional[str]:
        """Calculate relative import path from this location to target location."""
        if not self.file_path or not target_location.file_path:
            return f"./{target_location.module_path.replace('.', '/')}"
        
        try:
            source_path = Path(self.file_path)
            target_path = Path(target_location.file_path)
            
            source_ts_dir = source_path.with_suffix('.ts').parent
            target_ts_file = target_path.with_suffix('.ts')
            
            import os
            relative_path = os.path.relpath(target_ts_file, source_ts_dir)
            relative_path = Path(relative_path).with_suffix('')
            import_path = str(relative_path).replace('\\', '/')
            
            if not import_path.startswith('../'):
                import_path = './' + import_path
            
            return import_path
            
        except (ValueError, OSError):
            return f"./{target_location.module_path.replace('.', '/')}"

    def is_same_file(self, other: 'ModuleLocation') -> bool:
        """Check if two locations represent the same file."""
        if self.file_path and other.file_path:
            try:
                return Path(self.file_path).resolve() == Path(other.file_path).resolve()
            except (ValueError, OSError):
                pass
        return self.module_path == other.module_path


# === FIELD SYSTEM === #

@dataclass
class Field:
    """
    Universal field representation for both model fields and function parameters.
    
    This unified structure allows the same type system and constraint handling
    for Pydantic model fields and FastAPI function parameters.
    """
    name: str                                        # Field/parameter name
    annotation: FieldAnnotation                      # Type annotation
    default: Any = None                              # Default value
    constraints: Optional[FieldConstraints] = None   # Validation and metadata
    description: Optional[str] = None                # Documentation string
    
    def __post_init__(self):
        """Initialize default empty constraints if none provided."""
        if self.constraints is None:
            self.constraints = FieldConstraints()
    
    @property
    def is_optional(self) -> bool:
        """
        Determine if this field is optional.
        
        A field is optional if it has an Optional type annotation or a default value.
        
        Returns:
            True if the field is optional, False if required.
        """
        return self.annotation.is_optional() or self.default is not None
    
    @property 
    def is_required(self) -> bool:
        """
        Determine if this field is required.
        
        Returns:
            True if the field is required, False if optional.
        """
        return not self.is_optional

    def get_referenced_types(self) -> Set[str]:
        """
        Get all custom types referenced in this field's annotation.
        
        Returns:
            Set of custom type names that need to be imported/defined.
        """
        return self.annotation.get_referenced_types()
    
    def should_include_in_fetch(self) -> bool:
        """
        Determine if this parameter should be included in the actual fetch request.
        
        Headers, cookies, and security are documented but handled separately from fetch logic.
        """
        if not self.constraints or not self.constraints.parameter_type:
            return True  # Model fields are always included
        
        fetch_types = {
            ParameterType.PATH, 
            ParameterType.QUERY, 
            ParameterType.BODY, 
            ParameterType.FORM, 
            ParameterType.FILE
        }
        
        return self.constraints.parameter_type in fetch_types

    def should_document_in_jsdoc(self) -> bool:
        """
        Determine if this parameter should appear in JSDoc documentation.
        
        Includes fetch parameters plus headers/auth for developer awareness.
        """
        if not self.constraints or not self.constraints.parameter_type:
            return True  # Model fields are always documented
        
        document_types = {
            ParameterType.PATH, 
            ParameterType.QUERY, 
            ParameterType.BODY, 
            ParameterType.FORM, 
            ParameterType.FILE,
            ParameterType.HEADER,
            ParameterType.COOKIE, 
            ParameterType.SECURITY
        }
        
        return self.constraints.parameter_type in document_types


# === SECURITY RELATED FIELD SYSTEM === #

@dataclass
class SecurityRequirement:
    """Security requirement for TypeScript client JSDoc generation."""
    scheme_name: str                           # "oauth2", "api_key", "bearer_token"  
    scheme_type: str                           # "oauth2", "apiKey", "http"
    description: Optional[str] = None          # Human description
    scopes: List[str] = field(default_factory=list)  # OAuth2 scopes
    location: Optional[str] = None             # "header", "query", "cookie" (for apiKey)
    parameter_name: Optional[str] = None       # "X-API-Key", "Authorization" (for apiKey)

# === CORE NODES === #

@dataclass
class ModelNode:
    """
    Pydantic model discovered through runtime introspection.
    
    Represents a Python class that should be converted to TypeScript interface.
    Populated from Pydantic model introspection rather than AST parsing.
    """
    name: str                                      # Class name
    fields: List[Field]                            # Model fields
    location: ModuleLocation                       # Module location for generation
    docstring: Optional[str] = None                # Class docstring
    inheritance: List[str] = field(default_factory=list)  # Base class names
    is_enum: bool = False                          # Whether this is an enum
    metadata: Dict[str, Any] = field(default_factory=dict)      # Additional metadata
    
    def get_referenced_types(self) -> Set[str]:
        """
        Get all custom types referenced in this model.
        
        Includes types from field annotations and base classes.
        
        Returns:
            Set of custom type names that need to be imported/defined.
        """
        types = set()
        for field_item in self.fields:
            types.update(field_item.get_referenced_types())
        if self.inheritance:
            types.update(self.inheritance)
        return types
    
    def is_interface_model(self) -> bool:
        """
        Check if this should be generated as TypeScript interface.
        
        Returns:
            True for Pydantic models, False for enums
        """
        return not self.is_enum and 'BaseModel' in self.inheritance

    def is_type_alias(self) -> bool:
        """Check if this represents a TypeScript type alias."""
        return self.metadata.get('is_type_alias', False)
    
    def get_typescript_type(self) -> Optional[str]:
        """Get the TypeScript type for type aliases."""
        return self.metadata.get('typescript_type')


@dataclass  
class RouteNode:
    """
    FastAPI route discovered through runtime introspection.
    
    Represents a FastAPI route function that should be converted to TypeScript
    fetch client function. Populated from FastAPI route introspection.
    """
    name: str                                       # Function name
    methods: List[str]                              # HTTP methods ["GET", "POST"] or ["GET"]
    path: str                                       # URL path pattern
    parameters: List[Field]                         # Function parameters as Fields
    location: ModuleLocation                        # Module location for generation
    return_type: Optional[FieldAnnotation] = None   # Return type annotation
    docstring: Optional[str] = None                 # Function docstring
    security_requirements: List[SecurityRequirement] = field(default_factory=list)
    
    @property
    def is_single_method(self) -> bool:
        return len(self.methods) == 1

    def get_referenced_types(self) -> Set[str]:
        """
        Get all custom types referenced in this route.
        
        Includes types from parameter annotations and return type.
        
        Returns:
            Set of custom type names that need to be imported/defined.
        """
        types = set()
        for param in self.parameters:
            types.update(param.get_referenced_types())
        if self.return_type:
            types.update(self.return_type.get_referenced_types())
        return types
    
    def get_client_parameters(self) -> List[Field]:
        """
        Get only parameters that should be included in client generation.
        
        Filters out dependencies, request objects, and background tasks.
        
        Returns:
            List of parameters to include in generated fetch functions.
        """
        return [param for param in self.parameters if param.should_include_in_fetch()]
    
    def get_auth_parameters(self) -> List[Field]:
        """
        Get parameters for authentication documentation (headers, security).
        
        Returns:
            List of auth-related parameters for JSDoc documentation
        """
        auth_types = {ParameterType.HEADER, ParameterType.COOKIE, ParameterType.SECURITY}
        return [param for param in self.parameters 
                if param.constraints and param.constraints.parameter_type in auth_types]


# === APP-WIDE COLLECTION === #

@dataclass
class FluidKitApp:
    """
    Complete app introspection results from FastAPI runtime analysis.
    
    Replaces file-based CompilationUnit with app-wide model and route collection.
    Contains all discovered models and routes across the entire FastAPI application.
    """
    models: List[ModelNode] = field(default_factory=list)      # All discovered models
    routes: List[RouteNode] = field(default_factory=list)      # All discovered routes
    app_instance: Optional[Any] = None                         # Reference to FastAPI app
    metadata: Dict[str, Any] = field(default_factory=dict)     # Additional app metadata
    
    def get_all_referenced_types(self) -> Set[str]:
        """
        Get all custom types referenced across models and routes.
        
        Returns:
            Set of custom type names that need to be resolved/imported.
        """
        types = set()
        for model in self.models:
            types.update(model.get_referenced_types())
        for route in self.routes:
            types.update(route.get_referenced_types())
        return types
    
    def get_exported_types(self) -> Set[str]:
        """
        Get all types that this app exports (available for import).
        
        Returns:
            Set of model names that can be imported by external clients.
        """
        return {model.name for model in self.models}
    
    def get_models_by_location(self) -> Dict[str, List[ModelNode]]:
        """
        Group models by their file location for distributed generation.
        
        Returns:
            Dict mapping file_path -> list of models in that file
        """
        models_by_location = {}
        for model in self.models:
            file_path = model.location.file_path
            if file_path:
                if file_path not in models_by_location:
                    models_by_location[file_path] = []
                models_by_location[file_path].append(model)
        return models_by_location
    
    def get_routes_by_location(self) -> Dict[str, List[RouteNode]]:
        """
        Group routes by their file location for distributed generation.
        
        Returns:
            Dict mapping file_path -> list of routes in that file
        """
        routes_by_location = {}
        for route in self.routes:
            file_path = route.location.file_path
            if file_path:
                if file_path not in routes_by_location:
                    routes_by_location[file_path] = []
                routes_by_location[file_path].append(route)
        return routes_by_location
    
    def get_generation_files(self) -> Dict[str, Dict[str, List]]:
        """
        Get complete file-to-content mapping for distributed generation.
        
        Returns:
            Dict mapping typescript_file_path -> {'models': [...], 'routes': [...]}
        """
        generation_files = {}
        
        # Add models
        for model in self.models:
            ts_file_path = model.location.get_typescript_file_path()
            if ts_file_path:
                if ts_file_path not in generation_files:
                    generation_files[ts_file_path] = {'models': [], 'routes': []}
                generation_files[ts_file_path]['models'].append(model)
        
        # Add routes
        for route in self.routes:
            ts_file_path = route.location.get_typescript_file_path()
            if ts_file_path:
                if ts_file_path not in generation_files:
                    generation_files[ts_file_path] = {'models': [], 'routes': []}
                generation_files[ts_file_path]['routes'].append(route)
        
        return generation_files
    
    def find_model_by_name(self, model_name: str) -> Optional[ModelNode]:
        """
        Find a model by name for import resolution.
        
        Args:
            model_name: Name of the model to find
            
        Returns:
            ModelNode if found, None otherwise
        """
        for model in self.models:
            if model.name == model_name:
                return model
        return None
    
    def calculate_imports_for_location(
        self, 
        location: ModuleLocation, 
        referenced_types: Set[str]
    ) -> Dict[str, List[str]]:
        """
        Calculate import statements needed for a specific location.
        
        Args:
            location: Location where imports are needed
            referenced_types: Set of type names that need to be imported
            
        Returns:
            Dict mapping import_path -> list of symbols to import
        """
        imports_by_path = {}
        
        for type_name in referenced_types:
            model = self.find_model_by_name(type_name)
            if model:
                import_path = location.calculate_relative_import_path(model.location)
                if import_path:
                    if import_path not in imports_by_path:
                        imports_by_path[import_path] = []
                    imports_by_path[import_path].append(type_name)
        
        return imports_by_path


# === COMPATIBILITY HELPERS === #
def _calculate_cross_platform_relative_path(target_path: Path, source_dir: Path) -> Optional[Path]:
    """
    Calculate relative path between two paths with cross-drive/mount handling.
    
    Args:
        target_path: Target file path
        source_dir: Source directory path
        
    Returns:
        Relative Path object or None if cross-drive/mount issue
    """
    try:
        # Try Path.relative_to first (most reliable when it works)
        return target_path.relative_to(source_dir)
    except ValueError:
        # Path.relative_to failed - try os.path.relpath
        try:
            import os
            rel_path_str = os.path.relpath(str(target_path), str(source_dir))
            return Path(rel_path_str)
        except (ValueError, OSError):
            # Both methods failed - likely cross-drive on Windows
            return None


def create_fluidkit_app_from_compilation_units(compilation_units: Dict[str, Any]) -> FluidKitApp:
    """
    Migration helper: Convert V1 CompilationUnits to V2 FluidKitApp.
    
    Enables gradual migration from AST-based to introspection-based approach.
    
    Args:
        compilation_units: V1 CompilationUnit structures
        
    Returns:
        FluidKitApp with all models and routes combined
    """
    app = FluidKitApp()
    
    for compilation_unit in compilation_units.values():
        app.models.extend(compilation_unit.models)
        app.routes.extend(compilation_unit.routes)
    
    return app
