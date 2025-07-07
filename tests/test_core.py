"""
Core functionality tests for FluidKit type system and data structures
"""

from fluidkit.core.type_conversion import python_type_to_field_annotation
from fluidkit.core.schema import FieldAnnotation, BaseType, ContainerType, ModuleLocation


def test_python_type_to_field_annotation():
    """Test conversion of various Python types to FieldAnnotation"""
    from enum import Enum
    from typing import Optional, List, Union, Dict, Tuple
    
    # Create test classes
    class User:
        name: str
        age: int
    
    class UserStatus(Enum):
        ACTIVE = "active"
        INACTIVE = "inactive"
    
    test_cases = [
        # Primitives
        (int, "number"),
        (str, "string"), 
        (bool, "boolean"),
        
        # Optional
        (Optional[str], "Optional[string]"),
        (Optional[int], "Optional[number]"),
        
        # Lists
        (List[str], "Array[string]"),
        (List[User], "Array[User]"),
        
        # Unions
        (Union[str, int], "Union[string, number]"),
        (Union[User, UserStatus], "Union[User, UserStatus]"),
        
        # Complex nested
        (Optional[List[Union[User, UserStatus]]], "Optional[Array[Union[User, UserStatus]]]"),
        
        # Dicts
        (Dict[str, int], "Record<string, number>"),
        (dict, "Record<string, any>"),
        
        # Tuples
        (Tuple[str, int], "Tuple[string, number]"),
    ]
    
    print("=== TYPE CONVERSION TESTS ===")
    for py_type, expected_desc in test_cases:
        annotation = python_type_to_field_annotation(py_type)
        print(f"{py_type} -> {annotation}")
        print(f"  Expected: {expected_desc}")
        print(f"  Container: {annotation.container}")
        print(f"  Base: {annotation.base_type}")
        print(f"  Custom: {annotation.custom_type}")
        if annotation.args:
            print(f"  Args: {len(annotation.args)} arguments")
        print()


def test_module_location_path_calculation():
    """Test ModuleLocation path calculation and conversion"""
    
    # Test basic location creation
    location = ModuleLocation(
        module_path="routes.users.page",
        file_path="/project/routes/users/page.py"
    )
    
    print("=== MODULE LOCATION TESTS ===")
    print(f"Module path: {location.module_path}")
    print(f"File path: {location.file_path}")
    
    # Test TypeScript file path conversion
    ts_path = location.get_typescript_file_path()
    print(f"TypeScript path: {ts_path}")
    
    # Test relative import calculation
    target_location = ModuleLocation(
        module_path="models.user",
        file_path="/project/models/user.py"
    )
    
    relative_path = location.calculate_relative_import_path(target_location)
    print(f"Relative import path: {relative_path}")
    print()


def test_field_annotation_system():
    """Test FieldAnnotation creation and analysis"""
    
    print("=== FIELD ANNOTATION TESTS ===")
    
    # Test simple types
    string_annotation = FieldAnnotation(base_type=BaseType.STRING)
    print(f"String annotation: {string_annotation}")
    print(f"Is simple: {string_annotation.is_simple()}")
    print(f"Is optional: {string_annotation.is_optional()}")
    
    # Test optional types
    optional_annotation = FieldAnnotation(
        container=ContainerType.OPTIONAL,
        args=[FieldAnnotation(base_type=BaseType.STRING)]
    )
    print(f"Optional annotation: {optional_annotation}")
    print(f"Is optional: {optional_annotation.is_optional()}")
    
    # Test custom types
    custom_annotation = FieldAnnotation(custom_type="User")
    referenced_types = custom_annotation.get_referenced_types()
    print(f"Custom annotation: {custom_annotation}")
    print(f"Referenced types: {referenced_types}")
    print()


def run_core_tests():
    """Run all core tests"""
    test_python_type_to_field_annotation()
    test_module_location_path_calculation()
    test_field_annotation_system()
    print("Core tests completed")


if __name__ == "__main__":
    run_core_tests()
