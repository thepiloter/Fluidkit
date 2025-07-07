"""
Core FluidKit components - for advanced users and plugin developers
"""

# Main data structures
from .schema import (
    FluidKitApp,
    RouteNode, 
    ModelNode,
    Field,
    FieldAnnotation,
    FieldConstraints,
    ModuleLocation,
    
    # Enums
    BaseType,
    LanguageType,
    ContainerType, 
    ParameterType,
)

# Main integration function
from .integrator import integrate, introspect_only, generate_only

__all__ = [
    # Functions
    'integrate', 'introspect_only', 'generate_only',

    # Data structures
    'FluidKitApp', 'RouteNode', 'ModelNode', 'Field', 
    'FieldAnnotation', 'FieldConstraints', 'ModuleLocation',

    # Enums
    'LanguageType', 'BaseType', 'ContainerType', 'ParameterType',
]
