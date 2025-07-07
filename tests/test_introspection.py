"""
Introspection tests for FastAPI routes and Pydantic models
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

from fluidkit.core.schema import ModuleLocation, FieldAnnotation, BaseType
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
    location = ModuleLocation.from_python_object(UserStatus)
    status_model = _introspect_enum_model(UserStatus, location)
    print(f"UserStatus Enum: {status_model.name}")
    print(f"  Fields: {[f.name for f in status_model.fields]}")
    print(f"  Is Enum: {status_model.is_enum}")
    print()
    
    # Test Pydantic model introspection
    location = ModuleLocation.from_python_object(User)
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


def run_introspection_tests():
    """Run all introspection tests"""
    test_pydantic_model_introspection()
    test_route_parameter_processing()
    test_model_discovery_from_routes()
    print("Introspection tests completed")


if __name__ == "__main__":
    run_introspection_tests()
