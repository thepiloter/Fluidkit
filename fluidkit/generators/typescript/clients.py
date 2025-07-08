"""
FluidKit V2 Fetch Wrapper Generator

Generates TypeScript fetch functions from V2 RouteNode objects with configurable
FluidKit runtime imports and clean automatic indentation management.
"""

from typing import List, Dict, Set
from fluidkit.core.constants import FluidKitRuntime
from fluidkit.core.schema import RouteNode, Field, FieldAnnotation, ParameterType, SecurityRequirement


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
        builder.add_line(opening)
        builder.indent()
    
    def __enter__(self):
        return self.builder
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.builder.dedent()
        self.builder.add_line(self.closing)


def generate_fetch_wrapper(
    route: RouteNode, 
    api_result_type: str = FluidKitRuntime.API_RESULT_TYPE,
    get_base_url_fn: str = FluidKitRuntime.GET_BASE_URL_FN, 
    handle_response_fn: str = FluidKitRuntime.HANDLE_RESPONSE_FN
) -> str:
    """
    Generate TypeScript fetch function(s) for a single RouteNode.
    
    Args:
        route: RouteNode with method(s), path, parameters, and metadata
        api_result_type: Name of the ApiResult type from FluidKit runtime
        get_base_url_fn: Name of the getBaseUrl function from FluidKit runtime
        handle_response_fn: Name of the handleResponse function from FluidKit runtime
        
    Returns:
        Complete TypeScript fetch function(s) with JSDoc as string
    """
    if route.is_single_method:
        return _generate_single_method_wrapper(route, api_result_type, get_base_url_fn, handle_response_fn)
    else:
        return _generate_multi_method_wrapper(route, api_result_type, get_base_url_fn, handle_response_fn)


def _generate_single_method_wrapper(
    route: RouteNode, 
    api_result_type: str, 
    get_base_url_fn: str, 
    handle_response_fn: str
) -> str:
    """Generate single async arrow function for single-method routes."""
    builder = CodeBuilder()
    
    method = route.methods[0]  # Single method
    
    # Generate JSDoc header
    jsdoc = _generate_function_jsdoc(route, method)
    if jsdoc:
        builder.add_lines(jsdoc.split('\n'))
    
    # Generate function with auto-indented body
    signature = _generate_function_signature(route, method, api_result_type)
    
    with builder.add_block(signature, "};"):
        _generate_function_body_lines(builder, route, method, get_base_url_fn, handle_response_fn)
    
    return builder.get_code()


def _generate_multi_method_wrapper(
    route: RouteNode, 
    api_result_type: str,
    get_base_url_fn: str, 
    handle_response_fn: str
) -> str:
    """Generate object with method properties for multi-method routes."""
    builder = CodeBuilder()
    
    # Generate object JSDoc header
    jsdoc = _generate_object_jsdoc(route)
    if jsdoc:
        builder.add_lines(jsdoc.split('\n'))
    
    # Generate object with auto-indented methods
    with builder.add_block(f"export const {route.name} = {{", "};"):
        for i, method in enumerate(route.methods):
            # Add spacing between methods
            if i > 0:
                builder.add_line()
            
            # Generate method JSDoc
            method_jsdoc = _generate_method_jsdoc(route, method)
            if method_jsdoc:
                builder.add_lines(method_jsdoc.split('\n'))
            
            # Generate method function with auto-indented body
            method_name = method.lower()
            method_signature = _generate_method_signature(route, method, api_result_type)
            
            # Determine closing based on whether this is the last method
            closing = "}," if i < len(route.methods) - 1 else "}"
            
            with builder.add_block(f"{method_name}: {method_signature}", closing):
                _generate_function_body_lines(builder, route, method, get_base_url_fn, handle_response_fn)
    
    return builder.get_code()


def _generate_function_jsdoc(route: RouteNode, method: str) -> str:
    """Generate JSDoc for single-method function."""
    parts = []
    
    # Add function description
    if route.docstring:
        parts.append(route.docstring)
    else:
        parts.append(f"{method.upper()} {route.path}")
    
    # Add parameter documentation
    client_params = _get_client_parameters_for_method(route, method)

    # Sort parameters to match function signature
    required_params = [p for p in client_params if not p.is_optional]
    optional_params = [p for p in client_params if p.is_optional]
    sorted_params = required_params + optional_params

    if sorted_params:
        parts.append("")  # Empty line separator
        for param in client_params:
            param_line = f"@param {param.name}"
            if param.description:
                param_line += f" - {param.description}"
            parts.append(param_line)
        
        parts.append("@param options - Additional fetch options")
    
    # Add security requirements
    security_docs = _generate_security_jsdoc(route)
    if security_docs:
        parts.append("")  # Empty line separator
        parts.extend(security_docs)
    
    return _wrap_jsdoc(parts)


def _generate_object_jsdoc(route: RouteNode) -> str:
    """Generate JSDoc for multi-method object."""
    parts = []
    
    # Add object description
    if route.docstring:
        parts.append(route.docstring)
    else:
        methods_str = ", ".join(route.methods)
        parts.append(f"{route.path} - {methods_str} operations")
    
    # Add security requirements if any
    security_docs = _generate_security_jsdoc(route)
    if security_docs:
        parts.append("")
        parts.extend(security_docs)
    
    return _wrap_jsdoc(parts) if parts else ""


def _generate_method_jsdoc(route: RouteNode, method: str) -> str:
    """Generate JSDoc for individual method in multi-method object."""
    parts = []
    
    # Add method description
    parts.append(f"{method.upper()} operation")
    
    # Add parameter documentation
    client_params = _get_client_parameters_for_method(route, method)

    # Sort parameters to match function signature
    required_params = [p for p in client_params if not p.is_optional]
    optional_params = [p for p in client_params if p.is_optional]
    sorted_params = required_params + optional_params

    if client_params:
        parts.append("")
        for param in client_params:
            param_line = f"@param {param.name}"
            if param.description:
                param_line += f" - {param.description}"
            parts.append(param_line)
        
        parts.append("@param options - Additional fetch options")
    
    return _wrap_jsdoc(parts)


def _generate_security_jsdoc(route: RouteNode) -> List[str]:
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


def _wrap_jsdoc(parts: List[str]) -> str:
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


def _generate_function_signature(route: RouteNode, method: str, api_result_type: str) -> str:
    """Generate function signature for single-method function."""
    client_params = _get_client_parameters_for_method(route, method)

    # Sort parameters - required first, then optional
    required_params = [p for p in client_params if not p.is_optional]
    optional_params = [p for p in client_params if p.is_optional]
    sorted_params = required_params + optional_params
    
    # Build parameter list
    param_parts = []
    for param in sorted_params:
        typescript_type = _convert_annotation_to_typescript(param.annotation, is_top_level=True)
        param_name = param.name
        if param.is_optional:
            param_name += "?"
        param_parts.append(f"{param_name}: {typescript_type}")
    
    # Add options parameter
    param_parts.append("options?: RequestInit")
    
    params_str = ", ".join(param_parts)
    
    # Generate return type
    return_type = f"Promise<{api_result_type}<any>>"
    if route.return_type:
        inner_type = _convert_annotation_to_typescript(route.return_type, is_top_level=True)
        return_type = f"Promise<{api_result_type}<{inner_type}>>"
    
    return f"export const {route.name} = async ({params_str}): {return_type} => {{"


def _generate_method_signature(route: RouteNode, method: str, api_result_type: str) -> str:
    """Generate method signature for multi-method object."""
    client_params = _get_client_parameters_for_method(route, method)

    # Sort parameters - required first, then optional
    required_params = [p for p in client_params if not p.is_optional]
    optional_params = [p for p in client_params if p.is_optional]
    sorted_params = required_params + optional_params
    
    # Build parameter list
    param_parts = []
    for param in sorted_params:
        typescript_type = _convert_annotation_to_typescript(param.annotation, is_top_level=True)
        param_name = param.name
        if param.is_optional:
            param_name += "?"
        param_parts.append(f"{param_name}: {typescript_type}")
    
    # Add options parameter
    param_parts.append("options?: RequestInit")
    
    params_str = ", ".join(param_parts)
    
    # Generate return type
    return_type = f"Promise<{api_result_type}<any>>"
    if route.return_type:
        inner_type = _convert_annotation_to_typescript(route.return_type, is_top_level=True)
        return_type = f"Promise<{api_result_type}<{inner_type}>>"
    
    return f"async ({params_str}): {return_type} => {{"


def _generate_function_body_lines(
    builder: CodeBuilder, 
    route: RouteNode, 
    method: str, 
    get_base_url_fn: str, 
    handle_response_fn: str
):
    """Generate function body implementation using CodeBuilder."""
    
    # URL building
    _generate_url_building_lines(builder, route, get_base_url_fn)
    
    # Request options building  
    _generate_request_options_lines(builder, route, method)
    
    # Fetch call and response handling
    builder.add_line()
    builder.add_line("const response = await fetch(url, requestOptions);")
    builder.add_line(f"return {handle_response_fn}(response);")


def _generate_url_building_lines(builder: CodeBuilder, route: RouteNode, get_base_url_fn: str):
    """Generate URL construction with path and query parameters."""
    
    # Start with base URL and path
    path = route.path
    
    # Handle path parameters - replace {param} with ${param}
    path_params = _get_parameters_by_type(route, ParameterType.PATH)
    if path_params:
        for param in path_params:
            path = path.replace(f"{{{param.name}}}", f"${{{param.name}}}")
        builder.add_line(f"let url = `${{{get_base_url_fn}()}}{path}`;")
    else:
        builder.add_line(f"let url = `${{{get_base_url_fn}()}}{path}`;")
    
    # Handle query parameters
    query_params = _get_parameters_by_type(route, ParameterType.QUERY)
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


def _generate_request_options_lines(builder: CodeBuilder, route: RouteNode, method: str):
    """Generate request options with method, headers, and body."""
    
    # Determine if we have a request body
    body_params = _get_parameters_by_type_for_method(route, ParameterType.BODY, method)
    form_params = _get_parameters_by_type_for_method(route, ParameterType.FORM, method)
    file_params = _get_parameters_by_type_for_method(route, ParameterType.FILE, method)
    
    has_json_body = len(body_params) > 0
    has_form_data = len(form_params) > 0 or len(file_params) > 0
    
    builder.add_line()
    
    # Build request options using block context
    with builder.add_block("const requestOptions: RequestInit = {", "};"):
        builder.add_line(f"method: '{method.upper()}',")
        
        # Headers
        if has_json_body and not has_form_data:
            with builder.add_block("headers: {", "},"):
                builder.add_line("'Content-Type': 'application/json',")
                builder.add_line("...options?.headers")
        elif not has_form_data:
            builder.add_line("headers: options?.headers,")
        else:
            # FormData sets its own Content-Type
            builder.add_line("headers: options?.headers,")
        
        # Body handling
        if has_json_body and not has_form_data:
            _generate_json_body_lines(builder, body_params)
        elif has_form_data:
            _generate_form_data_lines(builder, form_params, file_params, body_params)
        
        # Merge with user options
        builder.add_line("...options")


def _generate_json_body_lines(builder: CodeBuilder, body_params: List[Field]):
    """Generate JSON body building for body parameters."""
    if not body_params:
        return
    
    if len(body_params) == 1:
        # Single body parameter
        param = body_params[0]
        builder.add_line(f"body: JSON.stringify({param.name}),")
    else:
        # Multiple body parameters - auto-merge
        with builder.add_block("body: JSON.stringify({", "}),"):
            for param in body_params:
                builder.add_line(f"{param.name},")


def _generate_form_data_lines(builder: CodeBuilder, form_params: List[Field], 
                             file_params: List[Field], body_params: List[Field]):
    """Generate FormData building for form and file parameters."""
    
    with builder.add_block("body: (() => {", "})(),"):
        builder.add_line("const formData = new FormData();")
        
        # Add form parameters
        for param in form_params:
            if param.is_optional:
                builder.add_line(f"if ({param.name} !== undefined) {{")
                builder.indent()
                builder.add_line(f"formData.append('{param.name}', String({param.name}));")
                builder.dedent()
                builder.add_line("}")
            else:
                builder.add_line(f"formData.append('{param.name}', String({param.name}));")
        
        # Add file parameters
        for param in file_params:
            if param.is_optional:
                builder.add_line(f"if ({param.name} !== undefined) {{")
                builder.indent()
                builder.add_line(f"formData.append('{param.name}', {param.name});")
                builder.dedent()
                builder.add_line("}")
            else:
                builder.add_line(f"formData.append('{param.name}', {param.name});")
        
        # Add JSON body parameters as JSON strings in FormData
        for param in body_params:
            builder.add_line(f"formData.append('{param.name}', JSON.stringify({param.name}));")
        
        builder.add_line("return formData;")


# === PARAMETER CLASSIFICATION HELPERS === #

def _get_client_parameters(route: RouteNode) -> List[Field]:
    """Get parameters that should appear in function signature."""
    client_types = {ParameterType.PATH, ParameterType.QUERY, ParameterType.BODY, 
                   ParameterType.FORM, ParameterType.FILE}
    
    return [param for param in route.parameters 
            if param.constraints and param.constraints.parameter_type in client_types]


def _get_client_parameters_for_method(route: RouteNode, method: str) -> List[Field]:
    """Get parameters appropriate for specific HTTP method."""
    all_params = _get_client_parameters(route)
    
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


def _get_parameters_by_type(route: RouteNode, param_type: ParameterType) -> List[Field]:
    """Get all parameters of a specific type."""
    return [param for param in route.parameters 
            if param.constraints and param.constraints.parameter_type == param_type]


def _get_parameters_by_type_for_method(route: RouteNode, param_type: ParameterType, method: str) -> List[Field]:
    """Get parameters of specific type that are appropriate for the HTTP method."""
    method_params = _get_client_parameters_for_method(route, method)
    return [param for param in method_params 
            if param.constraints and param.constraints.parameter_type == param_type]


# === TYPE CONVERSION (Reuse from interface generator) === #

def _convert_annotation_to_typescript(annotation: FieldAnnotation, is_top_level: bool = False) -> str:
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


# === TESTING HELPERS === #

def test_v2_fetch_wrapper_generator():
    """Test V2 fetch wrapper generator with various RouteNode scenarios."""
    from fluidkit.core.schema import RouteNode, Field, FieldAnnotation, FieldConstraints, ModuleLocation, BaseType, ParameterType, SecurityRequirement
    
    location = ModuleLocation(module_path="test.routes", file_path="/test/routes.py")
    
    # === TEST 1: Single Method Route ===
    print("=== TEST 1: Single Method Route ===")
    get_user_route = RouteNode(
        name="getUserById",
        methods=["GET"],
        path="/users/{user_id}",
        parameters=[
            Field(
                name="user_id", 
                annotation=FieldAnnotation(base_type=BaseType.NUMBER), 
                constraints=FieldConstraints(parameter_type=ParameterType.PATH),
                description="User identifier"
            ),
            Field(
                name="include_profile", 
                annotation=FieldAnnotation(base_type=BaseType.BOOLEAN), 
                constraints=FieldConstraints(parameter_type=ParameterType.QUERY),
                default=False,
                description="Include user profile"
            )
        ],
        location=location,
        return_type=FieldAnnotation(custom_type="User"),
        docstring="Get user by ID"
    )
    
    result = generate_fetch_wrapper(get_user_route)
    print(result)
    print("\n" + "="*50 + "\n")
    
    # === TEST 2: Multi-Method Route ===
    print("=== TEST 2: Multi-Method Route ===")
    users_route = RouteNode(
        name="users",
        methods=["GET", "POST"],
        path="/users",
        parameters=[
            Field(
                name="limit", 
                annotation=FieldAnnotation(base_type=BaseType.NUMBER), 
                constraints=FieldConstraints(parameter_type=ParameterType.QUERY),
                default=10,
                description="Maximum number of results"
            ),
            Field(
                name="user", 
                annotation=FieldAnnotation(custom_type="User"), 
                constraints=FieldConstraints(parameter_type=ParameterType.BODY),
                description="User data for creation"
            )
        ],
        location=location,
        return_type=FieldAnnotation(custom_type="User"),
        docstring="Users endpoint with multiple operations"
    )
    
    result = generate_fetch_wrapper(users_route)
    print(result)
    print("\n" + "="*50 + "\n")
    
    # === TEST 3: Route with Security Requirements ===
    print("=== TEST 3: Route with Security Requirements ===")
    admin_route = RouteNode(
        name="getAdminData",
        methods=["GET"],
        path="/admin/data",
        parameters=[],
        location=location,
        security_requirements=[
            SecurityRequirement(
                scheme_name="bearer_auth",
                scheme_type="http",
                description="Bearer token authentication"
            ),
            SecurityRequirement(
                scheme_name="api_key",
                scheme_type="apiKey",
                location="header",
                parameter_name="X-API-Key"
            )
        ],
        docstring="Get admin data"
    )
    
    result = generate_fetch_wrapper(admin_route)
    print(result)
    print("\n" + "="*50 + "\n")
    
    # === TEST 4: Route with Custom FluidKit Names ===
    print("=== TEST 4: Custom FluidKit Names ===")
    result = generate_fetch_wrapper(
        get_user_route,
        api_result_type="CustomApiResult",
        get_base_url_fn="customGetBaseUrl",
        handle_response_fn="customHandleResponse"
    )
    print(result)


if __name__ == "__main__":
    test_v2_fetch_wrapper_generator()
