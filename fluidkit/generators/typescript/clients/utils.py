"""
Shared utilities for TypeScript client generation.

Contains common code used by both fetch and streaming client generators,
including code building helpers, parameter processing, and type conversion.
"""

from typing import List, Dict, Set, Union
from fluidkit.core.schema import RouteNode, Field, FieldAnnotation, ParameterType


class CodeBuilder:
    """Helper for building indented code with automatic indent management."""
    
    def __init__(self, indent_size: int = 2):
        self.lines = []
        self.indent_level = 0
        self.indent_size = indent_size
    
    def add_line(self, line: str = ""):
        """Add line with current indentation."""
        if line.strip():  # Only indent non-empty lines
            indented = " " * (self.indent_level * self.indent_size) + line
            self.lines.append(indented)
        else:
            self.lines.append("")  # Empty line
    
    def add_lines(self, lines: List[str]):
        """Add multiple lines."""
        for line in lines:
            self.add_line(line)
    
    def indent(self):
        """Increase indentation level."""
        self.indent_level += 1
    
    def dedent(self):
        """Decrease indentation level."""
        old_level = self.indent_level
        self.indent_level = max(0, self.indent_level - 1)
    
    def add_block(self, opening: str, closing: str = "}"):
        """Context manager for blocks like { ... }."""
        return BlockContext(self, opening, closing)
    
    def get_code(self) -> str:
        """Get final code string."""
        return "\n".join(self.lines)


class BlockContext:
    """Context manager for automatic block indentation."""
    
    def __init__(self, builder: CodeBuilder, opening: str, closing: str):
        self.builder = builder
        self.closing = closing
        self.builder.add_line(opening)
        self.builder.indent()
    
    def __enter__(self):
        return self.builder
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Dedent first, then add closing line
        self.builder.dedent()
        self.builder.add_line(self.closing)
        return None


# === PARAMETER CLASSIFICATION HELPERS === #

def get_client_parameters(route: RouteNode) -> List[Field]:
    """Get parameters that should appear in function signature."""
    client_types = {ParameterType.PATH, ParameterType.QUERY, ParameterType.BODY, 
                   ParameterType.FORM, ParameterType.FILE}
    
    return [param for param in route.parameters 
            if param.constraints and param.constraints.parameter_type in client_types]


def get_client_parameters_for_method(route: RouteNode, method: str) -> List[Field]:
    """Get parameters appropriate for specific HTTP method."""
    all_params = get_client_parameters(route)
    
    # HTTP semantic filtering
    if method.upper() in ["GET", "DELETE", "HEAD", "OPTIONS"]:
        # These methods typically don't have bodies
        allowed_types = {ParameterType.PATH, ParameterType.QUERY}
    else:
        # POST, PUT, PATCH can have bodies
        allowed_types = {ParameterType.PATH, ParameterType.QUERY, ParameterType.BODY, 
                        ParameterType.FORM, ParameterType.FILE}
    
    return [param for param in all_params 
            if param.constraints.parameter_type in allowed_types]


def get_parameters_by_type(route: RouteNode, param_type: ParameterType) -> List[Field]:
    """Get all parameters of a specific type."""
    return [param for param in route.parameters 
            if param.constraints and param.constraints.parameter_type == param_type]


def get_parameters_by_type_for_method(route: RouteNode, param_type: ParameterType, method: str) -> List[Field]:
    """Get parameters of specific type that are appropriate for the HTTP method."""
    method_params = get_client_parameters_for_method(route, method)
    return [param for param in method_params 
            if param.constraints and param.constraints.parameter_type == param_type]


def sort_parameters_for_signature(parameters: List[Field]) -> List[Field]:
    """Sort parameters for function signature: required first, then optional."""
    required_params = [p for p in parameters if not p.is_optional]
    optional_params = [p for p in parameters if p.is_optional]
    return required_params + optional_params


# === TYPE CONVERSION === #

def convert_annotation_to_typescript(annotation: FieldAnnotation, is_top_level: bool = False) -> str:
    """Convert FieldAnnotation to TypeScript type string."""
    # Import and reuse the type conversion logic from interface generator
    try:
        from fluidkit.generators.typescript.interfaces import _convert_annotation_to_typescript as convert_type
        return convert_type(annotation, is_top_level)
    except ImportError:
        # Fallback if interface generator not available
        if annotation.custom_type:
            return annotation.custom_type
        elif annotation.base_type:
            mapping = {
                "string": "string",
                "number": "number", 
                "boolean": "boolean",
                "any": "any",
                "unknown": "unknown",
                "null": "null"
            }
            return mapping.get(annotation.base_type.value, "any")
        else:
            return "any"


# === JSDOC GENERATION === #

def generate_function_jsdoc(route: RouteNode, method: str = None) -> str:
    """Generate JSDoc for function or method."""
    parts = []
    
    # Add function description
    if route.docstring:
        parts.append(route.docstring)
    else:
        if method:
            parts.append(f"{method.upper()} {route.path}")
        else:
            methods_str = ", ".join(route.methods)
            parts.append(f"{route.path} - {methods_str} operations")
    
    # Add parameter documentation
    client_params = get_client_parameters_for_method(route, method) if method else get_client_parameters(route)
    sorted_params = sort_parameters_for_signature(client_params)

    if sorted_params:
        parts.append("")  # Empty line separator
        for param in sorted_params:
            param_line = f"@param {param.name}"
            if param.description:
                param_line += f" - {param.description}"
            parts.append(param_line)
    
    # Add security requirements
    security_docs = generate_security_jsdoc(route)
    if security_docs:
        parts.append("")  # Empty line separator
        parts.extend(security_docs)
    
    return wrap_jsdoc(parts)


def generate_security_jsdoc(route: RouteNode) -> List[str]:
    """Generate security requirements documentation."""
    if not route.security_requirements:
        return []
    
    security_lines = ["**Security Requirements:**"]
    
    for req in route.security_requirements:
        if req.scheme_type == "oauth2":
            if req.scopes:
                scopes_str = ", ".join(req.scopes)
                security_lines.append(f"- OAuth2: {req.scheme_name} (scopes: {scopes_str})")
            else:
                security_lines.append(f"- OAuth2: {req.scheme_name}")
        elif req.scheme_type == "apiKey":
            location = req.location or "header"
            param_name = req.parameter_name or req.scheme_name
            security_lines.append(f"- API Key: {param_name} in {location}")
        elif req.scheme_type == "http":
            security_lines.append(f"- HTTP: {req.scheme_name}")
        else:
            security_lines.append(f"- {req.scheme_name}")
        
        if req.description:
            security_lines[-1] += f" - {req.description}"
    
    return security_lines


def wrap_jsdoc(parts: List[str]) -> str:
    """Wrap JSDoc parts in proper comment syntax."""
    if not parts:
        return ""
    
    lines = ["/**"]
    for part in parts:
        if part == "":  # Empty line separator
            lines.append(" *")
        else:
            lines.append(f" * {part}")
    lines.append(" */")
    
    return "\n".join(lines)


# === URL BUILDING === #

def generate_url_building_lines(builder: CodeBuilder, route: RouteNode, get_base_url_fn: str, method: str = None):
    """Generate URL construction with path and query parameters."""
    
    # Start with base URL and path
    path = route.path
    
    # Handle path parameters - replace {param} with ${param}
    path_params = get_parameters_by_type(route, ParameterType.PATH)
    if path_params:
        for param in path_params:
            path = path.replace(f"{{{param.name}}}", f"${{{param.name}}}")
        builder.add_line(f"let url = `${{{get_base_url_fn}()}}{path}`;")
    else:
        builder.add_line(f"let url = `${{{get_base_url_fn}()}}{path}`;")
    
    # Handle query parameters
    if method:
        query_params = get_parameters_by_type_for_method(route, ParameterType.QUERY, method)
    else:
        query_params = get_parameters_by_type(route, ParameterType.QUERY)
    
    if query_params:
        builder.add_line()
        builder.add_line("const searchParams = new URLSearchParams();")
        
        for param in query_params:
            if param.is_optional:
                builder.add_line(f"if ({param.name} !== undefined) {{")
                builder.indent()
                builder.add_line(f"searchParams.set('{param.name}', String({param.name}));")
                builder.dedent()
                builder.add_line("}")
            else:
                builder.add_line(f"searchParams.set('{param.name}', String({param.name}));")
        
        builder.add_line("if (searchParams.toString()) {")
        builder.indent()
        builder.add_line("url += `?${searchParams.toString()}`;")
        builder.dedent()
        builder.add_line("}")


# === SIGNATURE GENERATION === #

def generate_function_signature(
    route: RouteNode, 
    method: str, 
    return_type: str,
    additional_params: List[str] = None
) -> str:
    """Generate function signature for single-method function."""
    client_params = get_client_parameters_for_method(route, method)
    sorted_params = sort_parameters_for_signature(client_params)
    
    # Build parameter list
    param_parts = []
    for param in sorted_params:
        typescript_type = convert_annotation_to_typescript(param.annotation, is_top_level=True)
        param_name = param.name
        if param.is_optional:
            param_name += "?"
        param_parts.append(f"{param_name}: {typescript_type}")
    
    # Add additional parameters (like callbacks, options)
    if additional_params:
        param_parts.extend(additional_params)
    
    params_str = ", ".join(param_parts)
    
    return f"export const {route.name} = async ({params_str}): {return_type} => {{"

def generate_sync_function_signature(
    route: RouteNode, 
    method: str, 
    return_type: str,
    additional_params: List[str] = None
) -> str:
    """Generate synchronous function signature (no async)."""
    client_params = get_client_parameters_for_method(route, method)
    sorted_params = sort_parameters_for_signature(client_params)
    
    # Build parameter list
    param_parts = []
    for param in sorted_params:
        typescript_type = convert_annotation_to_typescript(param.annotation, is_top_level=True)
        param_name = param.name
        if param.is_optional:
            param_name += "?"
        param_parts.append(f"{param_name}: {typescript_type}")
    
    # Add additional parameters
    if additional_params:
        param_parts.extend(additional_params)
    
    params_str = ", ".join(param_parts)
    
    return f"export const {route.name} = ({params_str}): {return_type} => {{"


def generate_sync_method_signature(
    route: RouteNode, 
    method: str, 
    return_type: str,
    additional_params: List[str] = None
) -> str:
    """Generate synchronous method signature (no async)."""
    client_params = get_client_parameters_for_method(route, method)
    sorted_params = sort_parameters_for_signature(client_params)
    
    # Build parameter list
    param_parts = []
    for param in sorted_params:
        typescript_type = convert_annotation_to_typescript(param.annotation, is_top_level=True)
        param_name = param.name
        if param.is_optional:
            param_name += "?"
        param_parts.append(f"{param_name}: {typescript_type}")
    
    # Add additional parameters
    if additional_params:
        param_parts.extend(additional_params)
    
    params_str = ", ".join(param_parts)
    
    return f"({params_str}): {return_type} => {{"

def generate_method_signature(
    route: RouteNode, 
    method: str, 
    return_type: str,
    additional_params: List[str] = None
) -> str:
    """Generate method signature for multi-method object."""
    client_params = get_client_parameters_for_method(route, method)
    sorted_params = sort_parameters_for_signature(client_params)
    
    # Build parameter list
    param_parts = []
    for param in sorted_params:
        typescript_type = convert_annotation_to_typescript(param.annotation, is_top_level=True)
        param_name = param.name
        if param.is_optional:
            param_name += "?"
        param_parts.append(f"{param_name}: {typescript_type}")
    
    # Add additional parameters
    if additional_params:
        param_parts.extend(additional_params)
    
    params_str = ", ".join(param_parts)
    
    return f"async ({params_str}): {return_type} => {{"


def generate_return_type(route: RouteNode, wrapper_type: str, api_result_type: str) -> str:
    """Generate return type based on route and wrapper type."""
    if route.return_type:
        inner_type = convert_annotation_to_typescript(route.return_type, is_top_level=True)
        return f"{wrapper_type}<{api_result_type}<{inner_type}>>"
    else:
        return f"{wrapper_type}<{api_result_type}<any>>"
    