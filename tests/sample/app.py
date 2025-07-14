from typing import Annotated
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware


# Create FastAPI app with comprehensive configuration
app = FastAPI(
    title="FluidKit Test E-commerce API",
    description="Complex test API for FluidKit with external types and nested models",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/api/openapi.json"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint with basic info"""
    return {
        "name": "FluidKit Test E-commerce API",
        "version": "1.0.0",
        "features": [
            "Complex Pydantic models",
            "External type integration", 
            "Nested model relationships",
            "Comprehensive validation",
            "Real-world e-commerce scenarios"
        ]
    }


def get_sys():
    return {"version": "1.0.0", "timestamp": "2024-01-01T00:00:00Z"}

GetSys = Annotated[dict, Depends(get_sys)]

@app.get("/health")
async def health_check(get_sys: GetSys):
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": "2024-01-01T00:00:00Z"}


# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)
