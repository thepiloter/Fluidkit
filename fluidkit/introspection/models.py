"""
Pydantic Model Introspection for FluidKit V2

Discovers and introspects Pydantic models and Enums referenced by FastAPI routes
using runtime introspection and tree traversal within project boundaries.
"""

import inspect
from enum import Enum
from pathlib import Path
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from fluidkit.core.utils import format_annotation_for_display
from fluidkit.core.type_conversion import python_type_to_field_annotation
from fluidkit.core.schema import ModelNode, RouteNode, Field, FieldAnnotation, ModuleLocation, BaseType


def discover_models_from_routes(route_nodes: List[RouteNode], project_root: Optional[str] = None) -> List[ModelNode]:
    """
    Discover all Pydantic models and Enums referenced by FastAPI routes.
    
    Uses tree traversal starting from route parameters and return types,
    recursively discovering nested models within project boundaries.
    
    Args:
        route_nodes: List of RouteNode objects from FastAPI introspection
        project_root: Project root directory for boundary detection (optional)
        
    Returns:
        List of discovered ModelNode objects
    """
    discovered = {}  # model_name -> ModelNode (prevent duplicates)
    project_path = Path(project_root).resolve() if project_root else None
    
    # Start tree traversal from all route entry points
    for route in route_nodes:
        # Discover from route parameters
        for param in route.parameters:
            _discover_from_field_annotation(param.annotation, discovered, project_path)
        
        # Discover from return type
        if route.return_type:
            _discover_from_field_annotation(route.return_type, discovered, project_path)
    
    return list(discovered.values())


def _discover_from_field_annotation(annotation: FieldAnnotation, discovered: Dict[str, ModelNode], 
                                  project_path: Optional[Path]):
    """
    Recursively discover models from a FieldAnnotation using tree traversal.
    
    Args:
        annotation: FieldAnnotation to process
        discovered: Dictionary to track discovered models (prevents duplicates)
        project_path: Project root path for boundary detection
    """
    # Process custom types with class references
    if annotation.class_reference and annotation.custom_type:
        model_name = annotation.custom_type
        
        # Skip if already discovered
        if model_name in discovered:
            return
        
        # Check project boundary
        if not _is_within_project_boundary(annotation.class_reference, project_path):
            return
        
        # Introspect the model
        model_node = _introspect_class_to_model_node(annotation.class_reference)
        if model_node:
            discovered[model_name] = model_node
            
            # Recursively discover from model's fields
            for field in model_node.fields:
                _discover_from_field_annotation(field.annotation, discovered, project_path)
    
    # Recursively process generic type arguments
    for arg in annotation.args:
        _discover_from_field_annotation(arg, discovered, project_path)


def _is_within_project_boundary(cls: type, project_path: Optional[Path]) -> bool:
    """
    Check if a class is defined within the project boundaries.
    
    Args:
        cls: Python class object
        project_path: Project root path (None = accept all)
        
    Returns:
        True if class is within project boundaries
    """
    if project_path is None:
        return True  # No boundary restriction
    
    try:
        class_file = Path(inspect.getfile(cls)).resolve()
        return class_file.is_relative_to(project_path)
    except (TypeError, OSError):
        return False


def _introspect_class_to_model_node(cls: type) -> Optional[ModelNode]:
    """
    Convert Python class to ModelNode using runtime introspection.
    
    Handles both Pydantic models and Enums.
    
    Args:
        cls: Python class object (BaseModel or Enum)
        
    Returns:
        ModelNode or None if introspection fails
    """
    try:
        # Get location information
        location = ModuleLocation.from_python_object(cls)
        
        # Handle Pydantic models
        if _is_pydantic_model(cls):
            return _introspect_pydantic_model(cls, location)
        
        # Handle Enums
        elif _is_enum_class(cls):
            return _introspect_enum_model(cls, location)
        
        # Skip other types
        else:
            return None
            
    except Exception as e:
        print(f"Warning: Failed to introspect class {cls.__name__}: {e}")
        return None


def _is_pydantic_model(cls: type) -> bool:
    """Check if class is a Pydantic model."""
    try:
        return issubclass(cls, BaseModel)
    except TypeError:
        return False


def _is_enum_class(cls: type) -> bool:
    """Check if class is an Enum."""
    try:
        return issubclass(cls, Enum)
    except TypeError:
        return False


def _introspect_pydantic_model(cls: type, location: ModuleLocation) -> ModelNode:
    """
    Introspect Pydantic model using Pydantic's field introspection.
    
    Handles both Pydantic V1 and V2 field access patterns.
    
    Args:
        cls: Pydantic model class
        location: ModuleLocation for the class
        
    Returns:
        ModelNode with introspected fields
    """
    fields = []
    
    # Get field information (handle both Pydantic V1 and V2)
    model_fields = _get_pydantic_fields(cls)
    
    for field_name, field_info in model_fields.items():
        try:
            # Extract field annotation
            field_annotation = _extract_field_annotation_from_pydantic_field(cls, field_name, field_info)
            
            # Extract default value
            default_value = _extract_default_from_pydantic_field(field_info)
            
            # Extract description
            description = _extract_description_from_pydantic_field(field_info)
            
            # Create Field object
            field_obj = Field(
                name=field_name,
                annotation=field_annotation,
                default=default_value,
                description=description
            )
            fields.append(field_obj)
            
        except Exception as e:
            print(f"Warning: Failed to introspect field {field_name} in {cls.__name__}: {e}")
            continue
    
    # Extract inheritance information
    inheritance = [base.__name__ for base in cls.__bases__ if base != object]
    
    return ModelNode(
        name=cls.__name__,
        fields=fields,
        location=location,
        docstring=cls.__doc__,
        inheritance=inheritance,
        is_enum=False
    )


def _introspect_enum_model(cls: type, location: ModuleLocation) -> ModelNode:
    """
    Introspect Enum class to ModelNode.
    
    Args:
        cls: Enum class
        location: ModuleLocation for the class
        
    Returns:
        ModelNode representing the enum
    """
    fields = []
    
    # Extract enum members
    for member_name, member_value in cls.__members__.items():
        # Create field for each enum value
        value_annotation = python_type_to_field_annotation(type(member_value.value))
        
        field_obj = Field(
            name=member_name,
            annotation=value_annotation,
            default=member_value.value
        )
        fields.append(field_obj)
    
    # Extract inheritance information
    inheritance = [base.__name__ for base in cls.__bases__ if base != object]
    
    return ModelNode(
        name=cls.__name__,
        fields=fields,
        location=location,
        docstring=cls.__doc__,
        inheritance=inheritance,
        is_enum=True
    )


def _get_pydantic_fields(cls: type) -> Dict[str, Any]:
    """
    Get Pydantic fields, handling both V1 and V2.
    
    Args:
        cls: Pydantic model class
        
    Returns:
        Dictionary of field_name -> field_info
    """
    # Try Pydantic V2 first
    if hasattr(cls, 'model_fields'):
        return cls.model_fields
    
    # Fall back to Pydantic V1
    elif hasattr(cls, '__fields__'):
        return cls.__fields__
    
    # No fields found
    else:
        return {}


def _extract_field_annotation_from_pydantic_field(cls: type, field_name: str, field_info: Any) -> FieldAnnotation:
    """
    Extract type annotation from Pydantic field information.
    
    Args:
        cls: Pydantic model class
        field_name: Name of the field
        field_info: Pydantic field information object
        
    Returns:
        FieldAnnotation representing the field type
    """
    # Try to get annotation from class annotations
    if hasattr(cls, '__annotations__') and field_name in cls.__annotations__:
        py_type = cls.__annotations__[field_name]
        return python_type_to_field_annotation(py_type)
    
    # Try to get from field_info annotation (Pydantic V2)
    elif hasattr(field_info, 'annotation'):
        return python_type_to_field_annotation(field_info.annotation)
    
    # Try to get from field_info type_ (Pydantic V1)
    elif hasattr(field_info, 'type_'):
        return python_type_to_field_annotation(field_info.type_)
    
    # Fallback to Any
    else:
        return FieldAnnotation(base_type=BaseType.ANY)


def _extract_default_from_pydantic_field(field_info: Any) -> Any:
    """
    Extract default value from Pydantic field information.
    
    Args:
        field_info: Pydantic field information object
        
    Returns:
        Default value or None if field is required
    """
    # Handle Pydantic V2
    if hasattr(field_info, 'default'):
        default = field_info.default
        # Check for Pydantic's special "required" markers
        if hasattr(default, '__class__'):
            class_name = default.__class__.__name__
            if 'PydanticUndefined' in class_name or 'Undefined' in class_name:
                return None
        return default
    
    # Handle Pydantic V1
    elif hasattr(field_info, 'default'):
        default = field_info.default
        if default is ...:  # Ellipsis means required
            return None
        return default
    
    # No default found
    return None


def _extract_description_from_pydantic_field(field_info: Any) -> Optional[str]:
    """
    Extract description from Pydantic field information.
    
    Args:
        field_info: Pydantic field information object
        
    Returns:
        Field description or None
    """
    # Try direct description attribute
    if hasattr(field_info, 'description'):
        return field_info.description
    
    # Try field_info (for older Pydantic versions)
    elif hasattr(field_info, 'field_info') and hasattr(field_info.field_info, 'description'):
        return field_info.field_info.description
    
    return None


# === TESTING HELPERS === #

def test_pydantic_introspection():
    """Test Pydantic model introspection with various scenarios."""
    from enum import Enum
    from typing import Optional, List
    from pydantic import BaseModel, Field
    
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
    
    # Test individual model introspection
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
    


if __name__ == "__main__":
    test_pydantic_introspection()
