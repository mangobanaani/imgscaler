"""Simple in-memory job queue for async upscaling.

This is a lightweight placeholder. For production, replace with Redis / Celery / RQ.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional
from uuid import uuid4
from threading import Lock


class JobStatus(str, Enum):
    queued = "queued"
    processing = "processing"
    done = "done"
    error = "error"


@dataclass
class UpscaleJob:
    id: str
    status: JobStatus = JobStatus.queued
    progress: float = 0.0  # 0..1
    error: Optional[str] = None
    result_bytes: Optional[bytes] = None
    content_type: Optional[str] = None


class JobQueue:
    def __init__(self) -> None:
        self._jobs: Dict[str, UpscaleJob] = {}
        self._lock = Lock()

    def create(self) -> UpscaleJob:
        job = UpscaleJob(id=uuid4().hex)
        with self._lock:
            self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> Optional[UpscaleJob]:
        return self._jobs.get(job_id)

    def update(self, job_id: str, **kwargs) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            for k, v in kwargs.items():
                setattr(job, k, v)


job_queue = JobQueue()
