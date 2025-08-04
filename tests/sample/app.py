from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="FluidKit Test API",
    description="Test API for FluidKit features",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"name": "FluidKit Test API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

import fluidkit
fluidkit.integrate(app, enable_fullstack=True)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
