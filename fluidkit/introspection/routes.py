"""
FastAPI Route Introspection for FluidKit V2

Main entry point for converting FastAPI routes to RouteNode objects using
runtime introspection instead of AST parsing. Supports both regular REST
endpoints and streaming endpoints (SSE, JSON streaming, file downloads, etc.).
"""

import ast
import inspect
import typing
from typing import Optional, Any, Union

from fastapi.dependencies.utils import get_dependant
from fluidkit.core.utils import find_function_returns
from fluidkit.core.type_conversion import python_type_to_field_annotation
from fluidkit.introspection.security import extract_security_requirements
from fluidkit.introspection.parameters import extract_parameters_from_dependant
from fluidkit.core.schema import RouteNode, StreamingClientType, FieldAnnotation


def route_to_node(route) -> Optional[RouteNode]:
    """
    Convert FastAPI route to RouteNode using runtime introspection.
    
    Args:
        route: FastAPI route object from app.routes
        
    Returns:
        RouteNode object or None if conversion fails
    """
    try:
        endpoint_function = route.endpoint
        methods = list(route.methods)
        path = route.path
        name = endpoint_function.__name__
        docstring = endpoint_function.__doc__
        
        from fluidkit.core.utils import create_module_location_from_object
        location = create_module_location_from_object(endpoint_function, is_external=False)
        
        type_hints = typing.get_type_hints(endpoint_function)
        
        # Enhanced return type detection (checks both annotations and response_model)
        return_type = _extract_enhanced_return_type(route, endpoint_function, type_hints)
        
        dependant = get_dependant(path=path, call=endpoint_function)
        parameters = extract_parameters_from_dependant(dependant, type_hints)
        security_requirements = extract_security_requirements(dependant)
        
        # Streaming detection
        streaming_client_type, streaming_media_type, streaming_metadata = _detect_streaming_info(
            route, endpoint_function, type_hints
        )
        
        return RouteNode(
            name=name,
            path=path,
            methods=methods,
            location=location,
            docstring=docstring,
            parameters=parameters,
            return_type=return_type,
            security_requirements=security_requirements,
            streaming_client_type=streaming_client_type,
            streaming_media_type=streaming_media_type,
            streaming_metadata=streaming_metadata
        )
        
    except Exception as e:
        print(f"Warning: Failed to convert route {route.path}: {e}")
        return None


def _extract_enhanced_return_type(route, endpoint_function, type_hints) -> Optional[FieldAnnotation]:
    """
    Extract return type using multiple strategies.
    
    Checks type annotations, FastAPI response_model, and AST analysis.
    
    Args:
        route: FastAPI route object
        endpoint_function: Route endpoint function
        type_hints: Type hints from typing.get_type_hints()
        
    Returns:
        FieldAnnotation representing return type or None
    """
    
    # Strategy 1: Type hints (most reliable)
    if 'return' in type_hints:
        return python_type_to_field_annotation(type_hints['return'])
    
    # Strategy 2: FastAPI response_model
    if hasattr(route, 'response_model') and route.response_model:
        return python_type_to_field_annotation(route.response_model)
    
    # Strategy 3: AST analysis of direct return statements (if needed in future)
    # Could be implemented here if required for edge cases
    
    return None


def _detect_streaming_info(route, endpoint_function, type_hints) -> tuple[
    Optional[StreamingClientType], 
    Optional[str], 
    dict[str, Any]
]:
    """
    Detect streaming information for the endpoint.
    
    Args:
        route: FastAPI route object
        endpoint_function: Route endpoint function
        type_hints: Type hints from typing.get_type_hints()
        
    Returns:
        Tuple of (streaming_client_type, streaming_media_type, streaming_metadata)
    """
    
    # Strategy 1: Return type annotation with immediate media type extraction
    if 'return' in type_hints:
        result = _extract_streaming_info_from_type(type_hints['return'], endpoint_function)
        if result[0]:  # streaming_client_type found
            return result
    
    # Strategy 2: FastAPI response_model with immediate media type extraction
    if hasattr(route, 'response_model') and route.response_model:
        result = _extract_streaming_info_from_type(route.response_model, endpoint_function)
        if result[0]:  # streaming_client_type found
            return result
    
    # Strategy 3: Scope-aware AST analysis for edge cases
    try:
        result = _extract_streaming_info_from_ast(endpoint_function)
        if result[0]:  # streaming_client_type found
            return result
    except Exception:
        pass  # AST analysis failed - not streaming
    
    # Not a streaming endpoint
    return None, None, {}


def _extract_streaming_info_from_type(py_type: Any, endpoint_function) -> tuple[
    Optional[StreamingClientType], 
    Optional[str], 
    dict[str, Any]
]:
    """
    Extract streaming information from return type annotation.
    
    Args:
        py_type: Python type object to check
        endpoint_function: Endpoint function for targeted AST analysis
        
    Returns:
        Tuple of (streaming_client_type, streaming_media_type, streaming_metadata)
    """
    
    # Check for EventSourceResponse from sse-starlette
    try:
        from sse_starlette import EventSourceResponse
        if py_type is EventSourceResponse:
            return StreamingClientType.EVENT_SOURCE, "text/event-stream", {}
        if inspect.isclass(py_type) and issubclass(py_type, EventSourceResponse):
            return StreamingClientType.EVENT_SOURCE, "text/event-stream", {}
    except ImportError:
        pass  # sse-starlette not installed
    
    # Check for StreamingResponse - do immediate targeted AST check
    try:
        from starlette.responses import StreamingResponse
        if py_type is StreamingResponse and endpoint_function:
            return _extract_streaming_response_info(endpoint_function)
        if inspect.isclass(py_type) and issubclass(py_type, StreamingResponse) and endpoint_function:
            return _extract_streaming_response_info(endpoint_function)
    except ImportError:
        pass
    
    # Check for FastAPI StreamingResponse
    try:
        from fastapi.responses import StreamingResponse
        if py_type is StreamingResponse and endpoint_function:
            return _extract_streaming_response_info(endpoint_function)
        if inspect.isclass(py_type) and issubclass(py_type, StreamingResponse) and endpoint_function:
            return _extract_streaming_response_info(endpoint_function)
    except ImportError:
        pass
    
    # Not a streaming type
    return None, None, {}


def _extract_streaming_response_info(endpoint_function) -> tuple[
    Optional[StreamingClientType], 
    Optional[str], 
    dict[str, Any]
]:
    """
    Extract streaming information from StreamingResponse calls using scope-aware AST analysis.
    
    Args:
        endpoint_function: Function to analyze
        
    Returns:
        Tuple of (streaming_client_type, streaming_media_type, streaming_metadata)
    """
    try:
        # Use scope-aware return detection
        returns = find_function_returns(endpoint_function)
        
        for return_node in returns:
            if return_node.value and isinstance(return_node.value, ast.Call):
                result = _analyze_streaming_response_call(return_node.value)
                if result[0]:  # streaming_client_type found
                    return result
        
        return None, None, {}
        
    except Exception:
        return None, None, {}


def _extract_streaming_info_from_ast(endpoint_function) -> tuple[
    Optional[StreamingClientType], 
    Optional[str], 
    dict[str, Any]
]:
    """
    Extract streaming information from function body using scope-aware AST analysis.
    
    Fallback method for cases where type annotations and response_model don't provide info.
    
    Args:
        endpoint_function: Function to analyze
        
    Returns:
        Tuple of (streaming_client_type, streaming_media_type, streaming_metadata)
    """
    try:
        # Use scope-aware return detection
        returns = find_function_returns(endpoint_function)
        
        for return_node in returns:
            if return_node.value:
                result = _analyze_return_statement(return_node.value)
                if result[0]:  # streaming_client_type found
                    return result
        
        return None, None, {}
        
    except Exception:
        return None, None, {}


def _analyze_streaming_response_call(call_node: ast.AST) -> tuple[
    Optional[StreamingClientType], 
    Optional[str], 
    dict[str, Any]
]:
    """
    Analyze StreamingResponse call to extract media type and client type.
    
    Args:
        call_node: AST node representing StreamingResponse call
        
    Returns:
        Tuple of (streaming_client_type, streaming_media_type, streaming_metadata)
    """
    
    if not isinstance(call_node, ast.Call):
        return None, None, {}
    
    # Check if this is a StreamingResponse call
    is_streaming_call = False
    if isinstance(call_node.func, ast.Name) and call_node.func.id == 'StreamingResponse':
        is_streaming_call = True
    elif isinstance(call_node.func, ast.Attribute) and call_node.func.attr == 'StreamingResponse':
        is_streaming_call = True
    
    if not is_streaming_call:
        return None, None, {}
    
    # Extract media_type from keyword arguments
    media_type = _extract_media_type_from_call(call_node)
    if media_type:
        client_type = _map_media_type_to_client_type(media_type)
        return client_type, media_type, {}
    
    # Default to readable stream if no media_type specified
    return StreamingClientType.READABLE_STREAM, None, {}


def _analyze_return_statement(return_node: ast.AST) -> tuple[
    Optional[StreamingClientType], 
    Optional[str], 
    dict[str, Any]
]:
    """
    Analyze any return statement for streaming responses.
    
    Args:
        return_node: AST node representing return statement value
        
    Returns:
        Tuple of (streaming_client_type, streaming_media_type, streaming_metadata)
    """
    
    if not isinstance(return_node, ast.Call):
        return None, None, {}
    
    # Check for EventSourceResponse(...)
    if isinstance(return_node.func, ast.Name):
        if return_node.func.id == 'EventSourceResponse':
            return StreamingClientType.EVENT_SOURCE, "text/event-stream", {}
        if return_node.func.id == 'StreamingResponse':
            return _analyze_streaming_response_call(return_node)
    
    # Check for qualified names
    if isinstance(return_node.func, ast.Attribute):
        if return_node.func.attr == 'EventSourceResponse':
            return StreamingClientType.EVENT_SOURCE, "text/event-stream", {}
        if return_node.func.attr == 'StreamingResponse':
            return _analyze_streaming_response_call(return_node)
    
    return None, None, {}


def _extract_media_type_from_call(call_node: ast.Call) -> Optional[str]:
    """
    Extract media_type parameter from function call.
    
    Args:
        call_node: AST Call node
        
    Returns:
        Media type string or None
    """
    
    # Check keyword arguments
    for keyword in call_node.keywords:
        if keyword.arg == 'media_type':
            # Python 3.8+
            if isinstance(keyword.value, ast.Constant):
                return keyword.value.value
            # Python < 3.8 compatibility
            if isinstance(keyword.value, ast.Str):
                return keyword.value.s
    
    return None


def _map_media_type_to_client_type(media_type: str) -> StreamingClientType:
    """
    Map MIME type to client generation pattern.
    
    Args:
        media_type: MIME type string
        
    Returns:
        StreamingClientType enum value
    """
    
    if media_type == "text/event-stream":
        return StreamingClientType.EVENT_SOURCE
    
    elif media_type in {"application/json", "application/x-ndjson", "application/x-jsonlines"}:
        return StreamingClientType.READABLE_STREAM
        
    elif media_type.startswith(("video/", "audio/", "image/")) or media_type in {
        "application/pdf", "application/octet-stream", "application/zip"
    }:
        return StreamingClientType.FILE_DOWNLOAD
        
    elif media_type.startswith("text/"):
        return StreamingClientType.TEXT_STREAM
        
    else:
        # Unknown - default to readable stream
        return StreamingClientType.READABLE_STREAM
