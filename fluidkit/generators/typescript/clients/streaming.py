"""
Streaming API client generation for all streaming types.

Generates TypeScript client functions for streaming endpoints including:
- SERVER-SENT EVENTS (EventSource API)
- JSON/DATA STREAMING (ReadableStream + JSON parsing)  
- FILE DOWNLOADS (fetch + blob/arrayBuffer)
- TEXT STREAMING (ReadableStream + TextDecoder)
"""

from typing import List

from fluidkit.core.constants import FluidKitRuntime
from fluidkit.core.schema import RouteNode, StreamingClientType
from .utils import (
    wrap_jsdoc,
    CodeBuilder,
    generate_method_signature,
    generate_url_building_lines,
    generate_function_signature,
    sort_parameters_for_signature,
    generate_sync_method_signature,
    get_client_parameters_for_method,
    generate_sync_function_signature,
)


def generate_streaming_wrapper(
    route: RouteNode,
    api_result_type: str = FluidKitRuntime.API_RESULT_TYPE,
    get_base_url_fn: str = FluidKitRuntime.GET_BASE_URL_FN,
    handle_response_fn: str = FluidKitRuntime.HANDLE_RESPONSE_FN
) -> tuple[str, List[str]]:
    """
    Generate TypeScript streaming client for any streaming endpoint.
    
    Routes to appropriate streaming generator based on StreamingClientType.
    
    Args:
        route: RouteNode with streaming_client_type set
        api_result_type: Name of the ApiResult type from FluidKit runtime
        get_base_url_fn: Name of the getBaseUrl function
        handle_response_fn: Name of the handleResponse function
        
    Returns:
        Tuple of (generated_code, used_runtime_types)
    """
    
    if not route.is_streaming:
        raise ValueError(f"Route {route.name} is not a streaming endpoint")
    
    # Route to appropriate streaming generator
    if route.streaming_client_type == StreamingClientType.EVENT_SOURCE:
        return generate_sse_wrapper(route, get_base_url_fn)
    elif route.streaming_client_type == StreamingClientType.READABLE_STREAM:
        return generate_readable_stream_wrapper(route, get_base_url_fn, handle_response_fn)
    elif route.streaming_client_type == StreamingClientType.FILE_DOWNLOAD:
        return generate_file_download_wrapper(route, get_base_url_fn, handle_response_fn)
    elif route.streaming_client_type == StreamingClientType.TEXT_STREAM:
        return generate_text_stream_wrapper(route, get_base_url_fn, handle_response_fn)
    else:
        raise ValueError(f"Unknown streaming client type: {route.streaming_client_type}")


# === SERVER-SENT EVENTS (EventSource API) === #

def generate_sse_wrapper(route: RouteNode, get_base_url_fn: str) -> tuple[str, List[str]]:
    """
    Generate Server-Sent Events client using EventSource API.
    
    Implements the callback pattern:
    streamEvents(params..., callbacks: SSECallbacks, options?: SSERequestInit): SSEConnection
    
    Returns:
        Tuple of (generated_code, used_runtime_types)
    """
    if route.is_single_method:
        return _generate_sse_single_method_wrapper(route, get_base_url_fn)
    else:
        return _generate_sse_multi_method_wrapper(route, get_base_url_fn)


def _generate_sse_single_method_wrapper(route: RouteNode, get_base_url_fn: str) -> tuple[str, List[str]]:
    """Generate single SSE function."""
    builder = CodeBuilder()
    
    method = route.methods[0]
    
    # Generate JSDoc
    jsdoc = _generate_sse_jsdoc(route, method)
    if jsdoc:
        builder.add_lines(jsdoc.split('\n'))
    
    # Generate SYNC function signature (no async)
    additional_params = [
        "callbacks: SSECallbacks",
        "options?: SSERequestInit"
    ]
    signature = generate_sync_function_signature(route, method, "SSEConnection", additional_params)
    
    # Generate function body
    with builder.add_block(signature, "};"):
        _generate_sse_function_body(builder, route, method, get_base_url_fn)
    
    # Return code and used runtime types
    used_types = ["SSECallbacks", "SSEConnection", "SSERequestInit", get_base_url_fn]
    return builder.get_code(), used_types


def _generate_sse_multi_method_wrapper(route: RouteNode, get_base_url_fn: str) -> tuple[str, List[str]]:
    """Generate SSE object with method properties."""
    builder = CodeBuilder()
    
    # Generate object JSDoc
    jsdoc = _generate_sse_object_jsdoc(route)
    if jsdoc:
        builder.add_lines(jsdoc.split('\n'))
    
    # Generate object with methods
    with builder.add_block(f"export const {route.name} = {{", "};"):
        for i, method in enumerate(route.methods):
            if i > 0:
                builder.add_line()
            
            # Method JSDoc
            method_jsdoc = _generate_sse_method_jsdoc(route, method)
            if method_jsdoc:
                builder.add_lines(method_jsdoc.split('\n'))
            
            # Method signature (SYNC, no async)
            method_name = method.lower()
            additional_params = [
                "callbacks: SSECallbacks",
                "options?: SSERequestInit"
            ]
            method_signature = generate_sync_method_signature(route, method, "SSEConnection", additional_params)
            
            closing = "}," if i < len(route.methods) - 1 else "}"
            
            with builder.add_block(f"{method_name}: {method_signature}", closing):
                _generate_sse_function_body(builder, route, method, get_base_url_fn)
    
    # Return code and used runtime types
    used_types = ["SSECallbacks", "SSEConnection", "SSERequestInit", get_base_url_fn]
    return builder.get_code(), used_types


def _generate_sse_function_body(builder: CodeBuilder, route: RouteNode, method: str, get_base_url_fn: str):
    """Generate SSE function body using EventSource API."""
    
    # URL building (only path and query params for GET-like SSE)
    generate_url_building_lines(builder, route, get_base_url_fn, method)
    
    # EventSource creation and setup
    builder.add_line()
    builder.add_line("const eventSource = new EventSource(url, {")
    builder.indent()
    builder.add_line("withCredentials: options?.withCredentials,")
    builder.add_line("...options")
    builder.dedent()
    builder.add_line("});")
    
    builder.add_line()
    
    # Attach callbacks
    builder.add_line("if (callbacks.onOpen) {")
    builder.indent()
    builder.add_line("eventSource.addEventListener('open', callbacks.onOpen);")
    builder.dedent()
    builder.add_line("}")
    
    builder.add_line()
    builder.add_line("if (callbacks.onMessage) {")
    builder.indent()
    builder.add_line("eventSource.addEventListener('message', callbacks.onMessage);")
    builder.dedent()
    builder.add_line("}")
    
    builder.add_line()
    builder.add_line("if (callbacks.onError) {")
    builder.indent()
    builder.add_line("eventSource.addEventListener('error', callbacks.onError);")
    builder.dedent()
    builder.add_line("}")
    
    builder.add_line()
    builder.add_line("if (callbacks.onClose) {")
    builder.indent()
    builder.add_line("eventSource.addEventListener('close', callbacks.onClose);")
    builder.dedent()
    builder.add_line("}")
    
    # Return connection object
    builder.add_line()
    with builder.add_block("return {", "};"):
        builder.add_line("close: () => eventSource.close(),")
        builder.add_line("readyState: eventSource.readyState,")
        builder.add_line("url: eventSource.url,")
        builder.add_line("addEventListener: eventSource.addEventListener.bind(eventSource),")
        builder.add_line("removeEventListener: eventSource.removeEventListener.bind(eventSource)")


# === JSON/DATA STREAMING (ReadableStream) === #

def generate_readable_stream_wrapper(route: RouteNode, get_base_url_fn: str, handle_response_fn: str) -> tuple[str, List[str]]:
    """
    Generate ReadableStream client for JSON/data streaming.
    
    Implements pattern:
    streamData(params..., callbacks: StreamingCallbacks<T>, options?: RequestInit): Promise<void>
    
    Returns:
        Tuple of (generated_code, used_runtime_types)
    """
    if route.is_single_method:
        return _generate_readable_stream_single_method_wrapper(route, get_base_url_fn, handle_response_fn)
    else:
        return _generate_readable_stream_multi_method_wrapper(route, get_base_url_fn, handle_response_fn)


def _generate_readable_stream_single_method_wrapper(route: RouteNode, get_base_url_fn: str, handle_response_fn: str) -> tuple[str, List[str]]:
    """Generate single ReadableStream function."""
    builder = CodeBuilder()
    
    method = route.methods[0]
    
    # Generate JSDoc
    jsdoc = _generate_streaming_jsdoc(route, method, "JSON/data streaming")
    if jsdoc:
        builder.add_lines(jsdoc.split('\n'))
    
    # Generate function signature
    additional_params = [
        "callbacks: StreamingCallbacks<any>",
        "options?: RequestInit"
    ]
    signature = generate_function_signature(route, method, "Promise<void>", additional_params)
    
    # Generate function body
    with builder.add_block(signature, "};"):
        _generate_readable_stream_function_body(builder, route, method, get_base_url_fn, handle_response_fn)
    
    # Return code and used runtime types  
    used_types = ["StreamingCallbacks", get_base_url_fn]
    return builder.get_code(), used_types


def _generate_readable_stream_multi_method_wrapper(route: RouteNode, get_base_url_fn: str, handle_response_fn: str) -> tuple[str, List[str]]:
    """Generate ReadableStream object with method properties."""
    builder = CodeBuilder()
    
    # Generate object JSDoc
    jsdoc = _generate_streaming_object_jsdoc(route, "JSON/data streaming")
    if jsdoc:
        builder.add_lines(jsdoc.split('\n'))
    
    # Generate object with methods
    with builder.add_block(f"export const {route.name} = {{", "};"):
        for i, method in enumerate(route.methods):
            if i > 0:
                builder.add_line()
            
            # Method JSDoc
            method_jsdoc = _generate_streaming_method_jsdoc(route, method, "JSON/data streaming")
            if method_jsdoc:
                builder.add_lines(method_jsdoc.split('\n'))
            
            # Method signature
            method_name = method.lower()
            additional_params = [
                "callbacks: StreamingCallbacks<any>",
                "options?: RequestInit"
            ]
            method_signature = generate_method_signature(route, method, "Promise<void>", additional_params)
            
            closing = "}," if i < len(route.methods) - 1 else "}"
            
            with builder.add_block(f"{method_name}: {method_signature}", closing):
                _generate_readable_stream_function_body(builder, route, method, get_base_url_fn, handle_response_fn)
    
    # Return code and used runtime types
    used_types = ["StreamingCallbacks", get_base_url_fn]
    return builder.get_code(), used_types


def _generate_readable_stream_function_body(builder: CodeBuilder, route: RouteNode, method: str, get_base_url_fn: str, handle_response_fn: str):
    """Generate ReadableStream function body with proper brace management."""
    
    # URL building
    generate_url_building_lines(builder, route, get_base_url_fn, method)
    
    # Request options
    builder.add_line()
    with builder.add_block("const requestOptions: RequestInit = {", "};"):
        builder.add_line(f"method: '{method.upper()}',")
        builder.add_line("headers: options?.headers,")
        builder.add_line("...options")
    
    # Try-catch with proper block management
    builder.add_line()
    with builder.add_block("try {", "}"):
        builder.add_line("const response = await fetch(url, requestOptions);")
        builder.add_line()
        
        with builder.add_block("if (!response.ok) {", "}"):
            builder.add_line("callbacks.onError?.(new Error(`HTTP ${response.status}: ${response.statusText}`));")
            builder.add_line("return;")
        
        builder.add_line()
        builder.add_line("const reader = response.body?.getReader();")
        
        with builder.add_block("if (!reader) {", "}"):
            builder.add_line("callbacks.onError?.(new Error('Response body is not readable'));")
            builder.add_line("return;")
        
        builder.add_line()
        with builder.add_block("while (true) {", "}"):
            builder.add_line("const { done, value } = await reader.read();")
            builder.add_line("if (done) break;")
            builder.add_line()
            
            with builder.add_block("try {", "}"):
                builder.add_line("const chunk = JSON.parse(new TextDecoder().decode(value));")
                builder.add_line("callbacks.onChunk?.(chunk);")
            
            with builder.add_block("catch (parseError) {", "}"):
                builder.add_line("callbacks.onError?.(parseError instanceof Error ? parseError : new Error('JSON parse error'));")
                builder.add_line("break;")
        
        builder.add_line()
        builder.add_line("callbacks.onComplete?.();")
    
    with builder.add_block("catch (error) {", "}"):
        builder.add_line("callbacks.onError?.(error instanceof Error ? error : new Error('Streaming error'));")


# === FILE DOWNLOADS === #

def generate_file_download_wrapper(route: RouteNode, get_base_url_fn: str, handle_response_fn: str) -> tuple[str, List[str]]:
    """
    Generate file download client.
    
    Implements pattern:
    downloadFile(params..., options?: RequestInit): Promise<Blob>
    
    Returns:
        Tuple of (generated_code, used_runtime_types)
    """
    if route.is_single_method:
        return _generate_file_download_single_method_wrapper(route, get_base_url_fn)
    else:
        return _generate_file_download_multi_method_wrapper(route, get_base_url_fn)


def _generate_file_download_single_method_wrapper(route: RouteNode, get_base_url_fn: str) -> tuple[str, List[str]]:
    """Generate single file download function."""
    builder = CodeBuilder()
    
    method = route.methods[0]
    
    # Generate JSDoc
    jsdoc = _generate_streaming_jsdoc(route, method, "File download")
    if jsdoc:
        builder.add_lines(jsdoc.split('\n'))
    
    # Generate function signature
    additional_params = ["options?: RequestInit"]
    signature = generate_function_signature(route, method, "Promise<Blob>", additional_params)
    
    # Generate function body
    with builder.add_block(signature, "};"):
        _generate_file_download_function_body(builder, route, method, get_base_url_fn)
    
    # Return code and used runtime types (file downloads only use basic fetch, no special runtime types)
    used_types = [get_base_url_fn]
    return builder.get_code(), used_types
    builder = CodeBuilder()
    
    method = route.methods[0]
    
    # Generate JSDoc
    jsdoc = _generate_streaming_jsdoc(route, method, "File download")
    if jsdoc:
        builder.add_lines(jsdoc.split('\n'))
    
    # Generate function signature
    additional_params = ["options?: RequestInit"]
    signature = generate_function_signature(route, method, "Promise<Blob>", additional_params)
    
    # Generate function body
    with builder.add_block(signature, "};"):
        _generate_file_download_function_body(builder, route, method, get_base_url_fn)
    
    return builder.get_code()


def _generate_file_download_multi_method_wrapper(route: RouteNode, get_base_url_fn: str) -> tuple[str, List[str]]:
    """Generate file download object with method properties."""
    builder = CodeBuilder()
    
    # Generate object JSDoc
    jsdoc = _generate_streaming_object_jsdoc(route, "File download")
    if jsdoc:
        builder.add_lines(jsdoc.split('\n'))
    
    # Generate object with methods
    with builder.add_block(f"export const {route.name} = {{", "};"):
        for i, method in enumerate(route.methods):
            if i > 0:
                builder.add_line()
            
            # Method JSDoc
            method_jsdoc = _generate_streaming_method_jsdoc(route, method, "File download")
            if method_jsdoc:
                builder.add_lines(method_jsdoc.split('\n'))
            
            # Method signature
            method_name = method.lower()
            additional_params = ["options?: RequestInit"]
            method_signature = generate_method_signature(route, method, "Promise<Blob>", additional_params)
            
            closing = "}," if i < len(route.methods) - 1 else "}"
            
            with builder.add_block(f"{method_name}: {method_signature}", closing):
                _generate_file_download_function_body(builder, route, method, get_base_url_fn)
    
    # Return code and used runtime types
    used_types = [get_base_url_fn]
    return builder.get_code(), used_types


def _generate_file_download_function_body(builder: CodeBuilder, route: RouteNode, method: str, get_base_url_fn: str):
    """Generate file download function body."""
    
    # URL building
    generate_url_building_lines(builder, route, get_base_url_fn, method)
    
    # Request options
    builder.add_line()
    with builder.add_block("const requestOptions: RequestInit = {", "};"):
        builder.add_line(f"method: '{method.upper()}',")
        builder.add_line("headers: options?.headers,")
        builder.add_line("...options")
    
    # Fetch and return blob
    builder.add_line()
    builder.add_line("const response = await fetch(url, requestOptions);")
    builder.add_line()
    builder.add_line("if (!response.ok) {")
    builder.indent()
    builder.add_line("throw new Error(`HTTP ${response.status}: ${response.statusText}`);")
    builder.dedent()
    builder.add_line("}")
    builder.add_line()
    builder.add_line("return response.blob();")


# === TEXT STREAMING === #

def generate_text_stream_wrapper(route: RouteNode, get_base_url_fn: str, handle_response_fn: str) -> tuple[str, List[str]]:
    """
    Generate text streaming client.
    
    Implements pattern:
    streamText(params..., callbacks: TextStreamCallbacks, options?: RequestInit): Promise<void>
    
    Returns:
        Tuple of (generated_code, used_runtime_types)
    """
    if route.is_single_method:
        return _generate_text_stream_single_method_wrapper(route, get_base_url_fn, handle_response_fn)
    else:
        return _generate_text_stream_multi_method_wrapper(route, get_base_url_fn, handle_response_fn)


def _generate_text_stream_single_method_wrapper(route: RouteNode, get_base_url_fn: str, handle_response_fn: str) -> tuple[str, List[str]]:
    """Generate single text streaming function."""
    builder = CodeBuilder()
    
    method = route.methods[0]
    
    # Generate JSDoc
    jsdoc = _generate_streaming_jsdoc(route, method, "Text streaming")
    if jsdoc:
        builder.add_lines(jsdoc.split('\n'))
    
    # Generate function signature
    additional_params = [
        "callbacks: TextStreamCallbacks",
        "options?: RequestInit"
    ]
    signature = generate_function_signature(route, method, "Promise<void>", additional_params)
    
    # Generate function body
    with builder.add_block(signature, "};"):
        _generate_text_stream_function_body(builder, route, method, get_base_url_fn, handle_response_fn)
    
    # Return code and used runtime types
    used_types = ["TextStreamCallbacks", get_base_url_fn]
    return builder.get_code(), used_types


def _generate_text_stream_multi_method_wrapper(route: RouteNode, get_base_url_fn: str, handle_response_fn: str) -> tuple[str, List[str]]:
    """Generate text streaming object with method properties."""
    builder = CodeBuilder()
    
    # Generate object JSDoc
    jsdoc = _generate_streaming_object_jsdoc(route, "Text streaming")
    if jsdoc:
        builder.add_lines(jsdoc.split('\n'))
    
    # Generate object with methods
    with builder.add_block(f"export const {route.name} = {{", "};"):
        for i, method in enumerate(route.methods):
            if i > 0:
                builder.add_line()
            
            # Method JSDoc
            method_jsdoc = _generate_streaming_method_jsdoc(route, method, "Text streaming")
            if method_jsdoc:
                builder.add_lines(method_jsdoc.split('\n'))
            
            # Method signature
            method_name = method.lower()
            additional_params = [
                "callbacks: TextStreamCallbacks",
                "options?: RequestInit"
            ]
            method_signature = generate_method_signature(route, method, "Promise<void>", additional_params)
            
            closing = "}," if i < len(route.methods) - 1 else "}"
            
            with builder.add_block(f"{method_name}: {method_signature}", closing):
                _generate_text_stream_function_body(builder, route, method, get_base_url_fn, handle_response_fn)
    
    # Return code and used runtime types
    used_types = ["TextStreamCallbacks", get_base_url_fn]
    return builder.get_code(), used_types


def _generate_text_stream_function_body(builder: CodeBuilder, route: RouteNode, method: str, get_base_url_fn: str, handle_response_fn: str):
    """Generate text streaming function body."""
    
    # URL building
    generate_url_building_lines(builder, route, get_base_url_fn, method)
    
    # Request options
    builder.add_line()
    with builder.add_block("const requestOptions: RequestInit = {", "};"):
        builder.add_line(f"method: '{method.upper()}',")
        builder.add_line("headers: options?.headers,")
        builder.add_line("...options")
    
    # Fetch and stream processing
    builder.add_line()
    with builder.add_block("try {", "}"):
        builder.add_line("const response = await fetch(url, requestOptions);")
        builder.add_line()
        builder.add_line("if (!response.ok) {")
        builder.indent()
        builder.add_line("callbacks.onError?.(new Error(`HTTP ${response.status}: ${response.statusText}`));")
        builder.add_line("return;")
        builder.dedent()
        builder.add_line("}")
        
        builder.add_line()
        builder.add_line("const reader = response.body?.getReader();")
        builder.add_line("const decoder = new TextDecoder();")
        builder.add_line()
        builder.add_line("if (!reader) {")
        builder.indent()
        builder.add_line("callbacks.onError?.(new Error('Response body is not readable'));")
        builder.add_line("return;")
        builder.dedent()
        builder.add_line("}")
        
        builder.add_line()
        with builder.add_block("while (true) {", "}"):
            builder.add_line("const { done, value } = await reader.read();")
            builder.add_line("if (done) break;")
            builder.add_line()
            builder.add_line("const text = decoder.decode(value);")
            builder.add_line("callbacks.onChunk?.(text);")
        
        builder.add_line()
        builder.add_line("callbacks.onComplete?.();")
    
    with builder.add_block("catch (error) {", "}"):
        builder.add_line("callbacks.onError?.(error instanceof Error ? error : new Error('Text streaming error'));")


# === JSDOC HELPERS === #

def _generate_sse_jsdoc(route: RouteNode, method: str) -> str:
    """Generate JSDoc for SSE functions."""
    parts = []
    
    # Add description
    if route.docstring:
        parts.append(f"{route.docstring} (Server-Sent Events)")
    else:
        parts.append(f"{method.upper()} {route.path} - Server-Sent Events stream")
    
    # Add parameters
    client_params = get_client_parameters_for_method(route, method)
    sorted_params = sort_parameters_for_signature(client_params)
    
    if sorted_params:
        parts.append("")
        for param in sorted_params:
            param_line = f"@param {param.name}"
            if param.description:
                param_line += f" - {param.description}"
            parts.append(param_line)
    
    parts.append("@param callbacks - SSE event handlers")
    parts.append("@param options - EventSource options")
    
    # Add streaming info
    if route.streaming_media_type:
        parts.append("")
        parts.append(f"**Stream Type:** {route.streaming_media_type}")
    
    return wrap_jsdoc(parts)


def _generate_sse_object_jsdoc(route: RouteNode) -> str:
    """Generate JSDoc for SSE object."""
    parts = []
    
    if route.docstring:
        parts.append(f"{route.docstring} (Server-Sent Events)")
    else:
        methods_str = ", ".join(route.methods)
        parts.append(f"{route.path} - {methods_str} Server-Sent Events operations")
    
    if route.streaming_media_type:
        parts.append("")
        parts.append(f"**Stream Type:** {route.streaming_media_type}")
    
    return wrap_jsdoc(parts)


def _generate_sse_method_jsdoc(route: RouteNode, method: str) -> str:
    """Generate JSDoc for SSE method."""
    parts = [f"{method.upper()} Server-Sent Events operation"]
    
    client_params = get_client_parameters_for_method(route, method)
    sorted_params = sort_parameters_for_signature(client_params)
    
    if sorted_params:
        parts.append("")
        for param in sorted_params:
            param_line = f"@param {param.name}"
            if param.description:
                param_line += f" - {param.description}"
            parts.append(param_line)
    
    parts.append("@param callbacks - SSE event handlers")
    parts.append("@param options - EventSource options")
    
    return wrap_jsdoc(parts)


def _generate_streaming_jsdoc(route: RouteNode, method: str, stream_type: str) -> str:
    """Generate JSDoc for generic streaming functions."""
    parts = []
    
    # Add description
    if route.docstring:
        parts.append(f"{route.docstring} ({stream_type})")
    else:
        parts.append(f"{method.upper()} {route.path} - {stream_type}")
    
    # Add parameters
    client_params = get_client_parameters_for_method(route, method)
    sorted_params = sort_parameters_for_signature(client_params)
    
    if sorted_params:
        parts.append("")
        for param in sorted_params:
            param_line = f"@param {param.name}"
            if param.description:
                param_line += f" - {param.description}"
            parts.append(param_line)
    
    parts.append("@param callbacks - Streaming event handlers")
    parts.append("@param options - Request options")
    
    # Add streaming info
    if route.streaming_media_type:
        parts.append("")
        parts.append(f"**Stream Type:** {route.streaming_media_type}")
    
    return wrap_jsdoc(parts)


def _generate_streaming_object_jsdoc(route: RouteNode, stream_type: str) -> str:
    """Generate JSDoc for streaming object."""
    parts = []
    
    if route.docstring:
        parts.append(f"{route.docstring} ({stream_type})")
    else:
        methods_str = ", ".join(route.methods)
        parts.append(f"{route.path} - {methods_str} {stream_type} operations")
    
    if route.streaming_media_type:
        parts.append("")
        parts.append(f"**Stream Type:** {route.streaming_media_type}")
    
    return wrap_jsdoc(parts)


def _generate_streaming_method_jsdoc(route: RouteNode, method: str, stream_type: str) -> str:
    """Generate JSDoc for streaming method."""
    parts = [f"{method.upper()} {stream_type} operation"]
    
    client_params = get_client_parameters_for_method(route, method)
    sorted_params = sort_parameters_for_signature(client_params)
    
    if sorted_params:
        parts.append("")
        for param in sorted_params:
            param_line = f"@param {param.name}"
            if param.description:
                param_line += f" - {param.description}"
            parts.append(param_line)
    
    parts.append("@param callbacks - Streaming event handlers")
    parts.append("@param options - Request options")
    
    return wrap_jsdoc(parts)


# === TESTING HELPERS === #

def test_streaming_wrapper_generation():
    """Test streaming wrapper generation for all types."""
    from fluidkit.core.schema import RouteNode, Field, FieldAnnotation, FieldConstraints, ModuleLocation, BaseType, ParameterType, StreamingClientType
    
    location = ModuleLocation(module_path="test.routes", file_path="/test/routes.py")
    
    print("=== STREAMING WRAPPER GENERATION TESTS ===")
    
    # Test SSE endpoint
    print("\n1. Testing SSE Wrapper:")
    sse_route = RouteNode(
        name="streamEvents",
        methods=["GET"],
        path="/events/{topic}",
        parameters=[
            Field(
                name="topic",
                annotation=FieldAnnotation(base_type=BaseType.STRING),
                constraints=FieldConstraints(parameter_type=ParameterType.PATH),
                description="Event topic"
            )
        ],
        location=location,
        streaming_client_type=StreamingClientType.EVENT_SOURCE,
        streaming_media_type="text/event-stream",
        docstring="Stream real-time events"
    )
    
    result = generate_streaming_wrapper(sse_route)
    print(result[:300] + "...")
    
    # Test JSON streaming endpoint
    print("\n2. Testing JSON Streaming Wrapper:")
    json_route = RouteNode(
        name="streamData",
        methods=["GET"],
        path="/data/stream",
        parameters=[],
        location=location,
        streaming_client_type=StreamingClientType.READABLE_STREAM,
        streaming_media_type="application/x-ndjson",
        docstring="Stream JSON data"
    )
    
    result = generate_streaming_wrapper(json_route)
    print(result[:300] + "...")


if __name__ == "__main__":
    test_streaming_wrapper_generation()
