"""API route definitions (aggregate)."""
from fastapi import APIRouter

from .v1 import upscaling, websocket, status

router = APIRouter()
router.include_router(upscaling.router, prefix="/v1/upscale", tags=["upscale"])
router.include_router(websocket.router, prefix="/v1", tags=["websocket"])
router.include_router(status.router, prefix="/v1", tags=["status"])
