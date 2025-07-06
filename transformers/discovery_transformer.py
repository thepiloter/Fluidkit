import ast, os
from pathlib import Path
from core.nodes import *
from typing import List, Optional, Dict, Any, Set
from core.ast_utils import (extract_type_annotation, extract_field_info, FieldInfo, FastAPIInfo,
extract_basic_default_value, extract_docstring,  infer_annotation_from_value, extract_fastapi_info)


class DiscoveryTransformer(ast.NodeVisitor):
    """
    Pattern-based AST discovery transformer for FluidKit.
    
    Discovers @interface models and FastAPI routes with explicit annotations,
    leveraging the robust recursive type annotation system for consistent
    type handling across models and routes.
    """
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.models: List[ModelNode] = []
        self.routes: List[RouteNode] = []
        self.imports: List[ImportNode] = []

    def transform(self, source_code: str) -> CompilationUnit:
        """
        Transform Python source code into FluidKit's unified IR.
        
        Args:
            source_code: Python source code to analyze
            
        Returns:
            CompilationUnit containing discovered models, routes, and imports
        """
        tree = ast.parse(source_code)
        self.visit(tree)
        
        return CompilationUnit(
            models=self.models,
            routes=self.routes,
            imports=self.imports,
            source_file=self.file_path
        )

    # === IMPORT DISCOVERY === #
    
    def visit_Import(self, node: ast.Import):
        """Process import statements: import fastapi"""
        for alias in node.names:
            self.imports.append(ImportNode(
                import_type=ImportType.MODULE,
                module=alias.name,
                alias=alias.asname,
                is_relative=False,
                ast_node=node,
                line_number=node.lineno,
                names=[]
            ))
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Process from imports: from fastapi import APIRouter"""
        module = node.module or ""
        is_relative = node.level > 0
        
        if is_relative:
            dots = "." * node.level
            full_module = dots + module if module else dots
        else:
            full_module = module

        names = []
        import_type = ImportType.FROM_IMPORT

        for alias in node.names:
            if alias.name == "*":
                import_type = ImportType.STAR_IMPORT
                names = ["*"]
                break
            else:
                names.append(alias.name)

        self.imports.append(ImportNode(
            import_type=import_type,
            module=full_module,
            alias=None,
            is_relative=is_relative,
            ast_node=node,
            line_number=node.lineno,
            names=names
        ))
        self.generic_visit(node)

    # === MODEL DISCOVERY === #
    
    def visit_ClassDef(self, node: ast.ClassDef):
        """Discover @interface decorated classes as ModelNodes"""
        if self._has_interface_decorator(node):
            model_node = self._create_model_node(node)
            self.models.append(model_node)
        self.generic_visit(node)

    def _has_interface_decorator(self, class_node: ast.ClassDef) -> bool:
        """Check if class has @interface decorator"""
        for decorator in class_node.decorator_list:
            if isinstance(decorator, ast.Name) and decorator.id == "interface":
                return True
        return False

    def _create_model_node(self, class_node: ast.ClassDef) -> ModelNode:
        """Convert @interface class to ModelNode with full type analysis"""
        fields = []
        inheritance = []
        
        # Extract base classes
        for base in class_node.bases:
            if isinstance(base, ast.Name):
                inheritance.append(base.id)
            elif isinstance(base, ast.Attribute):
                inheritance.append(self._get_attribute_name(base))

        # Process class body for fields
        for item in class_node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                # Type annotated field: name: str = "default"
                field = self._create_model_field_from_annotation(item)
                fields.append(field)
                
            elif isinstance(item, ast.Assign):
                # Assignment without annotation: name = "default" 
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        field = self._create_model_field_from_assignment(target, item)
                        fields.append(field)

        return ModelNode(
            name=class_node.name,
            fields=fields,
            docstring=extract_docstring(class_node),
            inheritance=inheritance if inheritance else None,
            location=SourceLocation(
                file=self.file_path,
                line=class_node.lineno,
                column=class_node.col_offset
            ),
            ast_node=class_node
        )

    def _create_model_field_from_annotation(self, item: ast.AnnAssign) -> Field:
        """Create Field from annotated assignment using recursive type extraction"""
        # Use robust recursive type annotation system
        field_info = extract_field_info(item.value)
        annotation = extract_type_annotation(item.annotation)
        
        return Field(
            name=item.target.id,
            annotation=annotation,
            default=field_info.default,
            description=field_info.description,
            constraints=self._convert_to_field_constraints(field_info)
        )

    def _create_model_field_from_assignment(self, target: ast.Name, item: ast.Assign) -> Field:
        """Create Field from simple assignment, inferring type from value"""
        field_info = extract_field_info(item.value)
        annotation = infer_annotation_from_value(field_info.default)
        
        return Field(
            name=target.id,
            annotation=annotation,
            default=field_info.default,
            constraints=self._convert_to_field_constraints(field_info),
            description=field_info.description
        )
    
    def _convert_to_field_constraints(self, field_info: FieldInfo) -> FieldConstraints:
        """
        Convert FieldInfo constraints to FieldConstraints structure.
        
        Maps raw Pydantic Field() constraints to FluidKit's unified constraint system.
        """
        constraints = FieldConstraints()
        
        if not field_info.constraints:
            return constraints
        
        # Map Pydantic validation constraints to structured fields
        raw_constraints = field_info.constraints
        
        # Numeric range constraints
        if "ge" in raw_constraints:
            constraints.min_value = float(raw_constraints["ge"])
        elif "gt" in raw_constraints:
            # gt (greater than) is exclusive, but we store as min_value
            # Could add a flag for exclusive vs inclusive later if needed
            constraints.min_value = float(raw_constraints["gt"])
        
        if "le" in raw_constraints:
            constraints.max_value = float(raw_constraints["le"])
        elif "lt" in raw_constraints:
            # lt (less than) is exclusive, but we store as max_value
            constraints.max_value = float(raw_constraints["lt"])
        
        # String/array length constraints
        if "min_length" in raw_constraints:
            constraints.min_length = int(raw_constraints["min_length"])
        
        if "max_length" in raw_constraints:
            constraints.max_length = int(raw_constraints["max_length"])
        
        # Pattern validation
        if "regex" in raw_constraints:
            constraints.regex_pattern = str(raw_constraints["regex"])
        
        # Store any unrecognized constraints in custom field for future extensibility
        unhandled_constraints = {}
        handled_keys = {"ge", "gt", "le", "lt", "min_length", "max_length", "regex"}
        
        for key, value in raw_constraints.items():
            if key not in handled_keys:
                unhandled_constraints[key] = value
        
        if unhandled_constraints:
            constraints.custom = unhandled_constraints
        
        return constraints

    # === ROUTE DISCOVERY === #
    
    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Discover FastAPI route functions"""
        route_info = self._extract_route_decorator(node)
        if route_info:
            route_node = self._create_route_node(node, route_info)
            self.routes.append(route_node)
        self.generic_visit(node)
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Discover async FastAPI route functions"""
        route_info = self._extract_route_decorator(node)
        if route_info:
            route_node = self._create_route_node(node, route_info)
            self.routes.append(route_node)
        self.generic_visit(node)

    def _extract_route_decorator(self, func_node: ast.FunctionDef) -> Optional[Dict[str, str]]:
        """
        Extract route information from FastAPI decorator patterns.
        
        Accepts only strict patterns:
        - @router.get("/path") 
        - @router.get(path="/path")
        - @app.post("/path")
        - @app.post(path="/path")
        
        Rejects anything else to avoid false positives with Flask, etc.
        """
        for decorator in func_node.decorator_list:
            if (isinstance(decorator, ast.Call) and 
                isinstance(decorator.func, ast.Attribute) and
                isinstance(decorator.func.value, ast.Name)):

                base_object = decorator.func.value.id
            
                # Strict FastAPI pattern validation - only accept router/app
                if base_object not in ["router", "app"]:
                    continue
                
                # Extract path from decorator arguments
                path = self._extract_path_from_decorator(decorator)
                
                return {
                    'object': base_object,                 # "router" or "app"
                    'method': decorator.func.attr,         # "get", "post", etc.
                    'path': path or "/"                    # URL path pattern
                }
        return None

    def _extract_path_from_decorator(self, decorator: ast.Call) -> Optional[str]:
        """
        Extract path string from decorator arguments.
        
        Handles both patterns:
        - @router.get("/users") - positional argument
        - @router.get(path="/users") - keyword argument
        """
        # Check positional arguments first: @router.get("/path")
        if decorator.args:
            first_arg = decorator.args[0]
            if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                return first_arg.value
        
        # Check keyword arguments: @router.get(path="/path")
        for keyword in decorator.keywords:
            if keyword.arg == "path" and isinstance(keyword.value, ast.Constant):
                if isinstance(keyword.value.value, str):
                    return keyword.value.value
        
        return None

    def _create_route_node(self, func_node: ast.FunctionDef, route_info: Dict) -> RouteNode:
        """Convert FastAPI route function to RouteNode with full parameter analysis"""
        parameters = []
        
        # Process function parameters
        args = func_node.args
        defaults = args.defaults or []
        num_args = len(args.args)
        num_defaults = len(defaults)
        
        for i, arg in enumerate(args.args):
            # Skip 'self' and 'cls' parameters
            if arg.arg in ('self', 'cls'):
                continue
                
            # Get default value if available
            default_index = i - (num_args - num_defaults)
            default_node = defaults[default_index] if default_index >= 0 else None
            
            # Use recursive type annotation extraction
            annotation = extract_type_annotation(arg.annotation) if arg.annotation else FieldAnnotation(base_type=BaseType.ANY)
            default_value = extract_basic_default_value(default_node) if default_node else None
            constraints = self._extract_route_param_constraints(default_node)
            
            parameters.append(Field(
                name=arg.arg,
                annotation=annotation,
                default=default_value,
                constraints=constraints
            ))

        # Extract return type annotation
        return_type = None
        if func_node.returns:
            return_type = extract_type_annotation(func_node.returns)

        return RouteNode(
            name=func_node.name,
            method=route_info['method'].upper(),
            path=route_info['path'],
            parameters=parameters,
            return_type=return_type,
            docstring=extract_docstring(func_node),
            location=SourceLocation(
                file=self.file_path,
                line=func_node.lineno,
                column=func_node.col_offset
            ),
            ast_node=func_node
        )

    # === CONSTRAINT EXTRACTION === #
    def _extract_route_param_constraints(self, default_node: ast.AST) -> FieldConstraints:
        """
        Extract FastAPI parameter constraints for route parameters.
        
        Uses unified FastAPI info extraction to get all relevant data for
        fetch generation and JSDoc documentation.
        """
        constraints = FieldConstraints()
        
        # Use unified FastAPI info extraction
        fastapi_info = extract_fastapi_info(default_node)
        
        if fastapi_info.annotation_type:
            # Map FastAPI annotation to parameter type
            type_mapping = {
                "Query": ParameterType.QUERY,
                "Path": ParameterType.PATH,
                "Body": ParameterType.BODY,
                "Header": ParameterType.HEADER,
                "Form": ParameterType.FORM,
                "File": ParameterType.FILE,
                "Cookie": ParameterType.COOKIE,
                "Security": ParameterType.SECURITY,
                "Depends": ParameterType.DEPENDENCY,
            }
            
            constraints.parameter_type = type_mapping.get(
                fastapi_info.annotation_type, 
                ParameterType.UNKNOWN
            )
            constraints.fastapi_annotation = fastapi_info.annotation_type
            
            # Store critical fetch generation data in custom field
            if fastapi_info.alias:
                constraints.custom = constraints.custom or {}
                constraints.custom["alias"] = fastapi_info.alias
            
            if fastapi_info.embed is not None:
                constraints.custom = constraints.custom or {}
                constraints.custom["embed"] = fastapi_info.embed
            
            # Store description for JSDoc generation
            if fastapi_info.description:
                # Note: We could store this in constraints.description if we add that field
                # For now, store in custom
                constraints.custom = constraints.custom or {}
                constraints.custom["fastapi_description"] = fastapi_info.description
            
            # Extract validation constraints
            constraints = self._extract_fastapi_validation_constraints(fastapi_info, constraints)
        else:
            # No explicit FastAPI annotation - classify as unknown for V1
            constraints.parameter_type = ParameterType.UNKNOWN
        
        return constraints

    def _extract_fastapi_validation_constraints(self, fastapi_info: FastAPIInfo, constraints: FieldConstraints) -> FieldConstraints:
        """
        Extract validation constraints from FastAPI info and merge with existing constraints.
        
        Handles all FastAPI validation parameters and maps them to our unified constraint system.
        """
        if not fastapi_info.constraints:
            return constraints
        
        raw_constraints = fastapi_info.constraints
        
        # Numeric range constraints
        if "ge" in raw_constraints:
            constraints.min_value = float(raw_constraints["ge"])
        elif "gt" in raw_constraints:
            # gt (greater than) is exclusive - store with note
            constraints.min_value = float(raw_constraints["gt"])
            constraints.custom = constraints.custom or {}
            constraints.custom["min_exclusive"] = True
        
        if "le" in raw_constraints:
            constraints.max_value = float(raw_constraints["le"])
        elif "lt" in raw_constraints:
            # lt (less than) is exclusive - store with note  
            constraints.max_value = float(raw_constraints["lt"])
            constraints.custom = constraints.custom or {}
            constraints.custom["max_exclusive"] = True
        
        # String/array length constraints
        if "min_length" in raw_constraints:
            constraints.min_length = int(raw_constraints["min_length"])
        
        if "max_length" in raw_constraints:
            constraints.max_length = int(raw_constraints["max_length"])
        
        # Pattern validation
        if "regex" in raw_constraints:
            constraints.regex_pattern = str(raw_constraints["regex"])
        
        # Deprecation flag
        if "deprecated" in raw_constraints:
            constraints.deprecated = bool(raw_constraints["deprecated"])
        
        # Store any unrecognized constraints for future extensibility
        unhandled_constraints = {}
        handled_keys = {"ge", "gt", "le", "lt", "min_length", "max_length", "regex", "deprecated"}
        
        for key, value in raw_constraints.items():
            if key not in handled_keys:
                unhandled_constraints[key] = value
        
        if unhandled_constraints:
            constraints.custom = constraints.custom or {}
            constraints.custom.update(unhandled_constraints)
        
        return constraints

    # === HELPER METHODS === #
    def _get_attribute_name(self, node: ast.Attribute) -> str:
        """Convert ast.Attribute to string: module.Class → 'module.Class'"""
        if isinstance(node.value, ast.Name):
            return f"{node.value.id}.{node.attr}"
        elif isinstance(node.value, ast.Attribute):
            return f"{self._get_attribute_name(node.value)}.{node.attr}"
        return node.attr
