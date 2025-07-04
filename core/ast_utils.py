import ast
from .models import *

def interface(cls):
    """Mark class for TypeScript interface generation"""
    cls._fluid_interface = True
    return cls


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
