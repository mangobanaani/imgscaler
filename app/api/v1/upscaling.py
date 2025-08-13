"""Upscaling endpoints."""
from __future__ import annotations

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from loguru import logger
from PIL import Image
import io

from app.services.upscale_service import UpscaleService, UpscaleRequest
from app.services.job_queue import job_queue, JobStatus
import threading

# Try to import TensorFlow Hub service
try:
    from app.services.tfhub_upscale_service import TFHubUpscaleService, TFHubUpscaleRequest
    TFHUB_AVAILABLE = True
    tfhub_service = TFHubUpscaleService()
    logger.info("TensorFlow Hub service available")
except ImportError as e:
    TFHUB_AVAILABLE = False
    tfhub_service = None
    logger.info(f"TensorFlow Hub service not available: {e}")

router = APIRouter()
service = UpscaleService()


class UpscaleResponse(BaseModel):
    width: int
    height: int
    mode: str
    format: str | None


class JobCreateResponse(BaseModel):
    job_id: str
    status: JobStatus


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    progress: float
    error: str | None = None


@router.post("/process", response_model=UpscaleResponse)
async def upscale_image(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    factor: int = 2,
    denoise: bool = False,
):
    if factor not in (2, 4, 8):
        raise HTTPException(status_code=400, detail="factor must be 2, 4, or 8")
    try:
        contents = await file.read()
        img = Image.open(io.BytesIO(contents))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="Invalid image file") from exc

    req = UpscaleRequest(image=img, factor=factor, denoise=denoise)

    # For now, synchronous processing (could queue/background)
    upscaled = service.upscale(req)

    buf = io.BytesIO()
    out_format = (img.format or "PNG").upper()
    upscaled.save(buf, format=out_format)
    buf.seek(0)

    background_tasks.add_task(logger.info, "Processed upscale request")

    return UpscaleResponse(
        width=upscaled.width, height=upscaled.height, mode=upscaled.mode, format=out_format
    )


@router.post("/download")
async def upscale_and_download(
    file: UploadFile = File(...),
    factor: int = 2,
    denoise: bool = False,
):
    contents = await file.read()
    try:
        img = Image.open(io.BytesIO(contents))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="Invalid image file") from exc
    req = UpscaleRequest(image=img, factor=factor, denoise=denoise)
    upscaled = service.upscale(req)
    buf = io.BytesIO()
    out_format = (img.format or "PNG").upper()
    upscaled.save(buf, format=out_format)
    buf.seek(0)
    return StreamingResponse(buf, media_type=f"image/{out_format.lower()}")


def _process_job(job_id: str, data: bytes, factor: int, denoise: bool, use_tfhub: bool = False) -> None:
    logger.info(f"Processing job {job_id} with factor={factor}, denoise={denoise}, use_tfhub={use_tfhub}")
    job_queue.update(job_id, status=JobStatus.processing, progress=0.05)
    try:
        img = Image.open(io.BytesIO(data))
        logger.info(f"Original image size: {img.size}")
        
        if use_tfhub and TFHUB_AVAILABLE:
            # Use TensorFlow Hub ESRGAN (always 4x)
            req = TFHubUpscaleRequest(image=img, factor=4, denoise=denoise)
            upscaled = tfhub_service.upscale(req)
        else:
            # Use PIL-based Real-ESRGAN
            req = UpscaleRequest(image=img, factor=factor, denoise=denoise)
            upscaled = service.upscale(req)
        
        logger.info(f"Upscaled image size: {upscaled.size}")
        buf = io.BytesIO()
        out_format = (img.format or "PNG").upper()
        upscaled.save(buf, format=out_format)
        job_queue.update(
            job_id,
            status=JobStatus.done,
            progress=1.0,
            result_bytes=buf.getvalue(),
            content_type=f"image/{out_format.lower()}",
        )
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Job {job_id} failed: {exc}")
        job_queue.update(job_id, status=JobStatus.error, error=str(exc))


@router.post("/job", response_model=JobCreateResponse)
async def create_upscale_job(
    file: UploadFile = File(...), 
    factor: int = 2, 
    denoise: bool = False,
    use_tfhub: bool = False
):
    logger.info(f"Creating upscale job with factor={factor}, denoise={denoise}, use_tfhub={use_tfhub}")
    
    if use_tfhub:
        if not TFHUB_AVAILABLE:
            raise HTTPException(status_code=400, detail="TensorFlow Hub not available. Install with: poetry install --with ml")
        # TensorFlow Hub ESRGAN is always 4x
        factor = 4
    else:
        if factor not in (2, 4, 8):
            raise HTTPException(status_code=400, detail="factor must be 2, 4, or 8 for PIL mode")
    
    data = await file.read()
    job = job_queue.create()
    logger.info(f"Created job {job.id}, starting processing thread")
    threading.Thread(
        target=_process_job, 
        args=(job.id, data, factor, denoise, use_tfhub), 
        daemon=True
    ).start()
    return JobCreateResponse(job_id=job.id, status=job.status)


@router.get("/job/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    job = job_queue.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return JobStatusResponse(
        job_id=job.id, status=job.status, progress=job.progress, error=job.error
    )


@router.get("/job/{job_id}/result")
async def get_job_result(job_id: str):
    job = job_queue.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    if job.status != JobStatus.done:
        return JSONResponse(status_code=409, content={"detail": "job not completed"})
    return StreamingResponse(io.BytesIO(job.result_bytes), media_type=job.content_type)
