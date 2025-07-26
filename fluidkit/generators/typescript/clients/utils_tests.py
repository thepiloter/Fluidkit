"""
Tests for TypeScript client generation utilities and routing.
"""

from fluidkit.core.schema import RouteNode, Field, FieldAnnotation, FieldConstraints, ModuleLocation, BaseType, ParameterType, StreamingClientType
from . import generate_client_wrapper, generate_fetch_wrapper, generate_streaming_wrapper


def get_client_type_info(route: RouteNode) -> dict:
    """Get information about what type of client will be generated for a route."""
    
    info = {
        "route_name": route.name,
        "methods": route.methods,
        "path": route.path,
        "is_streaming": route.is_streaming,
        "client_type": "fetch"
    }
    
    if route.is_streaming:
        info.update({
            "client_type": "streaming",
            "streaming_client_type": route.streaming_client_type.value if route.streaming_client_type else None,
            "streaming_media_type": route.streaming_media_type,
            "streaming_patterns": {
                "is_sse": route.is_sse,
                "is_readable_stream": route.is_readable_stream,
                "is_file_download": route.is_file_download,
                "is_text_stream": route.is_text_stream
            }
        })
    
    return info


def test_client_routing():
    """Test client generation routing logic."""
    location = ModuleLocation(module_path="test.routes", file_path="/test/routes.py")
    
    print("=== CLIENT ROUTING TESTS ===")
    
    # Test 1: Regular REST endpoint
    print("\n1. Testing regular REST route:")
    rest_route = RouteNode(
        name="getUser",
        methods=["GET"],
        path="/users/{id}",
        parameters=[
            Field(
                name="id",
                annotation=FieldAnnotation(base_type=BaseType.NUMBER),
                constraints=FieldConstraints(parameter_type=ParameterType.PATH)
            )
        ],
        location=location,
        return_type=FieldAnnotation(custom_type="User")
    )
    
    info = get_client_type_info(rest_route)
    print(f"   Client type: {info['client_type']}")
    print(f"   Is streaming: {info['is_streaming']}")
    
    # Test 2: SSE endpoint
    print("\n2. Testing SSE route:")
    sse_route = RouteNode(
        name="streamEvents",
        methods=["GET"],
        path="/events",
        parameters=[],
        location=location,
        streaming_client_type=StreamingClientType.EVENT_SOURCE,
        streaming_media_type="text/event-stream"
    )
    
    info = get_client_type_info(sse_route)
    print(f"   Client type: {info['client_type']}")
    print(f"   Streaming type: {info['streaming_client_type']}")
    print(f"   Is SSE: {info['streaming_patterns']['is_sse']}")
    
    print("\n✅ Client routing tests completed!")


def test_client_generation_integration():
    """Test end-to-end client generation for different route types."""
    location = ModuleLocation(module_path="test.routes", file_path="/test/routes.py")
    
    print("=== CLIENT GENERATION INTEGRATION TESTS ===")
    
    # Test 1: Generate regular fetch client
    print("\n1. Testing regular fetch client generation:")
    rest_route = RouteNode(
        name="getUser",
        methods=["GET"], 
        path="/users/{id}",
        parameters=[],
        location=location
    )
    
    try:
        client_code = generate_client_wrapper(rest_route)
        print(f"   Generated {len(client_code)} characters of fetch client code")
        print("   ✅ SUCCESS")
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
    
    # Test 2: Generate SSE client
    print("\n2. Testing SSE client generation:")
    sse_route = RouteNode(
        name="streamEvents",
        methods=["GET"],
        path="/events",
        parameters=[],
        location=location,
        streaming_client_type=StreamingClientType.EVENT_SOURCE,
        streaming_media_type="text/event-stream"
    )
    
    try:
        client_code = generate_client_wrapper(sse_route)
        print(f"   Generated {len(client_code)} characters of SSE client code")
        print("   ✅ SUCCESS")
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
    
    print("\n🎉 Integration tests completed!")


if __name__ == "__main__":
    test_client_routing()
    test_client_generation_integration()
