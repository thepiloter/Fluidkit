from typing import List
from core.nodes import *
from core.ast_utils import *

def generate_interface(model: ModelNode) -> str:
    """
    Generate TypeScript interface for a single model.
    
    Args:
        model: ModelNode with fields and metadata
        
    Returns:
        Complete TypeScript interface with JSDoc as string
    """
    
    # Determine if this should be an enum or interface
    if _is_enum_model(model):
        return _generate_enum(model)
    else:
        return _generate_interface(model)


def _is_enum_model(model: ModelNode) -> bool:
    """
    Determine if model represents an enum.
    
    Adapted from original logic but using ModelNode structure.
    """
    # Pydantic models are always interfaces
    if model.inheritance and "BaseModel" in model.inheritance:
        return False
    
    # For non-Pydantic classes, check if all fields are constants
    return (model.fields and 
            all(field.default is not None and 
                field.annotation.is_simple() 
                for field in model.fields))


def _generate_interface(model: ModelNode) -> str:
    """Generate TypeScript interface with JSDoc header."""
    lines = []
    
    # Generate JSDoc header
    header = _generate_interface_header(model)
    if header:
        lines.append(header)
    
    # Interface declaration
    lines.append(f"export interface {model.name} {{")
    
    # Generate fields
    for field in model.fields:
        field_lines = _generate_interface_field(field)
        if field_lines:
            # Add proper indentation for multi-line field JSDoc
            indented_lines = []
            for line in field_lines:
                indented_lines.append(f"  {line}")
            lines.extend(indented_lines)
    
    lines.append("}")
    
    return "\n".join(lines)


def _generate_interface_header(model: ModelNode) -> str:
    """Generate interface header with field overview."""
    lines = []
    lines.append("/**")
    
    # Add model docstring
    if model.docstring:
        lines.append(f" * {model.docstring}")
        if model.fields:
            lines.append(" *")
    
    # Add field documentation
    if model.fields:
        for field in model.fields:
            field_line = f" * @property {field.name}"
            if field.description:
                field_line += f" - {field.description}"
            lines.append(field_line)
    
    lines.append(" */")
    return "\n".join(lines)


def _generate_interface_field(field: Field) -> List[str]:
    """
    Generate single interface field with helpful JSDoc.
    
    Returns list of lines (for proper indentation).
    """
    lines = []
    
    # Collect JSDoc information
    jsdoc_parts = []
    if field.description:
        jsdoc_parts.append(field.description)
    
    if field.default is not None:
        if isinstance(field.default, str):
            # Check if it's an enum reference
            if "." in str(field.default) and not field.default.startswith('"'):
                jsdoc_parts.append(f"@default {field.default}")
            else:
                jsdoc_parts.append(f'@default "{field.default}"')
        elif isinstance(field.default, bool):
            jsdoc_parts.append(f"@default {str(field.default).lower()}")
        else:
            jsdoc_parts.append(f"@default {field.default}")
        
    # Add validation constraints from FieldConstraints
    if field.constraints:
        constraint_docs = _generate_constraint_docs(field.constraints)
        jsdoc_parts.extend(constraint_docs)
    
    # Only generate JSDoc if we have something useful to say
    if jsdoc_parts:
        if len(jsdoc_parts) == 1:
            lines.append(f"/** {jsdoc_parts[0]} */")
        else:
            lines.append("/**")
            for part in jsdoc_parts:
                lines.append(f" * {part}")
            lines.append(" */")
    
    # Generate field declaration
    field_name = field.name
    if _is_field_optional(field):
        field_name += "?"
    
    typescript_type = _convert_annotation_to_typescript(field.annotation, is_top_level=True)
    field_declaration = f"{field_name}: {typescript_type};"
    lines.append(field_declaration)
    
    return lines


def _generate_constraint_docs(constraints) -> List[str]:
    """Generate JSDoc documentation for field constraints."""
    docs = []
    
    if constraints.min_value is not None:
        docs.append(f"@minimum {constraints.min_value}")
    
    if constraints.max_value is not None:
        docs.append(f"@maximum {constraints.max_value}")
    
    if constraints.min_length is not None:
        docs.append(f"@minLength {constraints.min_length}")
    
    if constraints.max_length is not None:
        docs.append(f"@maxLength {constraints.max_length}")
    
    if constraints.regex_pattern:
        docs.append(f"@pattern {constraints.regex_pattern}")
    
    return docs


def _generate_enum(model: ModelNode) -> str:
    """Generate TypeScript enum."""
    lines = []
    
    # Generate JSDoc header (reuse interface header logic)
    header = _generate_interface_header(model)
    if header:
        lines.append(header)
    
    lines.append(f"export enum {model.name} {{")
    
    # Generate enum fields
    for field in model.fields:
        field_line = _generate_enum_field(field)
        if field_line:
            lines.append(f"  {field_line}")
    
    lines.append("}")
    
    return "\n".join(lines)


def _generate_enum_field(field: Field) -> str:
    """Generate single enum field."""
    if isinstance(field.default, str):
        escaped_value = _escape_typescript_string(field.default)
        return f'{field.name} = "{escaped_value}",'
    else:
        return f"{field.name} = {field.default},"


# === TYPE CONVERSION (Core Logic from Original) ===

def _convert_annotation_to_typescript(annotation: FieldAnnotation, is_top_level: bool = False) -> str:
    """Convert IR annotation to TypeScript type string."""
    if annotation.container:
        return _convert_container_type(annotation, is_top_level)
    elif annotation.custom_type:
        return annotation.custom_type
    elif annotation.base_type:
        return _convert_base_type(annotation.base_type)
    else:
        return "any"


def _convert_base_type(base_type: BaseType) -> str:
    """Convert base types to TypeScript."""
    mapping = {
        BaseType.STRING: "string",
        BaseType.NUMBER: "number", 
        BaseType.BOOLEAN: "boolean",
        BaseType.ANY: "any",
        BaseType.UNKNOWN: "unknown",
        BaseType.NULL: "null"
    }
    return mapping.get(base_type, "any")


def _convert_container_type(annotation: FieldAnnotation, is_top_level: bool = False) -> str:
    """Convert container types to TypeScript."""
    if annotation.container == ContainerType.OPTIONAL:
        return _convert_optional_type(annotation, is_top_level)
    elif annotation.container == ContainerType.ARRAY:
        return _convert_array_type(annotation)
    elif annotation.container == ContainerType.OBJECT:
        return _convert_object_type(annotation)
    elif annotation.container == ContainerType.TUPLE:
        return _convert_tuple_type(annotation)
    elif annotation.container == ContainerType.UNION:
        return _convert_union_type(annotation)
    elif annotation.container == ContainerType.LITERAL:
        return _convert_literal_type(annotation)
    else:
        return "any"


def _convert_array_type(annotation: FieldAnnotation) -> str:
    """Convert List[T] to T[]."""
    if annotation.args:
        inner_type = _convert_annotation_to_typescript(annotation.args[0], is_top_level=False)
        # Smart parentheses for complex union types
        if "|" in inner_type or "&" in inner_type:
            return f"({inner_type})[]"
        else:
            return f"{inner_type}[]"
    return "any[]"


def _convert_object_type(annotation: FieldAnnotation) -> str:
    """Convert Dict[K, V] to Record<K, V>."""
    if len(annotation.args) >= 2:
        key_type = _convert_annotation_to_typescript(annotation.args[0], is_top_level=False)
        value_type = _convert_annotation_to_typescript(annotation.args[1], is_top_level=False)
        return f"Record<{key_type}, {value_type}>"
    elif len(annotation.args) == 1:
        value_type = _convert_annotation_to_typescript(annotation.args[0], is_top_level=False)
        return f"Record<string, {value_type}>"
    else:
        return "Record<string, any>"


def _convert_union_type(annotation: FieldAnnotation) -> str:
    """Convert Union[A, B] to A | B."""
    if annotation.args:
        type_parts = []
        for arg in annotation.args:
            ts_type = _convert_annotation_to_typescript(arg, is_top_level=False)
            type_parts.append(ts_type)
        return " | ".join(type_parts)
    return "any"


def _convert_literal_type(annotation: FieldAnnotation) -> str:
    """Convert Literal["a", "b"] to "a" | "b"."""
    if annotation.literal_values:
        literal_parts = []
        for value in annotation.literal_values:
            if isinstance(value, str):
                escaped = _escape_typescript_string(value)
                literal_parts.append(f'"{escaped}"')
            else:
                literal_parts.append(str(value))
        return " | ".join(literal_parts)
    return "any"


def _convert_tuple_type(annotation: FieldAnnotation) -> str:
    """Convert Tuple[A, B] to [A, B]."""
    if annotation.args:
        type_parts = []
        for arg in annotation.args:
            ts_type = _convert_annotation_to_typescript(arg, is_top_level=False)
            type_parts.append(ts_type)
        return f"[{', '.join(type_parts)}]"
    else:
        return "[any]"


def _convert_optional_type(annotation: FieldAnnotation, is_top_level: bool = False) -> str:
    """
    Convert Optional[T] to T (top-level) or T | null (nested).
    
    This is the sophisticated logic from your original code.
    """
    if annotation.args:
        inner_type = _convert_annotation_to_typescript(annotation.args[0], is_top_level=False)
        if is_top_level:
            # Top-level Optional[T] becomes just T (with ? in field name)
            return inner_type
        else:
            # Nested Optional[T] becomes T | null
            return f"{inner_type} | null"
    return "any"


# === UTILITIES ===

def _escape_typescript_string(value: str) -> str:
    """Escape string literals for TypeScript."""
    return value.replace('"', '\\"').replace("\\", "\\\\")


def _is_field_optional(field: Field) -> bool:
    """
    Determine if field should be optional in TypeScript.
    
    Uses the sophisticated logic from your original code.
    """
    return (
        field.is_optional or  # Has default value
        field.annotation.is_optional()  # Is Optional[T] or Union with None
    )


# === TESTING HELPER ===
def test_generate_interface():
    """Test interface generation with various type scenarios."""
    
    # === TEST 1: Simple Interface ===
    print("=== TEST 1: Simple Interface ===")
    simple_user = ModelNode(
        name="User",
        fields=[
            Field(
                name="id",
                annotation=FieldAnnotation(base_type=BaseType.NUMBER),
                default=None,
                description="User identifier"
            ),
            Field(
                name="name", 
                annotation=FieldAnnotation(base_type=BaseType.STRING),
                default="Anonymous",
                description="User name"
            ),
            Field(
                name="active",
                annotation=FieldAnnotation(base_type=BaseType.BOOLEAN),
                default=True
            )
        ],
        location=SourceLocation("test.py", 1, 0),
        ast_node=None,
        docstring="Simple user model",
        inheritance=["BaseModel"]
    )
    
    result = generate_interface(simple_user)
    print(result)
    print("\n" + "="*50 + "\n")
    
    # === TEST 2: Optional and Union Types ===
    print("=== TEST 2: Optional and Union Types ===")
    complex_user = ModelNode(
        name="ComplexUser",
        fields=[
            Field(
                name="email",
                annotation=FieldAnnotation(
                    container=ContainerType.OPTIONAL,
                    args=[FieldAnnotation(base_type=BaseType.STRING)]
                ),
                default=None,
                description="Optional email address"
            ),
            Field(
                name="tags",
                annotation=FieldAnnotation(
                    container=ContainerType.ARRAY,
                    args=[FieldAnnotation(base_type=BaseType.STRING)]
                ),
                default=[],
                description="User tags"
            ),
            Field(
                name="role",
                annotation=FieldAnnotation(
                    container=ContainerType.UNION,
                    args=[
                        FieldAnnotation(base_type=BaseType.STRING),
                        FieldAnnotation(base_type=BaseType.NULL)
                    ]
                ),
                default=None
            )
        ],
        location=SourceLocation("test.py", 10, 0),
        ast_node=None,
        inheritance=["BaseModel"]
    )
    
    result = generate_interface(complex_user)
    print(result)
    print("\n" + "="*50 + "\n")
    
    # === TEST 3: Validation Constraints ===
    print("=== TEST 3: Validation Constraints ===")
    validated_user = ModelNode(
        name="ValidatedUser",
        fields=[
            Field(
                name="username",
                annotation=FieldAnnotation(base_type=BaseType.STRING),
                constraints=FieldConstraints(
                    min_length=3,
                    max_length=20,
                    regex_pattern="^[a-zA-Z0-9_]+$"
                ),
                description="Username with validation"
            ),
            Field(
                name="age",
                annotation=FieldAnnotation(base_type=BaseType.NUMBER),
                constraints=FieldConstraints(
                    min_value=0,
                    max_value=120
                ),
                description="User age"
            )
        ],
        location=SourceLocation("test.py", 20, 0),
        ast_node=None,
        inheritance=["BaseModel"]
    )
    
    result = generate_interface(validated_user)
    print(result)
    print("\n" + "="*50 + "\n")
    
    # === TEST 4: Custom Types and Complex Structures ===
    print("=== TEST 4: Custom Types and Complex Structures ===")
    product = ModelNode(
        name="Product",
        fields=[
            Field(
                name="id",
                annotation=FieldAnnotation(base_type=BaseType.STRING),
                default=None
            ),
            Field(
                name="owner",
                annotation=FieldAnnotation(custom_type="User"),
                default=None,
                description="Product owner"
            ),
            Field(
                name="metadata",
                annotation=FieldAnnotation(
                    container=ContainerType.OBJECT,
                    args=[
                        FieldAnnotation(base_type=BaseType.STRING),
                        FieldAnnotation(base_type=BaseType.ANY)
                    ]
                ),
                default={},
                description="Product metadata"
            ),
            Field(
                name="status",
                annotation=FieldAnnotation(
                    container=ContainerType.LITERAL,
                    literal_values=["draft", "published", "archived"]
                ),
                default="draft"
            )
        ],
        location=SourceLocation("test.py", 30, 0),
        ast_node=None,
        docstring="Product with custom types and literals",
        inheritance=["BaseModel"]
    )
    
    result = generate_interface(product)
    print(result)
    print("\n" + "="*50 + "\n")
    
    # === TEST 5: Enum Generation ===
    print("=== TEST 5: Enum Generation ===")
    status_enum = ModelNode(
        name="Status",
        fields=[
            Field(
                name="PENDING",
                annotation=FieldAnnotation(base_type=BaseType.STRING),
                default="pending"
            ),
            Field(
                name="COMPLETED",
                annotation=FieldAnnotation(base_type=BaseType.STRING),
                default="completed"
            ),
            Field(
                name="FAILED",
                annotation=FieldAnnotation(base_type=BaseType.STRING),
                default="failed"
            )
        ],
        location=SourceLocation("test.py", 40, 0),
        ast_node=None,
        docstring="Task status enumeration",
        inheritance=[]  # No BaseModel = potential enum
    )
    
    result = generate_interface(status_enum)
    print(result)
    print("\n" + "="*50 + "\n")
    
    # === TEST 6: Tuple and Complex Arrays ===
    print("=== TEST 6: Tuple and Complex Arrays ===")
    coordinate = ModelNode(
        name="Coordinate",
        fields=[
            Field(
                name="position",
                annotation=FieldAnnotation(
                    container=ContainerType.TUPLE,
                    args=[
                        FieldAnnotation(base_type=BaseType.NUMBER),
                        FieldAnnotation(base_type=BaseType.NUMBER)
                    ]
                ),
                default=None,
                description="X, Y coordinates"
            ),
            Field(
                name="connections",
                annotation=FieldAnnotation(
                    container=ContainerType.ARRAY,
                    args=[
                        FieldAnnotation(
                            container=ContainerType.UNION,
                            args=[
                                FieldAnnotation(custom_type="Coordinate"),
                                FieldAnnotation(base_type=BaseType.NULL)
                            ]
                        )
                    ]
                ),
                default=[],
                description="Connected coordinates"
            )
        ],
        location=SourceLocation("test.py", 50, 0),
        ast_node=None,
        inheritance=["BaseModel"]
    )
    
    result = generate_interface(coordinate)
    print(result)

if __name__ == "__main__":
    test_generate_interface()
