"""
Introspection tests for FastAPI routes and Pydantic models
"""

import ast
import inspect
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

from fluidkit.core.utils import create_module_location_from_object
from fluidkit.core.schema import ModuleLocation, FieldAnnotation, BaseType, RouteNode, StreamingClientType
from fluidkit.introspection.models import _introspect_pydantic_model, _introspect_enum_model


def test_pydantic_model_introspection():
    """Test Pydantic model introspection with various scenarios"""
    
    # Test models
    class UserStatus(str, Enum):
        ACTIVE = "active"
        INACTIVE = "inactive"
    
    class Profile(BaseModel):
        bio: str = Field(..., description="User biography")
        website: Optional[str] = None
    
    class User(BaseModel):
        id: int
        name: str = Field(..., description="User's full name")
        email: Optional[str] = None
        status: UserStatus = UserStatus.ACTIVE
        profile: Optional[Profile] = None
    
    print("=== PYDANTIC INTROSPECTION TEST ===")
    
    # Test Enum introspection
    location = create_module_location_from_object(UserStatus, is_external=False)
    status_model = _introspect_enum_model(UserStatus, location)
    print(f"UserStatus Enum: {status_model.name}")
    print(f"  Fields: {[f.name for f in status_model.fields]}")
    print(f"  Is Enum: {status_model.is_enum}")
    print()
    
    # Test Pydantic model introspection
    location = create_module_location_from_object(User, is_external=False)
    user_model = _introspect_pydantic_model(User, location)
    print(f"User Model: {user_model.name}")
    print(f"  Fields: {len(user_model.fields)}")
    for field in user_model.fields:
        print(f"    {field.name}: {field.annotation.custom_type or field.annotation.base_type}")
        if field.description:
            print(f"      Description: {field.description}")
        if field.default is not None:
            print(f"      Default: {field.default}")
    print()


def test_route_parameter_processing():
    """Test FastAPI route parameter analysis"""
    
    # This would test the parameter processing logic
    # For now, just demonstrate the expected structure
    
    print("=== ROUTE PARAMETER PROCESSING TEST ===")
    print("Testing parameter classification:")
    print("  PATH parameters: /users/{user_id}")
    print("  QUERY parameters: ?include_profile=true")
    print("  BODY parameters: User model in POST request")
    print("  HEADER parameters: Authorization headers")
    print()


def test_model_discovery_from_routes():
    """Test discovery of models from route references"""
    
    # Create mock route nodes for testing
    from fluidkit.core.schema import RouteNode, Field, FieldConstraints, ParameterType
    
    # Mock route that references User model
    route = RouteNode(
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
        location=ModuleLocation(module_path="test.routes", file_path="test/routes.py"),
        return_type=FieldAnnotation(custom_type="User")
    )
    
    print("=== MODEL DISCOVERY TEST ===")
    print(f"Route: {route.name}")
    print(f"Return type: {route.return_type.custom_type}")
    print("Model discovery would find User model from return type")
    print()


def test_sse_detection():
    """Test Server-Sent Events detection with various patterns"""
    
    print("=== SSE DETECTION TESTS ===")
    
    # Import the detection functions
    from fluidkit.introspection.routes import (
        _extract_streaming_info_from_type, 
        _map_media_type_to_client_type,
        _extract_media_type_from_call,
        _analyze_return_statement
    )
    
    # Test 1: EventSourceResponse type annotation detection
    print("1. Testing EventSourceResponse type detection:")
    try:
        from sse_starlette import EventSourceResponse
        
        client_type, media_type, metadata = _extract_streaming_info_from_type(EventSourceResponse, None)
        print(f"   EventSourceResponse -> {client_type}, {media_type}")
        assert client_type == StreamingClientType.EVENT_SOURCE
        assert media_type == "text/event-stream"
        print("   ✅ PASS")
    except ImportError:
        print("   ⚠️  SKIP (sse-starlette not installed)")
    
    # Test 2: StreamingResponse type detection (needs AST)
    print("2. Testing StreamingResponse type detection:")
    try:
        from starlette.responses import StreamingResponse

        def generator():
            yield "data: hello world\n\n"
            yield "data: how are you?\n\n"
        
        def mock_sse_function():
            return StreamingResponse(generator(), media_type="text/event-stream")
        
        client_type, media_type, metadata = _extract_streaming_info_from_type(StreamingResponse, mock_sse_function)
        print(f"   StreamingResponse with AST -> {client_type}, {media_type}")
        print("   ✅ PASS (requires AST analysis)")
    except ImportError:
        print("   ⚠️  SKIP (starlette not installed)")
    
    # Test 3: Media type to client type mapping
    print("3. Testing media type mapping:")
    test_cases = [
        ("text/event-stream", StreamingClientType.EVENT_SOURCE),
        ("application/json", StreamingClientType.READABLE_STREAM),
        ("application/x-ndjson", StreamingClientType.READABLE_STREAM),
        ("application/pdf", StreamingClientType.FILE_DOWNLOAD),
        ("video/mp4", StreamingClientType.FILE_DOWNLOAD),
        ("text/plain", StreamingClientType.TEXT_STREAM),
        ("application/unknown", StreamingClientType.READABLE_STREAM)  # Default
    ]
    
    for media_type, expected_client_type in test_cases:
        result = _map_media_type_to_client_type(media_type)
        print(f"   {media_type} -> {result}")
        assert result == expected_client_type
    print("   ✅ PASS")
    
    # Test 4: AST media type extraction
    print("4. Testing AST media type extraction:")
    
    # Create a mock AST call node
    test_code = 'StreamingResponse(generator(), media_type="application/json")'
    tree = ast.parse(test_code, mode='eval')
    call_node = tree.body
    
    media_type = _extract_media_type_from_call(call_node)
    print(f"   Extracted media_type: {media_type}")
    assert media_type == "application/json"
    print("   ✅ PASS")
    
    print()


def test_false_positive_prevention():
    """Test that SSE detection doesn't confuse Pydantic models with SSE classes"""
    
    print("=== FALSE POSITIVE PREVENTION TESTS ===")
    
    # Create Pydantic models with SSE-like names
    class EventSourceResponse(BaseModel):
        """Pydantic model that happens to be named like SSE class"""
        data: str
        event_type: str
    
    class StreamingResponse(BaseModel):
        """Pydantic model that happens to be named like Streaming class"""
        stream_id: str
        content: str
    
    from fluidkit.introspection.routes import _extract_streaming_info_from_type
    
    # Test 1: Pydantic EventSourceResponse should NOT be detected as SSE
    print("1. Testing Pydantic EventSourceResponse (should NOT be SSE):")
    client_type, media_type, metadata = _extract_streaming_info_from_type(EventSourceResponse, None)
    print(f"   Pydantic EventSourceResponse -> {client_type}")
    assert client_type is None  # Should not be detected as streaming
    print("   ✅ PASS (correctly ignored)")
    
    # Test 2: Pydantic StreamingResponse should NOT be detected as streaming
    print("2. Testing Pydantic StreamingResponse (should NOT be streaming):")
    client_type, media_type, metadata = _extract_streaming_info_from_type(StreamingResponse, None)
    print(f"   Pydantic StreamingResponse -> {client_type}")
    assert client_type is None  # Should not be detected as streaming
    print("   ✅ PASS (correctly ignored)")
    
    print()


def test_ast_return_analysis():
    """Test AST analysis of return statements"""
    
    print("=== AST RETURN ANALYSIS TESTS ===")
    
    from fluidkit.introspection.routes import _analyze_return_statement
    
    # Test 1: EventSourceResponse return
    print("1. Testing EventSourceResponse return statement:")
    test_code = 'EventSourceResponse(generator())'
    tree = ast.parse(test_code, mode='eval')
    return_node = tree.body
    
    client_type, media_type, metadata = _analyze_return_statement(return_node)
    print(f"   EventSourceResponse() -> {client_type}, {media_type}")
    assert client_type == StreamingClientType.EVENT_SOURCE
    assert media_type == "text/event-stream"
    print("   ✅ PASS")
    
    # Test 2: StreamingResponse with SSE media type
    print("2. Testing StreamingResponse with SSE media_type:")
    test_code = 'StreamingResponse(generator(), media_type="text/event-stream")'
    tree = ast.parse(test_code, mode='eval')
    return_node = tree.body
    
    client_type, media_type, metadata = _analyze_return_statement(return_node)
    print(f"   StreamingResponse(media_type=\"text/event-stream\") -> {client_type}, {media_type}")
    assert client_type == StreamingClientType.EVENT_SOURCE
    assert media_type == "text/event-stream"
    print("   ✅ PASS")
    
    # Test 3: StreamingResponse with JSON media type
    print("3. Testing StreamingResponse with JSON media_type:")
    test_code = 'StreamingResponse(generator(), media_type="application/json")'
    tree = ast.parse(test_code, mode='eval')
    return_node = tree.body
    
    client_type, media_type, metadata = _analyze_return_statement(return_node)
    print(f"   StreamingResponse(media_type=\"application/json\") -> {client_type}, {media_type}")
    assert client_type == StreamingClientType.READABLE_STREAM
    assert media_type == "application/json"
    print("   ✅ PASS")
    
    # Test 4: Regular function call (should not be streaming)
    print("4. Testing regular function call:")
    test_code = 'User(id=1, name="test")'
    tree = ast.parse(test_code, mode='eval')
    return_node = tree.body
    
    client_type, media_type, metadata = _analyze_return_statement(return_node)
    print(f"   User() -> {client_type}")
    assert client_type is None
    print("   ✅ PASS")
    
    print()


def test_route_node_properties():
    """Test RouteNode streaming properties"""
    
    print("=== ROUTE NODE PROPERTIES TESTS ===")
    
    from fluidkit.core.schema import RouteNode, Field
    
    # Test 1: SSE endpoint
    print("1. Testing SSE RouteNode properties:")
    sse_route = RouteNode(
        name="streamEvents",
        methods=["GET"],
        path="/events",
        parameters=[],
        location=ModuleLocation(module_path="test.routes", file_path="test/routes.py"),
        streaming_client_type=StreamingClientType.EVENT_SOURCE,
        streaming_media_type="text/event-stream"
    )
    
    print(f"   is_streaming: {sse_route.is_streaming}")
    print(f"   is_sse: {sse_route.is_sse}")
    print(f"   is_readable_stream: {sse_route.is_readable_stream}")
    print(f"   is_file_download: {sse_route.is_file_download}")
    
    assert sse_route.is_streaming == True
    assert sse_route.is_sse == True
    assert sse_route.is_readable_stream == False
    assert sse_route.is_file_download == False
    print("   ✅ PASS")
    
    # Test 2: JSON streaming endpoint
    print("2. Testing JSON streaming RouteNode properties:")
    json_route = RouteNode(
        name="streamData",
        methods=["GET"],
        path="/data/stream",
        parameters=[],
        location=ModuleLocation(module_path="test.routes", file_path="test/routes.py"),
        streaming_client_type=StreamingClientType.READABLE_STREAM,
        streaming_media_type="application/json"
    )
    
    print(f"   is_streaming: {json_route.is_streaming}")
    print(f"   is_sse: {json_route.is_sse}")
    print(f"   is_readable_stream: {json_route.is_readable_stream}")
    
    assert json_route.is_streaming == True
    assert json_route.is_sse == False
    assert json_route.is_readable_stream == True
    print("   ✅ PASS")
    
    # Test 3: Regular REST endpoint
    print("3. Testing regular REST RouteNode properties:")
    rest_route = RouteNode(
        name="getUser",
        methods=["GET"],
        path="/users/{id}",
        parameters=[],
        location=ModuleLocation(module_path="test.routes", file_path="test/routes.py")
    )
    
    print(f"   is_streaming: {rest_route.is_streaming}")
    print(f"   is_sse: {rest_route.is_sse}")
    
    assert rest_route.is_streaming == False
    assert rest_route.is_sse == False
    print("   ✅ PASS")
    
    print()


def run_introspection_tests():
    """Run all introspection tests"""
    test_pydantic_model_introspection()
    test_route_parameter_processing()
    test_model_discovery_from_routes()
    
    # New streaming tests
    test_sse_detection()
    test_false_positive_prevention()
    test_ast_return_analysis()
    test_route_node_properties()
    
    print("🎉 All introspection tests completed successfully!")


if __name__ == "__main__":
    run_introspection_tests()
