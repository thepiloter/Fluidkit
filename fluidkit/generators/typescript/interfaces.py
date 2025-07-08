"""
FluidKit V2 Interface Generator

Generates TypeScript interfaces from V2 ModelNode objects with enhanced enum detection,
type alias support, and security-aware documentation.
"""

from typing import List
from fluidkit.core.schema import ModelNode, Field, FieldConstraints, ContainerType, BaseType


def generate_interface(model: ModelNode) -> str:
    """Generate TypeScript interface for a ModelNode."""
    if model.is_enum:
        return _generate_enum(model)
    else:
        return _generate_interface(model)


def _generate_interface(model: ModelNode) -> str:
    """Generate TypeScript interface."""
    lines = []
    
    header = _generate_interface_header(model)
    if header:
        lines.append(header)
    
    lines.append(f"export interface {model.name} {{")
    
    for field in model.fields:
        field_lines = _generate_interface_field(field)
        if field_lines:
            indented_lines = []
            for line in field_lines:
                indented_lines.append(f"  {line}")
            lines.extend(indented_lines)
    
    lines.append("}")
    return "\n".join(lines)


def _generate_interface_header(model: ModelNode) -> str:
    """Generate interface header with field overview."""
    parts_to_include = []
    
    if model.docstring:
        parts_to_include.append(model.docstring)
    
    fields_with_descriptions = [f for f in model.fields if f.description]
    if fields_with_descriptions:
        if model.docstring:
            parts_to_include.append("")
        
        for field in fields_with_descriptions:
            parts_to_include.append(f"@property {field.name} - {field.description}")
    
    if not parts_to_include:
        return ""
    
    lines = ["/**"]
    for part in parts_to_include:
        if part == "":
            lines.append(" *")
        else:
            lines.append(f" * {part}")
    lines.append(" */")
    
    return "\n".join(lines)


def _generate_interface_field(field: Field) -> List[str]:
    """Generate single interface field with JSDoc."""
    lines = []
    jsdoc_parts = []
    
    if field.description:
        jsdoc_parts.append(field.description)
    
    # Add external type context
    if field.annotation.class_reference:
        cls = field.annotation.class_reference
        module_name = cls.__module__
        
        from fluidkit.core.utils import classify_module
        if classify_module(module_name) != 'project':
            jsdoc_parts.append(f"@external {module_name}.{cls.__name__}")
    
    if field.default is not None:
        if isinstance(field.default, str):
            jsdoc_parts.append(f'@default "{field.default}"')
        elif isinstance(field.default, bool):
            jsdoc_parts.append(f"@default {str(field.default).lower()}")
        else:
            jsdoc_parts.append(f"@default {field.default}")
    
    if field.constraints:
        constraint_docs = _generate_constraint_docs(field.constraints)
        jsdoc_parts.extend(constraint_docs)
    
    if jsdoc_parts:
        if len(jsdoc_parts) == 1:
            lines.append(f"/** {jsdoc_parts[0]} */")
        else:
            lines.append("/**")
            for part in jsdoc_parts:
                lines.append(f" * {part}")
            lines.append(" */")
    
    field_name = field.name
    if _is_field_optional(field):
        field_name += "?"
    
    typescript_type = _convert_annotation_to_typescript(field.annotation, is_top_level=True)
    field_declaration = f"{field_name}: {typescript_type};"
    lines.append(field_declaration)
    
    return lines


def _generate_constraint_docs(constraints: FieldConstraints) -> List[str]:
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
    
    if constraints.deprecated:
        docs.append("@deprecated")
    
    return docs


def _generate_enum(model: ModelNode) -> str:
    """Generate TypeScript enum."""
    lines = []
    
    header = _generate_interface_header(model)
    if header:
        lines.append(header)
    
    lines.append(f"export enum {model.name} {{")
    
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


def _convert_annotation_to_typescript(annotation, is_top_level: bool = False) -> str:
    """Convert FieldAnnotation to TypeScript type string."""
    if annotation.container:
        return _convert_container_type(annotation, is_top_level)
    elif annotation.custom_type:
        # External types become 'any', project types keep their name
        if annotation.class_reference:
            from fluidkit.core.utils import classify_module
            module_name = annotation.class_reference.__module__
            if classify_module(module_name) != 'project':
                return "any"
        return annotation.custom_type
    elif annotation.base_type:
        return _convert_base_type(annotation.base_type)
    else:
        return "any"


def _convert_base_type(base_type) -> str:
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


def _convert_container_type(annotation, is_top_level: bool = False) -> str:
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


def _convert_array_type(annotation) -> str:
    """Convert List[T] to T[]."""
    if annotation.args:
        inner_type = _convert_annotation_to_typescript(annotation.args[0], is_top_level=False)
        if "|" in inner_type or "&" in inner_type:
            return f"({inner_type})[]"
        else:
            return f"{inner_type}[]"
    return "any[]"


def _convert_object_type(annotation) -> str:
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


def _convert_union_type(annotation) -> str:
    """Convert Union[A, B] to A | B."""
    if annotation.args:
        type_parts = []
        for arg in annotation.args:
            ts_type = _convert_annotation_to_typescript(arg, is_top_level=False)
            type_parts.append(ts_type)
        return " | ".join(type_parts)
    return "any"


def _convert_literal_type(annotation) -> str:
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


def _convert_tuple_type(annotation) -> str:
    """Convert Tuple[A, B] to [A, B]."""
    if annotation.args:
        type_parts = []
        for arg in annotation.args:
            ts_type = _convert_annotation_to_typescript(arg, is_top_level=False)
            type_parts.append(ts_type)
        return f"[{', '.join(type_parts)}]"
    else:
        return "[any]"


def _convert_optional_type(annotation, is_top_level: bool = False) -> str:
    """Convert Optional[T] to T (top-level) or T | null (nested)."""
    if annotation.args:
        inner_type = _convert_annotation_to_typescript(annotation.args[0], is_top_level=False)
        if is_top_level:
            return inner_type
        else:
            return f"{inner_type} | null"
    return "any"


def _escape_typescript_string(value: str) -> str:
    """Escape string literals for TypeScript."""
    return value.replace('"', '\\"').replace("\\", "\\\\")


def _is_field_optional(field: Field) -> bool:
    """Determine if field should be optional in TypeScript."""
    return (
        field.is_optional or
        field.annotation.is_optional()
    )


def test_v2_interface_generator():
    """Test V2 interface generator with various ModelNode scenarios."""
    from fluidkit.core.schema import ModelNode, Field, FieldAnnotation, FieldConstraints, ModuleLocation, BaseType, ContainerType
    
    # Create test location
    location = ModuleLocation(module_path="test.models", file_path="/test/models.py")
    
    # Test 1: Simple Interface
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
        location=location,
        docstring="Simple user model",
        inheritance=["BaseModel"],
        is_enum=False
    )
    
    result = generate_interface(simple_user)
    print(result)
    print("\n" + "="*50 + "\n")
    
    # Test 2: Enum
    print("=== TEST 2: Enum ===")
    status_enum = ModelNode(
        name="UserStatus",
        fields=[
            Field(
                name="ACTIVE",
                annotation=FieldAnnotation(base_type=BaseType.STRING),
                default="active"
            ),
            Field(
                name="INACTIVE",
                annotation=FieldAnnotation(base_type=BaseType.STRING),
                default="inactive"
            )
        ],
        location=location,
        docstring="User status enumeration",
        inheritance=["Enum"],
        is_enum=True
    )
    
    result = generate_interface(status_enum)
    print(result)
    print("\n" + "="*50 + "\n")
    
    # Test 3: Type Alias
    print("=== TEST 3: Type Alias ===")
    email_alias = ModelNode(
        name="EmailStr",
        fields=[],
        location=location,
        docstring="Type alias for EmailStr",
        inheritance=[],
        is_enum=False,
        metadata={'is_type_alias': True, 'typescript_type': 'any'}
    )
    
    result = generate_interface(email_alias)
    print(result)
    print("\n" + "="*50 + "\n")
    
    # Test 4: Complex Types with Constraints
    print("=== TEST 4: Complex Types with Constraints ===")
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
                    max_value=120,
                    deprecated=True
                ),
                description="User age"
            ),
            Field(
                name="profile",
                annotation=FieldAnnotation(
                    container=ContainerType.OPTIONAL,
                    args=[FieldAnnotation(custom_type="Profile")]
                ),
                default=None
            )
        ],
        location=location,
        inheritance=["BaseModel"],
        is_enum=False
    )
    
    result = generate_interface(validated_user)
    print(result)


if __name__ == "__main__":
    test_v2_interface_generator()
