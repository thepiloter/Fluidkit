import ast
from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Set


# === TYPE SYSTEM === #

class BaseType(Enum):
    ANY = "any"
    NULL = "null"
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    UNKNOWN = "unknown"

class ContainerType(Enum):
    ARRAY = "array"
    UNION = "union"
    TUPLE = "tuple"
    OBJECT = "object"
    LITERAL = "literal"
    OPTIONAL = "optional"

class ParameterType(Enum):
    # Client-side parameters (include in generated fetch)
    PATH = "path"           # Path(...) or inferred from route pattern
    QUERY = "query"         # Query(...) or simple types with no annotation
    BODY = "body"           # Pydantic models or Body(...)
    HEADER = "header"       # Header(...)
    FORM = "form"           # Form(...)
    FILE = "file"           # File(...), UploadFile
    
    # Server-side only (IGNORE in client generation)
    DEPENDENCY = "dependency"   # Depends(...)
    SECURITY = "security"       # Security(...)
    REQUEST = "request"         # Request type
    BACKGROUND = "background"   # BackgroundTasks type

    UNKNOWN = "unknown"


@dataclass
class FieldAnnotation:
    """Recursive type annotation representation"""
    base_type:      Optional[BaseType] = None
    container:      Optional[ContainerType] = None
    args:           List['FieldAnnotation'] = None  # For generic parameters
    literal_values: List[str] = None                # For Literal["admin", "user"]
    custom_type:    Optional[str] = None            # For custom classes/enums
    
    def __post_init__(self):
        if self.args is None:
            self.args = []
        if self.literal_values is None:
            self.literal_values = []

    def is_simple(self) -> bool:
        """Check if this is a simple type (no container)"""
        return self.container is None and self.custom_type is None

    def is_optional(self) -> bool:
        """Check if this type includes None/optional"""
        return self.container == ContainerType.OPTIONAL

    def get_referenced_types(self) -> Set[str]:
        """Get all custom types referenced in this annotation"""
        types = set()
        if self.custom_type:
            types.add(self.custom_type)
        for arg in self.args:
            types.update(arg.get_referenced_types())
        return types

@dataclass 
class FieldInfo:
    """Extracted information from Field() calls or basic assignments"""
    default:     Any = None
    description: Optional[str] = None
    constraints: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.constraints is None:
            self.constraints = {}

@dataclass
class Field:
    name:        str
    annotation:  FieldAnnotation
    default:     Any = None
    constraints: Dict[str, Any] = None
    description: Optional[str] = None
    
    def __post_init__(self):
        if self.constraints is None:
            self.constraints = {}
    
    @property
    def is_optional(self) -> bool:
        """Derive optional status from annotation"""
        return self.annotation.is_optional() or self.default is not None
    
    @property 
    def is_required(self) -> bool:
        """Check if field is required (no default, not optional)"""
        return not self.is_optional

    def get_referenced_types(self) -> Set[str]:
        """Get all custom types referenced in this field"""
        return self.annotation.get_referenced_types()


# === SOURCE TRACKING === #

@dataclass
class SourceLocation:
    file:   str
    line:   int
    column: int


# === IMPORT SYSTEM ===

@dataclass
class ImportInfo:
    module:         str                     # "fastapi", "models"
    symbols:        List[str]               # ["APIRouter", "Query"]
    location:       SourceLocation 
    alias:          Optional[str] = None    # "import fastapi as fa"
    is_from_import: bool = True             # from X import Y vs import X

@dataclass
class SymbolAssignment:
    name:      str             # "router"
    value_ast: str             # "APIRouter()" (keep as string for now)
    location:  SourceLocation


# === FUNCTION SYSTEM === #

@dataclass
class DecoratorInfo:
    name:     str            # "get" 
    object:   str            # "router"
    args:     List[Any]      # ["/users/{id}"]
    kwargs:   Dict[str, Any] # {"status_code": 200}
    location: SourceLocation
    
    def __post_init__(self):
        if self.kwargs is None:
            self.kwargs = {}

@dataclass
class Parameter:
    name: str
    annotation: FieldAnnotation
    default_value: Any = None
    has_default: bool = False
    is_required: bool = True
    parameter_type: ParameterType = ParameterType.UNKNOWN
    ast_node: Optional[ast.arg] = None          
    default_ast_node: Optional[ast.AST] = None  

    def __post_init__(self):
        self.is_required = not (self.has_default or self.annotation.is_optional())
    
    def get_referenced_types(self) -> Set[str]:
        """Get all custom types referenced in this parameter"""
        return self.annotation.get_referenced_types()
    
    def has_default_call(self) -> bool:
        """Check if default is a function call (Query(), Depends(), etc.)"""
        return (self.default_ast_node is not None and 
                isinstance(self.default_ast_node, ast.Call))
    
    def get_default_call_name(self) -> Optional[str]:
        """Get the name of the default function call"""
        if self.has_default_call():
            call: ast.Call = self.default_ast_node
            if isinstance(call.func, ast.Name):
                return call.func.id
        return None
    
    def should_include_in_client(self) -> bool:
        """Whether this parameter should appear in generated client code"""
        return self.parameter_type not in [ParameterType.DEPENDENCY, ParameterType.REQUEST, ParameterType.BACKGROUND]
    
@dataclass
class Function:
    name:        str
    parameters:  List[Parameter]
    location:    SourceLocation
    return_type: Optional[FieldAnnotation] = None
    docstring:   Optional[str] = None
    is_async:    bool = False
    decorators:  List[DecoratorInfo] = None
    
    def __post_init__(self):
        if self.decorators is None:
            self.decorators = []


# === MODEL SYSTEM === #

@dataclass
class Model:
    name:        str
    fields:      List[Field]
    location:    SourceLocation
    docstring:   Optional[str] = None
    inheritance: List[str] = None
    is_pydantic_model: bool = False

    def __post_init__(self):
        if self.inheritance is None:
            self.inheritance = []


# === COMPILATION UNIT === #

@dataclass
class CompilationUnit:
    """Normalized IR - stores only parsed AST information"""
    models:      List[Model]
    functions:   List[Function]
    imports:     List[ImportInfo]
    assignments: List[SymbolAssignment]
    source_file: str
    metadata:    Dict[str, Any]
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
