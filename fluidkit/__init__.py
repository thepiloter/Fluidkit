"""
FluidKit - Automatic TypeScript client code generation for FastAPI
"""

def _check_dependencies():
    """Check for required dependencies"""
    missing = []
    
    try:
        import fastapi
    except ImportError:
        missing.append("fastapi")
    
    try:
        import pydantic
    except ImportError:
        missing.append("pydantic")
    
    if missing:
        deps = " and ".join(missing)
        raise ImportError(
            f"FluidKit requires {deps} to be installed.\n"
            f"Install with: pip install {' '.join(missing)}\n"
            f"FluidKit works with your existing {deps} versions."
        )

# Check dependencies on import
_check_dependencies()

# Import main API only after dependency check
from .core.config import get_version
from .core.schema import LanguageType
from .core.integrator import integrate, introspect_only, generate_only

__version__ = get_version()

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
