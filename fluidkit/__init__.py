"""
FluidKit - FastAPI to TypeScript/Python/etc. code generation
"""

from fluidkit.core.schema import LanguageType
from fluidkit.core.integrator import integrate, introspect_only, generate_only


__version__ = "2.0.0"


__all__ = [
    # Main functions
    'integrate',
    'introspect_only', 
    'generate_only',
    
    # Enums
    'LanguageType',
    
    # Version
    '__version__'
]
