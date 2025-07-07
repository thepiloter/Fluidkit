"""
FastAPI Security Requirements Processing for FluidKit V2

Extracts security requirements from FastAPI Dependant for TypeScript JSDoc generation.
"""

from typing import List
from fluidkit.core.schema import SecurityRequirement


def extract_security_requirements(dependant) -> List[SecurityRequirement]:
    """
    Extract security requirements from FastAPI Dependant object.
    
    Converts FastAPI's rich SecurityRequirement objects into simplified
    SecurityRequirement objects suitable for TypeScript JSDoc generation.
    
    Args:
        dependant: FastAPI Dependant object from get_dependant()
        
    Returns:
        List of SecurityRequirement objects for RouteNode.security_requirements
    """
    requirements = []
    
    for req in dependant.security_requirements:
        try:
            security_scheme = req.security_scheme
            
            # Extract basic info
            scheme_name = security_scheme.scheme_name
            scheme_type = security_scheme.model.type_.value if hasattr(security_scheme.model, 'type_') else "unknown"
            description = getattr(security_scheme.model, 'description', None)
            scopes = list(req.scopes) if req.scopes else []
            
            # Extract location and parameter name for API key schemes
            location = None
            parameter_name = None
            
            if scheme_type == "apiKey":
                # API Key specific attributes
                location = getattr(security_scheme.model, 'in_', None)  # "header", "query", "cookie"
                parameter_name = getattr(security_scheme.model, 'name', None)  # "X-API-Key", "api_key"
            
            security_req = SecurityRequirement(
                scheme_name=scheme_name,
                scheme_type=scheme_type,
                description=description,
                scopes=scopes,
                location=location,
                parameter_name=parameter_name
            )
            requirements.append(security_req)
            
        except Exception as e:
            # If we can't extract security info, skip it with warning
            print(f"Warning: Failed to extract security requirement: {e}")
            continue
    
    return requirements
