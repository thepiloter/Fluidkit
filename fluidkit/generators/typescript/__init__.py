"""
TypeScript code generation for FluidKit
"""

# Main pipeline function
from .pipeline import generate_typescript_files

# Individual generators for advanced users
from .interfaces import generate_interface
from .clients import generate_fetch_wrapper
from .imports import generate_imports_for_file, ImportContext

__all__ = [
    # Main function
    'generate_typescript_files',
    
    # Individual generators
    'generate_interface',
    'generate_fetch_wrapper', 
    'generate_imports_for_file',
    
    # Utilities
    'ImportContext'
]
