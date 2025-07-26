"""
Regular REST API fetch wrapper generation.

Generates TypeScript fetch functions from RouteNode objects for regular REST endpoints.
Handles GET, POST, PUT, DELETE and other standard HTTP methods with full parameter support.
"""

from typing import List
from fluidkit.core.constants import FluidKitRuntime
from fluidkit.core.schema import RouteNode, Field, ParameterType
from .utils import ( 
    wrap_jsdoc,
    CodeBuilder,
    generate_return_type,
    generate_function_jsdoc,
    generate_method_signature,
    generate_url_building_lines,
    generate_function_signature,
    sort_parameters_for_signature,
    get_client_parameters_for_method,
    get_parameters_by_type_for_method,
)


def generate_fetch_wrapper(
    route: RouteNode, 
    api_result_type: str = FluidKitRuntime.API_RESULT_TYPE,
    get_base_url_fn: str = FluidKitRuntime.GET_BASE_URL_FN, 
    handle_response_fn: str = FluidKitRuntime.HANDLE_RESPONSE_FN
) -> tuple[str, List[str]]:
    """
    Generate TypeScript fetch function(s) for a single RouteNode.
    
    Args:
        route: RouteNode with method(s), path, parameters, and metadata
        api_result_type: Name of the ApiResult type from FluidKit runtime
        get_base_url_fn: Name of the getBaseUrl function from FluidKit runtime
        handle_response_fn: Name of the handleResponse function from FluidKit runtime
        
    Returns:
        Tuple of (generated_code, used_runtime_types)
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
) -> tuple[str, List[str]]:
    """Generate single async arrow function for single-method routes."""
    builder = CodeBuilder()
    
    method = route.methods[0]  # Single method
    
    # Generate JSDoc header
    jsdoc = generate_function_jsdoc(route, method)
    if jsdoc:
        builder.add_lines(jsdoc.split('\n'))
    
    # Generate function signature
    return_type = generate_return_type(route, "Promise", api_result_type)
    additional_params = ["options?: RequestInit"]
    signature = generate_function_signature(route, method, return_type, additional_params)
    
    # Generate function body
    with builder.add_block(signature, "};"):
        _generate_fetch_function_body_lines(builder, route, method, get_base_url_fn, handle_response_fn)
    
    # Return code and used runtime types
    used_types = [api_result_type, get_base_url_fn, handle_response_fn]
    return builder.get_code(), used_types


def _generate_multi_method_wrapper(
    route: RouteNode, 
    api_result_type: str,
    get_base_url_fn: str, 
    handle_response_fn: str
) -> tuple[str, List[str]]:
    """Generate object with method properties for multi-method routes."""
    builder = CodeBuilder()
    
    # Generate object JSDoc header
    jsdoc = _generate_object_jsdoc(route)
    if jsdoc:
        builder.add_lines(jsdoc.split('\n'))
    
    # Generate object with methods
    with builder.add_block(f"export const {route.name} = {{", "};"):
        for i, method in enumerate(route.methods):
            # Add spacing between methods
            if i > 0:
                builder.add_line()
            
            # Generate method JSDoc
            method_jsdoc = _generate_method_jsdoc(route, method)
            if method_jsdoc:
                builder.add_lines(method_jsdoc.split('\n'))
            
            # Generate method function
            method_name = method.lower()
            return_type = generate_return_type(route, "Promise", api_result_type)
            additional_params = ["options?: RequestInit"]
            method_signature = generate_method_signature(route, method, return_type, additional_params)
            
            # Determine closing based on whether this is the last method
            closing = "}," if i < len(route.methods) - 1 else "}"
            
            with builder.add_block(f"{method_name}: {method_signature}", closing):
                _generate_fetch_function_body_lines(builder, route, method, get_base_url_fn, handle_response_fn)
    
    # Return code and used runtime types
    used_types = [api_result_type, get_base_url_fn, handle_response_fn]
    return builder.get_code(), used_types


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
    from .utils import generate_security_jsdoc
    security_docs = generate_security_jsdoc(route)
    if security_docs:
        parts.append("")
        parts.extend(security_docs)
    
    return wrap_jsdoc(parts) if parts else ""


def _generate_method_jsdoc(route: RouteNode, method: str) -> str:
    """Generate JSDoc for individual method in multi-method object."""
    parts = []
    
    # Add method description
    parts.append(f"{method.upper()} operation")
    
    # Add parameter documentation
    client_params = get_client_parameters_for_method(route, method)
    sorted_params = sort_parameters_for_signature(client_params)

    if sorted_params:
        parts.append("")
        for param in sorted_params:
            param_line = f"@param {param.name}"
            if param.description:
                param_line += f" - {param.description}"
            parts.append(param_line)
        
        parts.append("@param options - Additional fetch options")
    
    return wrap_jsdoc(parts)


def _generate_fetch_function_body_lines(
    builder: CodeBuilder, 
    route: RouteNode, 
    method: str, 
    get_base_url_fn: str, 
    handle_response_fn: str
):
    """Generate fetch function body implementation using CodeBuilder."""
    
    # URL building
    generate_url_building_lines(builder, route, get_base_url_fn, method)
    
    # Request options building  
    _generate_request_options_lines(builder, route, method)
    
    # Fetch call and response handling
    builder.add_line()
    builder.add_line("const response = await fetch(url, requestOptions);")
    builder.add_line(f"return {handle_response_fn}(response);")


def _generate_request_options_lines(builder: CodeBuilder, route: RouteNode, method: str):
    """Generate request options with method, headers, and body."""
    
    # Determine if we have a request body
    body_params = get_parameters_by_type_for_method(route, ParameterType.BODY, method)
    form_params = get_parameters_by_type_for_method(route, ParameterType.FORM, method)
    file_params = get_parameters_by_type_for_method(route, ParameterType.FILE, method)
    
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


# === TESTING HELPERS === #

def test_fetch_wrapper_generation():
    """Test fetch wrapper generator with various RouteNode scenarios."""
    from fluidkit.core.schema import RouteNode, Field, FieldAnnotation, FieldConstraints, ModuleLocation, BaseType, ParameterType
    
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


if __name__ == "__main__":
    test_fetch_wrapper_generation()
