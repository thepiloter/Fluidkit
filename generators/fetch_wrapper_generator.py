from typing import List, Dict, Set
from core.nodes import *

def generate_fetch_wrapper(route: RouteNode) -> str:
    """
    Generate TypeScript fetch function for a single route.
    
    Args:
        route: RouteNode with method, path, parameters, and metadata
        
    Returns:
        Complete TypeScript fetch function with JSDoc as string
    """
    lines = []
    
    # Generate JSDoc header with authentication requirements
    header = _generate_fetch_function_header(route)
    if header:
        lines.append(header)
    
    # Generate function signature
    signature = _generate_fetch_function_signature(route)
    lines.append(signature)
    
    # Generate function body
    body_lines = _generate_fetch_function_body(route)
    lines.extend(body_lines)
    
    lines.append("}")
    
    return "\n".join(lines)


def _generate_fetch_function_header(route: RouteNode) -> str:
    """Generate JSDoc header with parameter docs and auth requirements."""
    lines = []
    lines.append("/**")
    
    # Add route docstring if available
    if route.docstring:
        lines.append(f" * {route.docstring}")
        lines.append(" *")
    
    # Document client parameters (PATH, QUERY, BODY, FORM, FILE)
    client_params = _get_client_parameters(route)
    if client_params:
        for param in client_params:
            param_line = f" * @param {param.name}"
            if param.description:
                param_line += f" - {param.description}"
            # REMOVED: Generic fallback descriptions - keep clean if no description
            lines.append(param_line)
        
        lines.append(" * @param options - Additional fetch options")
    
    # Document authentication requirements (HEADER, COOKIE, SECURITY)
    auth_params = _get_auth_parameters(route)
    if auth_params:
        lines.append(" *")
        lines.append(" * **Server Requirements:**")  # FIX: Use exactly two asterisks
        for param in auth_params:
            auth_type = param.constraints.parameter_type.value.title()
            requirement = "required" if param.is_required else "auto"
            auth_line = f" * - {auth_type}: {param.name} ({requirement})"
            if param.description:
                auth_line += f" - {param.description}"
            lines.append(auth_line)
    
    lines.append(" */")
    return "\n".join(lines)


def _generate_fetch_function_signature(route: RouteNode) -> str:
    """Generate function signature maintaining FastAPI parameter order."""
    client_params = _get_client_parameters(route)
    
    # Build parameter list maintaining FastAPI order
    param_parts = []
    for param in client_params:
        typescript_type = _convert_annotation_to_typescript(param.annotation, is_top_level=True)
        param_name = param.name
        if param.is_optional:
            param_name += "?"
        param_parts.append(f"{param_name}: {typescript_type}")
    
    # Add standard options parameter
    param_parts.append("options?: RequestInit")
    
    params_str = ", ".join(param_parts)
    
    # Generate return type
    return_type = "Promise<ApiResult<any>>"
    if route.return_type:
        inner_type = _convert_annotation_to_typescript(route.return_type, is_top_level=True)
        return_type = f"Promise<ApiResult<{inner_type}>>"
    
    return f"export async function {route.name}({params_str}): {return_type} {{"


def _generate_fetch_function_body(route: RouteNode) -> List[str]:
    """Generate complete function body with URL building and fetch logic."""
    lines = []
    
    # URL building
    url_lines = _generate_url_building(route)
    lines.extend(url_lines)
    
    # Request options building
    options_lines = _generate_request_options_building(route)
    lines.extend(options_lines)
    
    # Fetch call and response handling
    lines.append("")
    lines.append("  const response = await fetch(url, requestOptions);")
    lines.append("  return handleResponse(response);")
    
    return lines


def _generate_url_building(route: RouteNode) -> List[str]:
    """Generate URL construction with path and query parameters."""
    lines = []
    
    # Start with base URL and path
    path = route.path
    
    # Handle path parameters - replace {param} with ${param}
    path_params = _get_parameters_by_type(route, ParameterType.PATH)
    if path_params:
        for param in path_params:
            path = path.replace(f"{{{param.name}}}", f"${{{param.name}}}")
        lines.append(f"  let url = `${{getBaseUrl()}}{path}`;")
    else:
        lines.append(f"  let url = `${{getBaseUrl()}}{path}`;")
    
    # Handle query parameters
    query_params = _get_parameters_by_type(route, ParameterType.QUERY)
    if query_params:
        lines.append("")
        lines.append("  const searchParams = new URLSearchParams();")
        for param in query_params:
            if param.is_optional:
                lines.append(f"  if ({param.name} !== undefined) {{")
                lines.append(f"    searchParams.set('{param.name}', String({param.name}));")
                lines.append("  }")
            else:
                lines.append(f"  searchParams.set('{param.name}', String({param.name}));")
        
        lines.append("  if (searchParams.toString()) {")
        lines.append("    url += `?${searchParams.toString()}`;")
        lines.append("  }")
    
    return lines


def _generate_request_options_building(route: RouteNode) -> List[str]:
    """Generate request options with method, headers, and body."""
    lines = []
    lines.append("")
    
    # Determine if we have a request body
    body_params = _get_body_parameters(route)
    form_params = _get_parameters_by_type(route, ParameterType.FORM)
    file_params = _get_parameters_by_type(route, ParameterType.FILE)
    
    has_json_body = len(body_params) > 0
    has_form_data = len(form_params) > 0 or len(file_params) > 0
    
    # Build request options
    lines.append("  const requestOptions: RequestInit = {")
    lines.append(f"    method: '{route.method}',")
    
    # Headers
    if has_json_body and not has_form_data:
        lines.append("    headers: {")
        lines.append("      'Content-Type': 'application/json',")
        lines.append("      ...options?.headers")
        lines.append("    },")
    elif not has_form_data:
        lines.append("    headers: options?.headers,")
    else:
        # FormData sets its own Content-Type
        lines.append("    headers: options?.headers,")
    
    # Body handling
    if has_json_body and not has_form_data:
        body_building = _generate_json_body_building(body_params)
        lines.extend(body_building)
    elif has_form_data:
        form_building = _generate_form_data_building(form_params, file_params, body_params)
        lines.extend(form_building)
    
    # Merge with user options (excluding body and headers which we handle)
    lines.append("    ...options")
    lines.append("  };")
    
    return lines


def _generate_json_body_building(body_params: List[Field]) -> List[str]:
    """Generate JSON body building for multiple body parameters."""
    if not body_params:
        return []
    
    lines = []
    
    if len(body_params) == 1:
        # Single body parameter
        param = body_params[0]
        lines.append(f"    body: JSON.stringify({param.name}),")
    else:
        # Multiple body parameters - auto-merge following FastAPI/OpenAPI spec
        lines.append("    body: JSON.stringify({")
        for param in body_params:
            lines.append(f"      {param.name},")
        lines.append("    }),")
    
    return lines


def _generate_form_data_building(form_params: List[Field], file_params: List[Field], body_params: List[Field]) -> List[str]:
    """Generate FormData building for form and file parameters."""
    lines = []
    lines.append("    body: (() => {")
    lines.append("      const formData = new FormData();")
    
    # Add form parameters
    for param in form_params:
        if param.is_optional:
            lines.append(f"      if ({param.name} !== undefined) {{")
            lines.append(f"        formData.append('{param.name}', String({param.name}));")
            lines.append("      }")
        else:
            lines.append(f"      formData.append('{param.name}', String({param.name}));")
    
    # Add file parameters
    for param in file_params:
        if param.is_optional:
            lines.append(f"      if ({param.name} !== undefined) {{")
            lines.append(f"        formData.append('{param.name}', {param.name});")
            lines.append("      }")
        else:
            lines.append(f"      formData.append('{param.name}', {param.name});")
    
    # Add JSON body parameters as JSON strings in FormData (FastAPI pattern)
    for param in body_params:
        lines.append(f"      formData.append('{param.name}', JSON.stringify({param.name}));")
    
    lines.append("      return formData;")
    lines.append("    })(),")
    
    return lines


# === PARAMETER CLASSIFICATION HELPERS ===

def _get_client_parameters(route: RouteNode) -> List[Field]:
    """Get parameters that should appear in function signature (PATH, QUERY, BODY, FORM, FILE)."""
    client_types = {ParameterType.PATH, ParameterType.QUERY, ParameterType.BODY, 
                   ParameterType.FORM, ParameterType.FILE}
    
    return [param for param in route.parameters 
            if param.constraints and param.constraints.parameter_type in client_types]


def _get_auth_parameters(route: RouteNode) -> List[Field]:
    """Get parameters for auth documentation (HEADER, COOKIE, SECURITY)."""
    auth_types = {ParameterType.HEADER, ParameterType.COOKIE, ParameterType.SECURITY}
    
    return [param for param in route.parameters 
            if param.constraints and param.constraints.parameter_type in auth_types]


def _get_parameters_by_type(route: RouteNode, param_type: ParameterType) -> List[Field]:
    """Get all parameters of a specific type."""
    return [param for param in route.parameters 
            if param.constraints and param.constraints.parameter_type == param_type]


def _get_body_parameters(route: RouteNode) -> List[Field]:
    """Get all BODY parameters for request body building."""
    return _get_parameters_by_type(route, ParameterType.BODY)


# === TYPE CONVERSION (Reuse from interface generator) ===

def _convert_annotation_to_typescript(annotation: FieldAnnotation, is_top_level: bool = False) -> str:
    """Convert IR annotation to TypeScript type string (reused from interface generator)."""
    from generators.interface_generator import _convert_annotation_to_typescript as convert_type
    return convert_type(annotation, is_top_level)


# === TESTING HELPERS ===

def test_generate_fetch_wrapper():
    """Test function for fetch wrapper generation."""
    pass

if __name__ == "__main__":
    test_generate_fetch_wrapper()
