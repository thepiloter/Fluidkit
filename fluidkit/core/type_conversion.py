"""
FluidKit V2 Type Conversion for Runtime Introspection

Converts Python runtime type objects to FluidKit's FieldAnnotation system.
Handles typing module constructs, primitive types, and custom classes with
full recursive support for complex nested types.
"""

import typing
import inspect
from enum import Enum
from functools import lru_cache
from typing import Any, Union, Optional, get_origin, get_args

from fluidkit.core.schema import FieldAnnotation, BaseType, ContainerType


@lru_cache(maxsize=256)
def python_type_to_field_annotation(py_type: Any) -> FieldAnnotation:
    """
    Convert Python runtime type object to FieldAnnotation.
    
    Handles all typing module constructs, primitives, and custom classes.
    Supports complex nested types like Optional[List[Union[User, Product]]].
    
    Args:
        py_type: Python type object from typing.get_type_hints() or inspect
        
    Returns:
        FieldAnnotation representing the type structure
    """
    if py_type is None or py_type is type(None):
        return FieldAnnotation(base_type=BaseType.NULL)
    
    # Handle typing module constructs (Optional, List, Union, etc.)
    origin = get_origin(py_type)
    if origin is not None:
        return _convert_typing_construct(py_type, origin)
    
    # Handle primitive types
    if _is_primitive_type(py_type):
        return _convert_primitive_type(py_type)
    
    # Handle custom classes (User, UserStatus, etc.)
    if inspect.isclass(py_type):
        return _convert_custom_type(py_type)
    
    # Fallback for unknown types
    return FieldAnnotation(base_type=BaseType.ANY)


def _convert_typing_construct(py_type: Any, origin: Any) -> FieldAnnotation:
    """Convert typing module constructs (Optional, List, Union, etc.)."""
    args = get_args(py_type)
    
    # Union types (including Optional)
    if origin is Union:
        return _convert_union_type(args)
    
    # List/Array types
    elif origin is list or origin is typing.List:
        return _convert_list_type(args)
    
    # Dict/Object types  
    elif origin is dict or origin is typing.Dict:
        return _convert_dict_type(args)
    
    # Tuple types
    elif origin is tuple or origin is typing.Tuple:
        return _convert_tuple_type(args)
    
    # Literal types
    elif hasattr(typing, 'Literal') and origin is typing.Literal:
        return _convert_literal_type(args)
    
    # Generic types we don't specifically handle
    else:
        return FieldAnnotation(base_type=BaseType.ANY)


def _convert_union_type(args: tuple) -> FieldAnnotation:
    """
    Convert Union types, including Optional (Union[T, None]).
    
    Args:
        args: Union type arguments
        
    Returns:
        FieldAnnotation with UNION or OPTIONAL container
    """
    if len(args) == 2 and type(None) in args:
        # This is Optional[T] = Union[T, None]
        non_none_type = args[0] if args[1] is type(None) else args[1]
        inner_annotation = python_type_to_field_annotation(non_none_type)
        return FieldAnnotation(
            container=ContainerType.OPTIONAL,
            args=[inner_annotation]
        )
    else:
        # This is a regular Union[A, B, C]
        union_args = []
        for arg in args:
            union_args.append(python_type_to_field_annotation(arg))
        return FieldAnnotation(
            container=ContainerType.UNION,
            args=union_args
        )


def _convert_list_type(args: tuple) -> FieldAnnotation:
    """Convert List[T] to ARRAY container."""
    if args:
        inner_annotation = python_type_to_field_annotation(args[0])
        return FieldAnnotation(
            container=ContainerType.ARRAY,
            args=[inner_annotation]
        )
    else:
        # List without type parameter becomes list of any
        return FieldAnnotation(
            container=ContainerType.ARRAY,
            args=[FieldAnnotation(base_type=BaseType.ANY)]
        )


def _convert_dict_type(args: tuple) -> FieldAnnotation:
    """Convert Dict[K, V] to OBJECT container."""
    if len(args) >= 2:
        key_annotation = python_type_to_field_annotation(args[0])
        value_annotation = python_type_to_field_annotation(args[1])
        return FieldAnnotation(
            container=ContainerType.OBJECT,
            args=[key_annotation, value_annotation]
        )
    elif len(args) == 1:
        # Dict[V] assumes string keys
        value_annotation = python_type_to_field_annotation(args[0])
        return FieldAnnotation(
            container=ContainerType.OBJECT,
            args=[
                FieldAnnotation(base_type=BaseType.STRING),
                value_annotation
            ]
        )
    else:
        # Dict without parameters
        return FieldAnnotation(
            container=ContainerType.OBJECT,
            args=[
                FieldAnnotation(base_type=BaseType.STRING),
                FieldAnnotation(base_type=BaseType.ANY)
            ]
        )


def _convert_tuple_type(args: tuple) -> FieldAnnotation:
    """Convert Tuple[A, B, ...] to TUPLE container."""
    tuple_args = []
    for arg in args:
        tuple_args.append(python_type_to_field_annotation(arg))
    
    return FieldAnnotation(
        container=ContainerType.TUPLE,
        args=tuple_args
    )


def _convert_literal_type(args: tuple) -> FieldAnnotation:
    """Convert Literal["a", "b"] to LITERAL container."""
    literal_values = []
    for arg in args:
        if isinstance(arg, (str, int, float, bool)):
            literal_values.append(str(arg))
        else:
            literal_values.append(str(arg))
    
    return FieldAnnotation(
        container=ContainerType.LITERAL,
        literal_values=literal_values
    )


def _convert_primitive_type(py_type: type) -> FieldAnnotation:
    """Convert primitive Python types to BaseType."""
    if py_type is int or py_type is float:
        return FieldAnnotation(base_type=BaseType.NUMBER)
    elif py_type is str:
        return FieldAnnotation(base_type=BaseType.STRING)
    elif py_type is bool:
        return FieldAnnotation(base_type=BaseType.BOOLEAN)
    elif py_type is dict:
        return FieldAnnotation(
            container=ContainerType.OBJECT,
            args=[
                FieldAnnotation(base_type=BaseType.STRING),
                FieldAnnotation(base_type=BaseType.ANY)
            ]
        )
    elif py_type is list:
        return FieldAnnotation(
            container=ContainerType.ARRAY,
            args=[FieldAnnotation(base_type=BaseType.ANY)]
        )
    else:
        return FieldAnnotation(base_type=BaseType.ANY)


def _convert_custom_type(py_type: type) -> FieldAnnotation:
    """
    Convert custom classes (User, UserStatus, etc.) to custom_type annotation.
    
    Handles module prefixes and extracts clean class names.
    """
    # Check for common external types first
    common_external = _check_common_external_type(py_type)
    if common_external:
        return common_external
    
    # Custom type logic for project types
    class_name = py_type.__name__
    
    # Clean up module prefixes like "__main__.User" -> "User"
    if hasattr(py_type, '__module__'):
        module = py_type.__module__
        if module == '__main__':
            # For testing/development, just use the class name
            clean_name = class_name
        else:
            # For real modules, might want to preserve some module info
            # But for now, just use class name for simplicity
            clean_name = class_name
    else:
        clean_name = class_name
    
    return FieldAnnotation(custom_type=clean_name, class_reference=py_type)


def _is_primitive_type(py_type: Any) -> bool:
    """Check if type is a Python primitive type."""
    primitive_types = {int, float, str, bool, dict, list, tuple, set}
    return py_type in primitive_types


def _check_common_external_type(py_type: type) -> Optional[FieldAnnotation]:
    """
    Check for common external types using simple instance checking.
    
    Returns FieldAnnotation with is_common_external=True if found.
    """
    # Python built-ins (always available)
    import uuid
    from decimal import Decimal
    from datetime import datetime, date
    from pathlib import Path
    
    if py_type is uuid.UUID:
        return FieldAnnotation(
            custom_type="UUID",
            is_common_external=True,
            class_reference=py_type
        )
    
    if py_type is Decimal:
        return FieldAnnotation(
            custom_type="Decimal", 
            is_common_external=True,
            class_reference=py_type
        )
    
    if py_type is datetime:
        return FieldAnnotation(
            custom_type="datetime",
            is_common_external=True,
            class_reference=py_type
        )
    
    if py_type is date:
        return FieldAnnotation(
            custom_type="date",
            is_common_external=True,
            class_reference=py_type
        )
    
    if py_type is Path:
        return FieldAnnotation(
            custom_type="Path",
            is_common_external=True,
            class_reference=py_type
        )
    
    # Common third-party (with try/catch)
    try:
        from pydantic import EmailStr, HttpUrl
        if py_type is EmailStr:
            return FieldAnnotation(
                custom_type="EmailStr",
                is_common_external=True,
                class_reference=py_type
            )
        if py_type is HttpUrl:
            return FieldAnnotation(
                custom_type="HttpUrl", 
                is_common_external=True,
                class_reference=py_type
            )
    except ImportError:
        pass
    
    try:
        from pydantic_extra_types.payment import PaymentCardNumber
        if py_type is PaymentCardNumber:
            return FieldAnnotation(
                custom_type="PaymentCardNumber",
                is_common_external=True,
                class_reference=py_type
            )
    except ImportError:
        pass
    
    return None


# === TESTING HELPERS === #

def test_type_conversion():
    """Test various type conversion scenarios."""
    from typing import Optional, List, Union, Dict, Tuple
    
    # Create some dummy classes for testing
    class User:
        name: str
        age: int
    
    class UserStatus(Enum):
        ACTIVE = "active"
        INACTIVE = "inactive"
    
    test_cases = [
        # # Primitives
        # (int, "BaseType.NUMBER"),
        # (str, "BaseType.STRING"), 
        # (bool, "BaseType.BOOLEAN"),
        
        # # Optional
        # (Optional[str], "Optional[string]"),
        # (Optional[int], "Optional[number]"),
        
        # # Lists
        # (List[str], "Array[string]"),
        # (List[User], "Array[User]"),
        
        # # Unions
        # (Union[str, int], "Union[string, number]"),
        # (Union[User, UserStatus], "Union[User, UserStatus]"),
        
        # Complex nested
        (Optional[List[Union[User, UserStatus]]], "Optional[Array[Union[User, UserStatus]]]"),
        
        # # Dicts
        # (Dict[str, int], "Record<string, number>"),
        # (dict, "Record<string, any>"),
        
        # # Tuples
        # (Tuple[str, int], "Tuple[string, number]"),
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


if __name__ == "__main__":
    test_type_conversion()
