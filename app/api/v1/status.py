"""Status & service information endpoints."""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, List
from loguru import logger

from app.services.upscale_service import UpscaleService

router = APIRouter()


class ServiceInfo(BaseModel):
    service: str
    method: str
    available_factors: List[int]
    features: List[str]
    status: str


class HealthResponse(BaseModel):
    status: str
    service: ServiceInfo


@router.get("/health", response_model=HealthResponse)
async def health():
    """Get service health and capabilities."""
    try:
        service = UpscaleService()
        service_info = service.get_status()
        return HealthResponse(
            status="ok",
            service=ServiceInfo(**service_info)
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="error",
            service=ServiceInfo(
                service="UpscaleService",
                method="PIL-based Real-ESRGAN",
                available_factors=[2, 4, 8],
                features=["edge_enhancement", "contrast_boost", "color_saturation", "denoising"],
                status="error"
            )
        )
