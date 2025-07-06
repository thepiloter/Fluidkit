import ast
from core.nodes import *

def interface(cls):
    """Mark class for TypeScript interface generation"""
    cls._fluid_interface = True
    return cls

@dataclass
class FieldInfo:
    """Extracted information from Field() calls or basic assignments"""
    default: Any = None
    description: Optional[str] = None
    constraints: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.constraints is None:
            self.constraints = {}

@dataclass
class FastAPIInfo:
    """Extracted information from FastAPI annotation calls (Query, Path, Body, etc.)"""
    default: Any = None
    description: Optional[str] = None
    alias: Optional[str] = None                # Query(alias="search_term")
    embed: Optional[bool] = None               # Body(embed=True)
    constraints: Dict[str, Any] = None         # Validation constraints
    annotation_type: Optional[str] = None      # "Query", "Path", "Body", etc.
    
    def __post_init__(self):
        if self.constraints is None:
            self.constraints = {}

# === TYPE ANNOTATIONS EXTRACTION === #
def extract_type_annotation(node: ast.AST) -> FieldAnnotation:
    """Generic type annotation extraction - works for any Python type hint"""
    if isinstance(node, ast.Name):
        annotation = convert_name_annotation(node)
    elif isinstance(node, ast.Constant):
        annotation = convert_constant_annotation(node)
    elif isinstance(node, ast.Attribute):
        annotation = convert_attribute_annotation(node)
    elif isinstance(node, ast.Subscript):
        annotation = convert_subscript_annotation(node)
    elif isinstance(node, ast.BinOp):
        annotation = convert_binop_annotation(node)
    else:
        annotation = FieldAnnotation()
    return annotation

def convert_name_annotation(node: ast.Name) -> FieldAnnotation:
    """Convert ast.Name to FieldAnnotation"""
    annotation = FieldAnnotation()
    if node.id == "str":
        annotation.base_type = BaseType.STRING
    elif node.id == "int" or node.id == "float":
        annotation.base_type = BaseType.NUMBER
    elif node.id == "bool":
        annotation.base_type = BaseType.BOOLEAN
    elif node.id == "any" or node.id == "Any":
        annotation.base_type = BaseType.ANY
    elif node.id == "None":
        annotation.base_type = BaseType.NULL
    else:
        annotation.custom_type = node.id
    return annotation

def convert_constant_annotation(node: ast.Constant) -> FieldAnnotation:
    """Convert ast.Constant to FieldAnnotation"""
    annotation = FieldAnnotation()
    if node.value is None:
        annotation.base_type = BaseType.NULL
    else:
        annotation.base_type = BaseType.ANY
    return annotation

def convert_attribute_annotation(node: ast.Attribute) -> FieldAnnotation:
    """Convert ast.Attribute to FieldAnnotation"""
    
    def _build_attribute_path(node: ast.Attribute) -> str:
        """Recursively build full attribute path"""
        if isinstance(node.value, ast.Name):
            return f"{node.value.id}.{node.attr}"
        elif isinstance(node.value, ast.Attribute):
            base_path = _build_attribute_path(node.value)
            return f"{base_path}.{node.attr}"
        else:
            return node.attr
    
    annotation = FieldAnnotation()
    annotation.custom_type = _build_attribute_path(node)
    annotation.base_type = BaseType.ANY

    return annotation

def convert_subscript_annotation(node: ast.Subscript) -> FieldAnnotation:
    """Convert ast.Subscript to FieldAnnotation"""
    annotation = FieldAnnotation()
    if isinstance(node.value, ast.Name):
        if node.value.id == "Optional":
            annotation.container = ContainerType.OPTIONAL
        elif node.value.id == "List" or node.value.id == "list":
            annotation.container = ContainerType.ARRAY
        elif node.value.id == "Dict" or node.value.id == "dict":
            annotation.container = ContainerType.OBJECT
        elif node.value.id == "Union":
            annotation.container = ContainerType.UNION
        elif node.value.id == "Tuple":
            annotation.container = ContainerType.TUPLE
        elif node.value.id == "Literal":
            annotation.container = ContainerType.LITERAL
        
    if isinstance(node.slice, ast.Constant):
        if annotation.container == ContainerType.LITERAL:
            annotation.literal_values.append(node.slice.value)
        else:
            annotation.args.append(convert_constant_annotation(node.slice))
    
    elif isinstance(node.slice, ast.Name):
        annotation.args.append(convert_name_annotation(node.slice))
    
    elif isinstance(node.slice, ast.Subscript):
        annotation.args.append(convert_subscript_annotation(node.slice))
    
    elif isinstance(node.slice, ast.Tuple):
        for item in node.slice.elts:
            if annotation.container == ContainerType.LITERAL:
                if isinstance(item, ast.Constant):
                    annotation.literal_values.append(item.value)
            else:
                annotation.args.append(extract_type_annotation(item))

    elif isinstance(node.slice, ast.Attribute):
        annotation.args.append(convert_attribute_annotation(node.slice))

    return annotation

def convert_binop_annotation(node: ast.BinOp) -> FieldAnnotation:
    """Convert ast.BinOp (Union with |) to FieldAnnotation"""
    annotation = FieldAnnotation()
    if isinstance(node.op, ast.BitOr):
        annotation.container = ContainerType.UNION
        annotation.args.append(extract_type_annotation(node.left))
        annotation.args.append(extract_type_annotation(node.right))
    elif isinstance(node.op, ast.Add):
        annotation.container = ContainerType.TUPLE
        annotation.args.append(extract_type_annotation(node.left))
        annotation.args.append(extract_type_annotation(node.right))
    return annotation

def infer_annotation_from_value(value: Any) -> FieldAnnotation:
    """Infer type annotation from constant value"""
    if isinstance(value, str):
        return FieldAnnotation(base_type=BaseType.STRING)
    elif isinstance(value, (int, float)):
        return FieldAnnotation(base_type=BaseType.NUMBER)
    elif isinstance(value, bool):
        return FieldAnnotation(base_type=BaseType.BOOLEAN)
    else:
        return FieldAnnotation(base_type=BaseType.ANY)

def extract_docstring(node: ast.ClassDef | ast.FunctionDef) -> Optional[str]:
    """Extract docstring from class or function"""
    if (node.body and 
        isinstance(node.body[0], ast.Expr) and 
        isinstance(node.body[0].value, ast.Constant) and 
        isinstance(node.body[0].value.value, str)):
        return node.body[0].value.value
    return None


# === BASIC DEFAULT VALUE EXTRACTION === #
def extract_basic_default_value(node: ast.AST) -> Any:
    """Extract defaults from simple nodes (no call handling)"""
    if node is None:
        return None  # No assignment = required field
    elif isinstance(node, ast.Constant):
        return convert_constant_value(node)
    elif isinstance(node, ast.Name):
        return convert_name_value(node)
    elif isinstance(node, ast.Attribute):
        return convert_attribute_value(node)
    elif isinstance(node, ast.List):
        return []
    elif isinstance(node, ast.Dict):
        return {}
    else:
        return None
    
def convert_name_value(node: ast.Name) -> str:
    """Extract simple names: Config, os, datetime"""
    return node.id

def convert_constant_value(node: ast.Constant) -> Any:
    """Extract value from constants: None, 25, "default", True"""
    return node.value

def convert_attribute_value(node: ast.Attribute) -> str:
    """Extract attribute access recursively: Config.Database.DEFAULT_PORT"""
    if isinstance(node.value, ast.Name):
        base = convert_name_value(node.value)
    elif isinstance(node.value, ast.Attribute):
        base = convert_attribute_value(node.value)  # Recursive!
    else:
        return None  # Can't handle complex expressions
    
    return f"{base}.{node.attr}"


# === FIELD INFO EXTRACTION === #
def extract_field_info(node: ast.AST) -> FieldInfo:
    """
    Extract default value and metadata from Field() calls or basic values.
    
    Handles:
    - Field(...) → FieldInfo(default=None) - required field
    - Field(25) → FieldInfo(default=25) - positional default  
    - Field(default=25, description="...") → full extraction
    - Basic values → FieldInfo(default=value)
    """
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "Field":
        default_value = None
        description = None
        constraints = {}
        
        # Handle positional args: Field(...) or Field(25)
        if node.args:
            arg = node.args[0]
            if isinstance(arg, ast.Constant):
                if arg.value is ...:  # Field(...) - required field
                    default_value = None
                else:  # Field(25) - positional default
                    default_value = arg.value
        
        # Handle keyword args
        for keyword in node.keywords:
            if keyword.arg == "default":
                default_value = _extract_default_value_recursive(keyword.value)
            elif keyword.arg == "description" and isinstance(keyword.value, ast.Constant):
                description = keyword.value.value
            elif keyword.arg in ["ge", "le", "gt", "lt", "min_length", "max_length", "regex"]:
                if isinstance(keyword.value, ast.Constant):
                    constraints[keyword.arg] = keyword.value.value
        
        return FieldInfo(
            default=default_value,
            description=description,
            constraints=constraints
        )
    else:
        # Not a Field() call, use basic extraction
        basic_default = extract_basic_default_value(node)
        return FieldInfo(default=basic_default)

def _extract_default_value_recursive(node: ast.AST) -> Any:
    """Extract default value recursively handling nested Field() calls"""
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "Field":
        # Recursive Field() handling
        if node.args and isinstance(node.args[0], ast.Constant):
            if node.args[0].value is ...:
                return None
            else:
                return node.args[0].value
        
        for keyword in node.keywords:
            if keyword.arg == "default":
                return _extract_default_value_recursive(keyword.value)
        return None
    else:
        return extract_basic_default_value(node)


# === FASTAPI PARAMETER INFO EXTRACTION === #
def extract_fastapi_info(node: ast.AST) -> FastAPIInfo:
    """Extract information from FastAPI annotation calls"""
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        func_name = node.func.id
        
        # FastAPI annotation functions we care about
        fastapi_annotations = {
            "Query", "Path", "Body", "Header", "Form", "File", 
            "Depends", "Cookie", "Security"
        }
        
        if func_name not in fastapi_annotations:
            return FastAPIInfo(default=extract_basic_default_value(node))
        
        default_value = None
        description = None
        alias = None
        embed = None
        constraints = {}
        
        # Handle positional args: Query(...) or Query(10)
        if node.args:
            arg = node.args[0]
            if isinstance(arg, ast.Constant):
                if arg.value is ...:  # Query(...) - required
                    default_value = None
                else:  # Query(10) - positional default
                    default_value = arg.value
        
        # Handle keyword args
        for keyword in node.keywords:
            if keyword.arg == "default":
                default_value = _extract_default_value_recursive(keyword.value)
            elif keyword.arg == "description" and isinstance(keyword.value, ast.Constant):
                description = keyword.value.value
            elif keyword.arg == "alias" and isinstance(keyword.value, ast.Constant):
                alias = keyword.value.value
            elif keyword.arg == "embed" and isinstance(keyword.value, ast.Constant):
                embed = keyword.value.value
            elif keyword.arg in ["ge", "le", "gt", "lt", "min_length", "max_length", "regex", "deprecated"]:
                if isinstance(keyword.value, ast.Constant):
                    constraints[keyword.arg] = keyword.value.value
        
        return FastAPIInfo(
            default=default_value,
            description=description,
            alias=alias,
            embed=embed,
            constraints=constraints,
            annotation_type=func_name
        )
    else:
        # Not a FastAPI annotation call
        basic_default = extract_basic_default_value(node)
        return FastAPIInfo(default=basic_default)
