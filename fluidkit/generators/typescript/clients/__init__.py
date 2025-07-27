"""
TypeScript client generation routing module.

Main entry point for generating TypeScript clients for FastAPI routes.
Routes between regular fetch clients and streaming clients based on route type.
"""

from typing import List

from .streaming import (
    generate_sse_wrapper,
    generate_streaming_wrapper,
    generate_text_stream_wrapper,
    generate_file_download_wrapper,
    generate_readable_stream_wrapper,
)
from .fetch import generate_fetch_wrapper
from fluidkit.core.schema import RouteNode
from fluidkit.core.constants import FluidKitRuntime


def generate_client_wrapper(
    route: RouteNode,
    api_result_type: str = FluidKitRuntime.API_RESULT_TYPE,
    get_base_url_fn: str = FluidKitRuntime.GET_BASE_URL_FN,
    handle_response_fn: str = FluidKitRuntime.HANDLE_RESPONSE_FN
) -> tuple[str, List[str]]:
    """
    Generate TypeScript client wrapper for any route type.
    
    Routes to appropriate generator based on route characteristics:
    - Streaming routes → streaming generators (SSE, JSON streaming, etc.)
    - Regular routes → fetch generator (REST API with fetch())
    
    Args:
        route: RouteNode to generate client for
        api_result_type: Name of the ApiResult type from FluidKit runtime
        get_base_url_fn: Name of the getBaseUrl function from FluidKit runtime
        handle_response_fn: Name of the handleResponse function from FluidKit runtime
        
    Returns:
        Tuple of (generated_code, used_runtime_types)
    """
    
    if route.is_streaming:
        return generate_streaming_wrapper(
            route=route,
            api_result_type=api_result_type,
            get_base_url_fn=get_base_url_fn,
            handle_response_fn=handle_response_fn
        )
    else:
        return generate_fetch_wrapper(
            route=route,
            api_result_type=api_result_type,
            get_base_url_fn=get_base_url_fn,
            handle_response_fn=handle_response_fn
        )


# Export all available generators
__all__ = [
    # Main entry points
    'generate_fetch_wrapper',       # Direct fetch generation
    'generate_client_wrapper',      # Routes to fetch or streaming
    'generate_streaming_wrapper',   # Direct streaming generation
    
    # Specific streaming generators
    'generate_sse_wrapper',
    'generate_text_stream_wrapper',
    'generate_file_download_wrapper',
    'generate_readable_stream_wrapper',
]
