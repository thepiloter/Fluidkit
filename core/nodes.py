"""
Core data structures for FluidKit's AST representation and type system.

This module defines the unified IR (Intermediate Representation) used throughout
FluidKit's analysis pipeline. The design leverages a robust FieldAnnotation system
for type representation and reuses Field structures for both model fields and
function parameters.
"""

import ast
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set, Union


# === TYPE SYSTEM === #

class ImportType(Enum):
    """Types of Python import statements."""
    MODULE = "module"            # import fastapi
    FROM_IMPORT = "from_import"  # from fastapi import FastAPI
    STAR_IMPORT = "star_import"  # from fastapi import *


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
    DEPENDENCY = "dependency"  # Dependency injection
    REQUEST = "request"        # FastAPI Request object
    BACKGROUND = "background"  # Background tasks
    UNKNOWN = "unknown"        # Unclassified parameters


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


# === CONSTRAINTS === #

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


# === SOURCE TRACKING === #

@dataclass
class SourceLocation:
    """
    Source code location for debugging and error reporting.
    
    Tracks where each node was found in the original Python source files.
    """
    file: str       # Absolute file path
    line: int       # Line number (1-based)
    column: int     # Column offset (0-based)


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


# === IMPORT SYSTEM === #

@dataclass
class ImportNode:
    """
    Raw import discovery from AST parsing.
    
    Represents an import statement before symbol resolution. Contains the
    original AST node and extracted import information.
    """
    import_type: ImportType                         # Type of import statement
    module: str                                     # Module being imported
    alias: Optional[str]                            # Import alias if any
    is_relative: bool                               # Relative vs absolute import
    ast_node: Union[ast.Import, ast.ImportFrom]     # Original AST node
    line_number: int                                # Source line number
    names: List[str] = field(default_factory=list)  # Imported symbol names


# === CORE NODES === #

@dataclass
class ModelNode:
    """
    Pydantic model discovered with @interface decorator.
    
    Represents a Python class marked for TypeScript interface generation.
    Contains all fields and metadata needed for code generation.
    """
    name: str                                      # Class name
    fields: List[Field]                            # Model fields
    location: SourceLocation                       # Source location
    ast_node: ast.ClassDef                         # Original AST node
    docstring: Optional[str] = None                # Class docstring
    inheritance: Optional[List[str]] = None        # Base class names
    
    def __post_init__(self):
        """Initialize default empty inheritance list."""
        if self.inheritance is None:
            self.inheritance = []
    
    def get_referenced_types(self) -> Set[str]:
        """
        Get all custom types referenced in this model.
        
        Includes types from field annotations and base classes.
        
        Returns:
            Set of custom type names that need to be imported/defined.
        """
        types = set()
        for field in self.fields:
            types.update(field.get_referenced_types())
        if self.inheritance:
            types.update(self.inheritance)
        return types


@dataclass  
class RouteNode:
    """
    FastAPI route function discovered with router decorators.
    
    Represents a Python function decorated with FastAPI route decorators
    (e.g., @router.get, @app.post). Contains all information needed to
    generate TypeScript fetch client functions.
    """
    name: str                                       # Function name
    method: str                                     # HTTP method (get, post, etc.)
    path: str                                       # URL path pattern
    parameters: List[Field]                         # Function parameters as Fields
    location: SourceLocation                        # Source location
    ast_node: ast.FunctionDef                       # Original AST node
    return_type: Optional[FieldAnnotation] = None   # Return type annotation
    docstring: Optional[str] = None                 # Function docstring
    
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


# === COMPILATION UNIT === #

@dataclass
class CompilationUnit:
    """
    Complete parsed information for a single Python file.
    
    Contains all discovered models, routes, and imports from one source file.
    This is the output of the discovery stage and input to the resolution stage.
    """
    models: List[ModelNode]                         # Discovered @interface models
    routes: List[RouteNode]                         # Discovered FastAPI routes
    imports: List[ImportNode]                       # All import statements
    source_file: str                                # Absolute source file path
    metadata: Optional[Dict[str, Any]] = None       # Additional file metadata
    
    def __post_init__(self):
        """Initialize default empty metadata dict."""
        if self.metadata is None:
            self.metadata = {}
    
    def get_all_referenced_types(self) -> Set[str]:
        """
        Get all custom types referenced across models and routes in this file.
        
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
        Get types that this file exports (available for import by other files).
        
        Returns:
            Set of model names that can be imported from this file.
        """
        return {model.name for model in self.models}


# === SYMBOL RESOLUTION === #

@dataclass
class ResolvedSymbol:
    """
    A symbol with its resolved module path after import analysis.
    
    Represents the result of resolving an imported symbol to its full module path.
    """
    name: str                                      # Symbol name (e.g., "BaseModel")
    full_path: str                                 # Full module path (e.g., "pydantic.BaseModel")
    source_file: str                               # File where symbol was imported
    alias: Optional[str] = None                    # Import alias if used


@dataclass
class ImportRegistry:
    """
    Complete symbol resolution registry across all project files.
    
    Enhanced with file-scoped symbol resolution to handle name collisions
    while maintaining global FastAPI/Pydantic symbol tracking.
    """
    project_root: str
    symbols: Dict[str, ResolvedSymbol]                          # Global symbols (FastAPI/Pydantic)
    file_symbols: Dict[str, Dict[str, ResolvedSymbol]]          # File-scoped symbols
    modules: Dict[str, str]                                     # module_alias -> full_module_path
    fastapi_symbols: Set[str]                                   # Symbols from FastAPI
    pydantic_symbols: Set[str]                                  # Symbols from Pydantic
    
    def get_symbol_module(self, symbol: str) -> Optional[str]:
        """
        Get the root module that a symbol belongs to (global lookup).
        
        Args:
            symbol: Symbol name to look up
            
        Returns:
            Root module name (e.g., "fastapi", "pydantic") or None if not found
        """
        if symbol in self.symbols:
            return self.symbols[symbol].full_path.split('.')[0]
        return None
    
    def resolve_symbol_in_file(self, symbol_name: str, file_path: str) -> Optional[ResolvedSymbol]:
        """
        Resolve symbol within specific file's import context.
        
        Args:
            symbol_name: Symbol to resolve
            file_path: File where symbol is used
            
        Returns:
            ResolvedSymbol or None if not found
        """
        file_scope = self.file_symbols.get(file_path, {})
        return file_scope.get(symbol_name)
    
    def get_symbol_module_in_file(self, symbol: str, file_path: str) -> Optional[str]:
        """
        Get module for symbol within file context.
        
        Args:
            symbol: Symbol name to check
            file_path: File where symbol is used
            
        Returns:
            Module name or None
        """
        resolved = self.resolve_symbol_in_file(symbol, file_path)
        if resolved:
            return resolved.full_path.split('.')[0]
        return self.get_symbol_module(symbol)  # Fallback to global
    
    def is_fastapi_symbol(self, symbol: str) -> bool:
        """
        Check if a symbol is from the FastAPI module.
        
        Args:
            symbol: Symbol name to check
            
        Returns:
            True if symbol is from FastAPI
        """
        return symbol in self.fastapi_symbols
    
    def is_pydantic_symbol(self, symbol: str) -> bool:
        """
        Check if a symbol is from the Pydantic module.
        
        Args:
            symbol: Symbol name to check
            
        Returns:
            True if symbol is from Pydantic
        """
        return symbol in self.pydantic_symbols
    
    def resolve_symbol(self, symbol: str) -> Optional[str]:
        """
        Get the full module path for a symbol (global lookup).
        
        Args:
            symbol: Symbol name to resolve
            
        Returns:
            Full module path or None if not found
        """
        if symbol in self.symbols:
            return self.symbols[symbol].full_path
        return None
