"""
FluidKit constants for runtime imports and code generation
"""

class FluidKitRuntime:
    """FluidKit runtime function and type names"""
    
    # TypeScript runtime exports
    API_RESULT_TYPE = "ApiResult"
    GET_BASE_URL_FN = "getBaseUrl"
    HANDLE_RESPONSE_FN = "handleResponse"
    
    # Runtime file locations
    RUNTIME_DIR = ".fluidkit"
    RUNTIME_FILE = "runtime.ts"
    
    @classmethod
    def get_all_imports(cls) -> list[str]:
        """Get all runtime imports for TypeScript"""
        return [cls.API_RESULT_TYPE, cls.GET_BASE_URL_FN, cls.HANDLE_RESPONSE_FN]


class GenerationPaths:
    """Standard paths for code generation"""
    
    FLUIDKIT_DIR = ".fluidkit"
    TYPESCRIPT_RUNTIME = "runtime.ts"
    
    # Future language runtimes
    PYTHON_RUNTIME = "runtime.py"
    JAVASCRIPT_RUNTIME = "runtime.js"

COMMON_TYPE_MAP = {
    "UUID": "string",
    "Decimal": "number",
    "datetime": "string",
    "date": "string", 
    "Path": "string",
    "EmailStr": "string",
    "HttpUrl": "string",
    "PaymentCardNumber": "string"
}
