"""
FluidKit code generators - language-specific generation utilities
"""

# TypeScript generators
from .typescript import (
    generate_typescript_files as ts_files,
    generate_interface as ts_interface, 
    generate_fetch_wrapper as ts_client, 
    generate_imports_for_file as ts_imports,
)

# Future: Python client generators  
# from .python import (
#     generate_python_client as py_client,
#     generate_models as py_models,
#     generate_python_files as py_files,
# )

# Future: JavaScript generators
# from .javascript import (
#     generate_fetch_wrapper as js_client,
#     generate_javascript_files as js_files,
# )

# Future: Zod generators
# from .zod import (
#     generate_schema as zod_schema,
#     generate_zod_files as zod_files,
# )

__all__ = [
    # TypeScript generators
    'ts_files',        # Main pipeline
    'ts_interface',    # Individual interface generation
    'ts_client',       # Individual client generation  
    'ts_imports',      # Import statement generation
    
    # Future Python generators
    # 'py_client',
    # 'py_models', 
    # 'py_files',
    
    # Future JavaScript generators
    # 'js_client',
    # 'js_files',
    
    # Future Zod generators
    # 'zod_schema',
    # 'zod_files',
]
