"""
FastAPI Route Introspection for FluidKit V2

Main entry point for converting FastAPI routes to RouteNode objects using
runtime introspection instead of AST parsing.
"""

import typing
from typing import Optional

from fluidkit.core.schema import RouteNode
from fastapi.dependencies.utils import get_dependant
from fluidkit.core.type_conversion import python_type_to_field_annotation
from fluidkit.introspection.security import extract_security_requirements
from fluidkit.introspection.parameters import extract_parameters_from_dependant


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
        
        return_type = None
        if 'return' in type_hints:
            return_type = python_type_to_field_annotation(type_hints['return'])
        
        dependant = get_dependant(path=path, call=endpoint_function)
        parameters = extract_parameters_from_dependant(dependant, type_hints)
        security_requirements = extract_security_requirements(dependant)
        
        return RouteNode(
            name=name,
            path=path,
            methods=methods,
            location=location,
            docstring=docstring,
            parameters=parameters,
            return_type=return_type,
            security_requirements=security_requirements
        )
        
    except Exception as e:
        print(f"Warning: Failed to convert route {route.path}: {e}")
        return None
