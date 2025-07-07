"""
Code generation tests for TypeScript interfaces, clients, and imports
"""

from generators.typescript.interfaces import generate_interface
from generators.typescript.clients import generate_fetch_wrapper
from generators.typescript.imports import generate_imports_for_file, ImportContext
from core.schema import (ModelNode, RouteNode, Field, FieldAnnotation, FieldConstraints, 
ModuleLocation, FluidKitApp, BaseType, ParameterType)


def test_typescript_interface_generation():
    """Test TypeScript interface generation with various scenarios"""
    
    location = ModuleLocation(module_path="test.models", file_path="/test/models.py")
    
    print("=== TYPESCRIPT INTERFACE GENERATION TESTS ===")
    
    # Test 1: Simple Interface
    print("Test 1: Simple Interface")
    simple_user = ModelNode(
        name="User",
        fields=[
            Field(
                name="id",
                annotation=FieldAnnotation(base_type=BaseType.NUMBER),
                default=None,
                description="User identifier"
            ),
            Field(
                name="name", 
                annotation=FieldAnnotation(base_type=BaseType.STRING),
                default="Anonymous",
                description="User name"
            ),
            Field(
                name="active",
                annotation=FieldAnnotation(base_type=BaseType.BOOLEAN),
                default=True
            )
        ],
        location=location,
        docstring="Simple user model",
        inheritance=["BaseModel"],
        is_enum=False
    )
    
    result = generate_interface(simple_user)
    print(result)
    print("\n" + "="*50 + "\n")
    
    # Test 2: Enum
    print("Test 2: Enum")
    status_enum = ModelNode(
        name="UserStatus",
        fields=[
            Field(
                name="ACTIVE",
                annotation=FieldAnnotation(base_type=BaseType.STRING),
                default="active"
            ),
            Field(
                name="INACTIVE",
                annotation=FieldAnnotation(base_type=BaseType.STRING),
                default="inactive"
            )
        ],
        location=location,
        docstring="User status enumeration",
        inheritance=["Enum"],
        is_enum=True
    )
    
    result = generate_interface(status_enum)
    print(result)
    print("\n" + "="*50 + "\n")


def test_typescript_client_generation():
    """Test TypeScript fetch wrapper generation"""
    
    location = ModuleLocation(module_path="test.routes", file_path="/test/routes.py")
    
    print("=== TYPESCRIPT CLIENT GENERATION TESTS ===")
    
    # Test 1: Single Method Route
    print("Test 1: Single Method Route")
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
    
    # Test 2: Multi-Method Route
    print("Test 2: Multi-Method Route")
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


def test_import_statement_generation():
    """Test import statement generation with various scenarios"""
    
    # Create test locations
    route_location = ModuleLocation(
        module_path="routes.users.page", 
        file_path="/project/routes/users/page.py"
    )
    
    model_location = ModuleLocation(
        module_path="models.user",
        file_path="/project/models/user.py"
    )
    
    # Create test models
    user_model = ModelNode(
        name="User",
        fields=[],
        location=model_location
    )
    
    # Create test route that references User
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
        location=route_location,
        return_type=FieldAnnotation(custom_type="User")
    )
    
    # Create FluidKitApp
    fluid_app = FluidKitApp(models=[user_model], routes=[route])
    
    # Test both strategies
    strategies = ["co-locate", "mirror"]
    
    print("=== IMPORT STATEMENT GENERATION TESTS ===")
    
    for strategy in strategies:
        print(f"\nTesting {strategy.upper()} Strategy")
        
        context = ImportContext(
            source_location=route_location,
            strategy=strategy,
            project_root="/project"
        )
        
        # Test type imports only
        print("Type imports only:")
        imports = generate_imports_for_file(
            nodes=[route],
            context=context,
            fluid_app=fluid_app,
            needs_runtime=False
        )
        print(imports or "(no imports needed)")
        
        # Test with runtime imports
        print("\nWith runtime imports:")
        imports = generate_imports_for_file(
            nodes=[route],
            context=context,
            fluid_app=fluid_app,
            needs_runtime=True
        )
        print(imports)


def run_generator_tests():
    """Run all generator tests"""
    test_typescript_interface_generation()
    test_typescript_client_generation()
    test_import_statement_generation()
    print("Generator tests completed")


if __name__ == "__main__":
    run_generator_tests()
