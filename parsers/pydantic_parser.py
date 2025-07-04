import ast
from core.models import *
from core.ast_utils import (infer_annotation_from_value,
extract_type_annotation, extract_basic_default_value, extract_docstring)

# TODO: Support for forward references in models

# TODO: Edge cases it misses (but we can handle later):
# - from pydantic import BaseModel as BM → class User(BM)
# - class User(CustomBase) where CustomBase(BaseModel)

class PydanticParser:

    def parse_file(self, file_path: str) -> CompilationUnit:
        with open(file_path, 'r') as f:
            code = f.read()
        tree = ast.parse(code)
        return self.parse_ast(tree, source_file=file_path)

    def parse_ast(self, tree: ast.AST, source_file: str) -> CompilationUnit:
        compilation_unit = CompilationUnit(
            models=[],
            imports=[],
            metadata={},
            functions=[],
            assignments=[],
            source_file=source_file
        )

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                fields = []
                docstring = None
                inheritance = []
                is_interface = False

                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Name) and decorator.id == "interface":
                        is_interface = True
                        break
                        
                if is_interface:
                    inheritance = [base.id for base in node.bases if isinstance(base, ast.Name)]
                    docstring = extract_docstring(node)

                    for item in node.body:
                        if isinstance(item, ast.AnnAssign):
                            field_info = self._extract_field_info(item.value)
                            annotation = extract_type_annotation(item.annotation)
                            
                            fields.append(Field(
                                name=item.target.id,
                                annotation=annotation,  
                                default=field_info.default,
                                constraints=field_info.constraints,
                                description=field_info.description
                            ))

                        elif isinstance(item, ast.Assign):
                            for target in item.targets:
                                if isinstance(target, ast.Name):
                                    field_info = self._extract_field_info(item.value)
                                    annotation = infer_annotation_from_value(field_info.default)
                                    
                                    fields.append(Field(
                                        name=target.id,
                                        annotation=annotation,  
                                        default=field_info.default,
                                        constraints=field_info.constraints,
                                        description=field_info.description
                                    ))

                    compilation_unit.models.append(Model(
                        name=node.name,
                        fields=fields,
                        docstring=docstring,
                        location=SourceLocation(
                            file=source_file,
                            line=node.lineno,
                            column=node.col_offset
                        ),
                        is_pydantic_model="BaseModel" in inheritance,
                        inheritance=None if inheritance == [] else inheritance
                    ))
        return compilation_unit

    def _extract_field_info(self, node: ast.AST) -> FieldInfo:
        """Extract default value and metadata from Field() calls in single pass"""
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
            
            # Handle keyword args in single iteration
            for keyword in node.keywords:
                if keyword.arg == "default":
                    default_value = self._extract_default_value(keyword.value)  # Recursive for nested calls
                elif keyword.arg == "description":
                    if isinstance(keyword.value, ast.Constant):
                        description = keyword.value.value
                elif keyword.arg in ["ge", "le", "gt", "lt", "min_length", "max_length", "regex"]:
                    # Extract other Field constraints for future use
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

    def _extract_default_value(self, node: ast.AST) -> Any:
        """Extract default value from any node (including nested Field() calls)"""
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "Field":
            # Handle Field() calls directly here instead of separate method
            # Handle positional args: Field(...) or Field(25)
            if node.args:
                arg = node.args[0]
                if isinstance(arg, ast.Constant):
                    if arg.value is ...:  # Field(...) - required field
                        return None
                    else:  # Field(25) - positional default
                        return arg.value
            
            # Handle keyword args: Field(default=25)
            for keyword in node.keywords:
                if keyword.arg == "default":
                    return self._extract_default_value(keyword.value)  # Recursive!
            
            return None  # No default = required field
        else:
            # Use generic extraction for non-Field calls
            return extract_basic_default_value(node)
