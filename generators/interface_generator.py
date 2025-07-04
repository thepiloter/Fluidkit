from core.models import *
from typing import List

class TypeScriptGenerator:
    def __init__(self):
        self.generated_types = set()
    
    def generate(self, unit: CompilationUnit) -> str:
        """Main entry point - generate complete TypeScript output"""
        output = []
        
        for model in unit.models:
            model_output = self._generate_model(model)
            if model_output:
                output.append(model_output)
        
        return "\n\n".join(output)
    
    def _generate_model(self, model: Model) -> str:
        """Generate interface or enum based on model type"""
        if self._is_enum_model(model):
            return self._generate_enum(model)
        else:
            return self._generate_interface(model)
    
    def _is_enum_model(self, model: Model) -> bool:
        """Determine if model represents an enum"""
        # Pydantic models are always interfaces
        if model.is_pydantic_model:
            return False
        
        # For non-Pydantic classes, check if all fields are constants
        return (model.fields and 
                all(field.default is not None and 
                    field.annotation.is_simple() 
                    for field in model.fields))
    
    # === INTERFACE GENERATION ===
    def _generate_interface(self, model: Model) -> str:
        """Generate TypeScript interface"""
        lines = []
        
        header = self._generate_interface_header(model)
        if header:
            lines.append(header)
        
        lines.append(f"export interface {model.name} {{")
        
        for field in model.fields:
            field_line = self._generate_interface_field(field)
            if field_line:
                lines.append(f"  {field_line}")
        
        lines.append("}")
        
        return "\n".join(lines)
        
    def _generate_interface_header(self, model: Model) -> str:
        """Generate interface header with field overview"""
        lines = []
        lines.append("/**")
        
        if model.docstring:
            lines.append(f" * {model.docstring}")
            if model.fields:
                lines.append(" *")
        
        if model.fields:
            for field in model.fields:
                field_line = f" * @property {field.name}"
                if field.description:
                    field_line += f" - {field.description}"
                lines.append(field_line)
        
        lines.append(" */")
        return "\n".join(lines)
        
    def _generate_interface_field(self, field: Field) -> str:
        """Generate single interface field with helpful JSDoc only"""
        parts = []
        
        # Only add JSDoc if we have useful information
        jsdoc_parts = []
        if field.description:
            jsdoc_parts.append(field.description)
        
        if field.default is not None:
            if isinstance(field.default, str):
                jsdoc_parts.append(f'@default "{field.default}"')
            else:
                jsdoc_parts.append(f"@default {field.default}") 
                
        # Only generate JSDoc if we have something useful to say
        if jsdoc_parts:
            if len(jsdoc_parts) == 1:
                parts.append(f"/** {jsdoc_parts[0]} */")
            else:
                parts.append("/**")
                for part in jsdoc_parts:
                    parts.append(f" * {part}")
                parts.append(" */")
        
        # Generate field declaration
        field_name = field.name
        if self._is_field_optional(field):
            field_name += "?"
        
        typescript_type = self._convert_annotation_to_typescript(field.annotation, is_top_level=True)
        field_declaration = f"{field_name}: {typescript_type};"
        parts.append(field_declaration)
        
        return "\n  ".join(parts)
        
    # === ENUM GENERATION ===
    def _generate_enum(self, model: Model) -> str:
        """Generate TypeScript enum"""
        lines = []
        
        header = self._generate_interface_header(model)
        if header:
            lines.append(header)
        
        lines.append(f"export enum {model.name} {{")
        
        for field in model.fields:
            field_line = self._generate_enum_field(field)
            if field_line:
                lines.append(f"  {field_line}")
        
        lines.append("}")

        return "\n".join(lines)
        
    def _generate_enum_field(self, field: Field) -> str:
        """Generate single enum field"""
        if isinstance(field.default, str):
            escaped_value = self._escape_typescript_string(field.default)
            return f'{field.name} = "{escaped_value}",'
        else:
            return f"{field.name} = {field.default},"
        
    # === TYPE CONVERSION (Core Logic) ===
    def _convert_annotation_to_typescript(self, annotation: FieldAnnotation, is_top_level: bool = False) -> str:
        """Convert IR annotation to TypeScript type string"""
        if annotation.container:
            return self._convert_container_type(annotation, is_top_level)
        elif annotation.custom_type:
            return annotation.custom_type
        elif annotation.base_type:
            return self._convert_base_type(annotation.base_type)
        else:
            return "any"
        
    def _convert_base_type(self, base_type: BaseType) -> str:
        """Convert base types to TypeScript"""
        mapping = {
            BaseType.STRING: "string",
            BaseType.NUMBER: "number", 
            BaseType.BOOLEAN: "boolean",
            BaseType.ANY: "any",
            BaseType.UNKNOWN: "unknown",
            BaseType.NULL: "null"
        }
        return mapping.get(base_type, "any")
        
    def _convert_container_type(self, annotation: FieldAnnotation, is_top_level: bool = False) -> str:
        """Convert container types to TypeScript"""
        if annotation.container == ContainerType.OPTIONAL:
            return self._convert_optional_type(annotation, is_top_level)
        elif annotation.container == ContainerType.ARRAY:
            return self._convert_array_type(annotation)
        elif annotation.container == ContainerType.OBJECT:
            return self._convert_object_type(annotation)
        elif annotation.container == ContainerType.TUPLE:
            return self._convert_tuple_type(annotation)
        elif annotation.container == ContainerType.UNION:
            return self._convert_union_type(annotation)
        elif annotation.container == ContainerType.LITERAL:
            return self._convert_literal_type(annotation)
        else:
            return "any"
        
    def _convert_array_type(self, annotation: FieldAnnotation) -> str:
        """Convert List[T] to T[]"""
        if annotation.args:
            inner_type = self._convert_annotation_to_typescript(annotation.args[0], is_top_level=False)
            if "|" in inner_type or "&" in inner_type:
                return f"({inner_type})[]"
            else:
                return f"{inner_type}[]"
        return "any[]"
            
    def _convert_object_type(self, annotation: FieldAnnotation) -> str:
        """Convert Dict[K, V] to Record<K, V>"""
        if len(annotation.args) >= 2:
            key_type = self._convert_annotation_to_typescript(annotation.args[0], is_top_level=False)
            value_type = self._convert_annotation_to_typescript(annotation.args[1], is_top_level=False)
            return f"Record<{key_type}, {value_type}>"
        elif len(annotation.args) == 1:
            value_type = self._convert_annotation_to_typescript(annotation.args[0], is_top_level=False)
            return f"Record<string, {value_type}>"
        else:
            return "Record<string, any>"
        
    def _convert_union_type(self, annotation: FieldAnnotation) -> str:
        """Convert Union[A, B] to A | B"""
        if annotation.args:
            type_parts = []
            for arg in annotation.args:
                ts_type = self._convert_annotation_to_typescript(arg, is_top_level=False)
                type_parts.append(ts_type)
            return " | ".join(type_parts)
        return "any"
        
    def _convert_literal_type(self, annotation: FieldAnnotation) -> str:
        """Convert Literal["a", "b"] to "a" | "b" """
        if annotation.literal_values:
            literal_parts = []
            for value in annotation.literal_values:
                if isinstance(value, str):
                    escaped = self._escape_typescript_string(value)
                    literal_parts.append(f'"{escaped}"')
                else:
                    literal_parts.append(str(value))
            return " | ".join(literal_parts)
        return "any"
        
    def _convert_tuple_type(self, annotation: FieldAnnotation) -> str:
        """Convert Tuple[A, B] to [A, B]"""
        if annotation.args:
            type_parts = []
            for arg in annotation.args:
                ts_type = self._convert_annotation_to_typescript(arg, is_top_level=False)
                type_parts.append(ts_type)
            return f"[{', '.join(type_parts)}]"
        else:
            return "[any]"
        
    def _convert_optional_type(self, annotation: FieldAnnotation, is_top_level: bool = False) -> str:
        """Convert Optional[T] to T (top-level) or T | null (nested)"""
        if annotation.args:
            inner_type = self._convert_annotation_to_typescript(annotation.args[0], is_top_level=False)
            if is_top_level:
                return inner_type
            else:
                return f"{inner_type} | null"
        return "any"
        
    # === UTILITIES ===
    def _escape_typescript_string(self, value: str) -> str:
        """Escape string literals for TypeScript"""
        return value.replace('"', '\\"').replace("\\", "\\\\")
        
    def _generate_jsdoc_comment(self, text: str) -> str:
        """Generate JSDoc comment"""
        
    def _is_field_optional(self, field: Field) -> bool:
        """Determine if field should be optional in TypeScript"""
        return (
            field.is_optional or  # Has default value
            field.annotation.is_optional()  # Is Optional[T] or Union with None
        )
