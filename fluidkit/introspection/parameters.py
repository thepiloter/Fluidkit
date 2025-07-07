"""
FastAPI Dependant Processing for FluidKit V2

Converts FastAPI's Dependant object (from get_dependant) into FluidKit Field objects
with proper parameter classification and constraint extraction.
"""

from typing import List, Dict, Any

from fluidkit.core.type_conversion import python_type_to_field_annotation
from fluidkit.core.schema import Field, FieldAnnotation, FieldConstraints, ParameterType, BaseType


def extract_parameters_from_dependant(dependant, type_hints: Dict[str, Any]) -> List[Field]:
    """
    Extract all parameters from FastAPI Dependant object.
    
    Args:
        dependant: FastAPI Dependant object from get_dependant()
        type_hints: Type hints from typing.get_type_hints(endpoint_function)
        
    Returns:
        List of Field objects for RouteNode.parameters
    """
    parameters = []
    
    # Path parameters
    for model_field in dependant.path_params:
        field = convert_model_field_to_field(model_field, ParameterType.PATH, type_hints)
        parameters.append(field)
    
    # Query parameters  
    for model_field in dependant.query_params:
        field = convert_model_field_to_field(model_field, ParameterType.QUERY, type_hints)
        parameters.append(field)
    
    # Header parameters
    for model_field in dependant.header_params:
        field = convert_model_field_to_field(model_field, ParameterType.HEADER, type_hints)
        parameters.append(field)
    
    # Cookie parameters
    for model_field in dependant.cookie_params:
        field = convert_model_field_to_field(model_field, ParameterType.COOKIE, type_hints)
        parameters.append(field)
    
    # Body parameters (need to inspect field_info type for BODY/FORM/FILE)
    for model_field in dependant.body_params:
        param_type = determine_body_parameter_type(model_field)
        field = convert_model_field_to_field(model_field, param_type, type_hints)
        parameters.append(field)
    
    return parameters


def convert_model_field_to_field(model_field, parameter_type: ParameterType, type_hints: Dict[str, Any]) -> Field:
    """
    Convert FastAPI ModelField to FluidKit Field.
    
    Args:
        model_field: FastAPI ModelField from dependant.*_params
        parameter_type: Our ParameterType classification
        type_hints: Function type hints for annotation extraction
        
    Returns:
        Field object ready for RouteNode
    """
    name = model_field.name
    
    # Get type annotation using our type conversion system
    py_type = type_hints.get(name)
    if py_type:
        annotation = python_type_to_field_annotation(py_type)
    else:
        # Fallback if type hint not found
        annotation = FieldAnnotation(base_type=BaseType.ANY)
    
    # Extract default value from field_info
    default_value = extract_default_from_field_info(model_field.field_info)
    
    # Build constraints with parameter type and FastAPI annotation
    constraints = FieldConstraints(
        parameter_type=parameter_type,
        fastapi_annotation=model_field.field_info.__class__.__name__
    )
    
    # Extract validation constraints from field_info
    extract_validation_constraints_from_field_info(model_field.field_info, constraints)
    
    # Extract description if available
    description = getattr(model_field.field_info, 'description', None)
    
    return Field(
        name=name,
        annotation=annotation,
        default=default_value,
        constraints=constraints,
        description=description
    )


def determine_body_parameter_type(model_field) -> ParameterType:
    """
    Determine if body parameter is BODY, FORM, or FILE based on field_info type.
    
    Args:
        model_field: FastAPI ModelField from dependant.body_params
        
    Returns:
        ParameterType for the specific body parameter type
    """
    field_info_type = model_field.field_info.__class__.__name__
    
    if field_info_type == "Body":
        return ParameterType.BODY
    elif field_info_type == "Form":
        return ParameterType.FORM
    elif field_info_type == "File":
        return ParameterType.FILE
    else:
        # Default to BODY for unknown body parameter types
        return ParameterType.BODY


def extract_default_from_field_info(field_info) -> Any:
    """
    Extract default value from FastAPI field_info object.
    
    Handles PydanticUndefined (required parameters) vs actual default values.
    
    Args:
        field_info: FastAPI parameter annotation object (Path, Query, Body, etc.)
        
    Returns:
        Default value or None if parameter is required
    """
    if hasattr(field_info, 'default'):
        default = field_info.default
        
        # Handle PydanticUndefined (means required parameter)
        if hasattr(default, '__class__'):
            class_name = default.__class__.__name__
            if 'Undefined' in class_name or 'PydanticUndefined' in class_name:
                return None
                
        return default
    
    return None


def extract_validation_constraints_from_field_info(field_info, constraints: FieldConstraints):
    """
    Extract validation constraints from FastAPI field_info into FieldConstraints.
    
    Handles ge, le, min_length, max_length, regex, etc. from FastAPI annotations.
    
    Args:
        field_info: FastAPI parameter annotation object
        constraints: FieldConstraints object to populate
    """
    # Numeric range constraints
    if hasattr(field_info, 'ge') and field_info.ge is not None:
        constraints.min_value = float(field_info.ge)
    
    if hasattr(field_info, 'gt') and field_info.gt is not None:
        # gt (greater than) is exclusive, store in custom for now
        constraints.min_value = float(field_info.gt)
        constraints.custom = constraints.custom or {}
        constraints.custom["min_exclusive"] = True
    
    if hasattr(field_info, 'le') and field_info.le is not None:
        constraints.max_value = float(field_info.le)
    
    if hasattr(field_info, 'lt') and field_info.lt is not None:
        # lt (less than) is exclusive, store in custom for now
        constraints.max_value = float(field_info.lt)
        constraints.custom = constraints.custom or {}
        constraints.custom["max_exclusive"] = True
    
    # String/array length constraints
    if hasattr(field_info, 'min_length') and field_info.min_length is not None:
        constraints.min_length = int(field_info.min_length)
    
    if hasattr(field_info, 'max_length') and field_info.max_length is not None:
        constraints.max_length = int(field_info.max_length)
    
    # Pattern validation
    if hasattr(field_info, 'regex') and field_info.regex is not None:
        constraints.regex_pattern = str(field_info.regex)
    
    # Deprecation flag
    if hasattr(field_info, 'deprecated') and field_info.deprecated is not None:
        constraints.deprecated = bool(field_info.deprecated)
    
    # Media type for file uploads
    if hasattr(field_info, 'media_type') and field_info.media_type is not None:
        constraints.media_type = str(field_info.media_type)
    
    # Store parameter alias if present
    if hasattr(field_info, 'alias') and field_info.alias is not None:
        constraints.custom = constraints.custom or {}
        constraints.custom["alias"] = field_info.alias
