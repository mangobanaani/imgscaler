"""WebSocket endpoint for real-time progress updates."""
from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger
import json
import asyncio
from typing import Dict, Set

from app.services.job_queue import job_queue

router = APIRouter()

# Active WebSocket connections per job
active_connections: Dict[str, Set[WebSocket]] = {}


@router.websocket("/ws/job/{job_id}")
async def websocket_job_progress(websocket: WebSocket, job_id: str):
    """WebSocket endpoint for real-time job progress updates."""
    await websocket.accept()
    
    # Register connection
    if job_id not in active_connections:
        active_connections[job_id] = set()
    active_connections[job_id].add(websocket)
    
    logger.info(f"WebSocket connected for job {job_id}")
    
    try:
        while True:
            # Send current job status
            job = job_queue.get(job_id)
            if job:
                status_data = {
                    "job_id": job.id,
                    "status": job.status,
                    "progress": job.progress,
                    "error": job.error
                }
                await websocket.send_text(json.dumps(status_data))
                
                # If job is done, close connection
                if job.status in ["done", "error"]:
                    break
            else:
                await websocket.send_text(json.dumps({"error": "Job not found"}))
                break
                
            await asyncio.sleep(0.5)  # Update every 500ms
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for job {job_id}")
    finally:
        # Cleanup connection
        if job_id in active_connections:
            active_connections[job_id].discard(websocket)
            if not active_connections[job_id]:
                del active_connections[job_id]


async def broadcast_job_update(job_id: str, status_data: dict):
    """Broadcast job status update to all connected WebSockets."""
    if job_id in active_connections:
        disconnected = []
        for websocket in active_connections[job_id]:
            try:
                await websocket.send_text(json.dumps(status_data))
            except Exception:
                disconnected.append(websocket)
        
        # Remove disconnected sockets
        for ws in disconnected:
            active_connections[job_id].discard(ws)
