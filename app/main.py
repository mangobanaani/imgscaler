"""Main FastAPI application."""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from .api.routes import router as api_router

# Create FastAPI app
app = FastAPI(
    title="AI Image Upscaler",
    description="Enhanced image upscaling service using Real-ESRGAN and TensorFlow Hub",
    version="1.0.0"
)

# Include API routes
app.include_router(api_router, prefix="/api")

# Mount static files (frontend)
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
app.mount("/static", StaticFiles(directory=os.path.join(frontend_dir, "src")), name="static")

@app.get("/")
async def root():
    """Serve the main frontend page."""
    index_path = os.path.join(frontend_dir, "index.html")
    return FileResponse(index_path)

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
