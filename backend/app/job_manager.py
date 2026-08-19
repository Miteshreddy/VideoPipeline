import asyncio
import shutil
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from .config import JOBS_DIR
from .models import DubRequest, JobState, JobStatus
from .pipeline import run_dubbing_pipeline
from .utils.logger import StageLogger


class JobManager:
    """Manages background dubbing jobs, lifecycle state, and worker execution."""

    def __init__(self):
        self._jobs: dict[str, JobState] = {}
        self._executor = ThreadPoolExecutor(max_workers=3)

    def get_job(self, job_id: str) -> JobState | None:
        return self._jobs.get(job_id)

    def create_job(self, request: DubRequest) -> JobState:
        job_id = uuid.uuid4().hex[:12]
        state = JobState(
            id=job_id,
            status=JobStatus.queued,
            stage="queued",
            progress=2,
            message="Queued for processing…",
        )
        self._jobs[job_id] = state
        # Launch background processing task
        asyncio.create_task(self._run_job(job_id, request))
        return state

    def update_job_progress(self, job_id: str, status: str, progress: int, message: str):
        job = self._jobs.get(job_id)
        if not job:
            return
        job.status = JobStatus(status)
        job.progress = progress
        job.message = message
        # Determine active stage
        if status in ["downloading", "extracting"]:
            job.stage = "fetch"
        elif status == "transcribing":
            job.stage = "transcribe"
        elif status == "translating":
            job.stage = "translate"
        elif status == "synthesizing":
            job.stage = "synthesize"
        elif status == "remixing":
            job.stage = "remix"
        elif status in ["completed", "failed"]:
            job.stage = status

    async def _run_job(self, job_id: str, request: DubRequest):
        job_dir = JOBS_DIR / job_id
        job_dir.mkdir(parents=True, exist_ok=True)

        try:
            result = await run_dubbing_pipeline(
                job_dir=job_dir,
                url=request.url,
                voice=request.voice,
                whisper_model=request.whisper_model,
                progress_callback=lambda st, pr, msg: self.update_job_progress(job_id, st, pr, msg),
                job_id=job_id,
            )

            job = self._jobs.get(job_id)
            if job:
                job.source_title = result["title"]
                job.detected_language = result["language"]
                job.duration_seconds = result["duration"]
                job.output_file = result["output"]
                job.metrics = {
                    "segments": result["segments"],
                    "speech_segments": result["speech_segments"],
                    "processing_time_seconds": result["processing_time"],
                    "output_size_bytes": result["output_size"],
                }

        except Exception as exc:
            raw_err = str(exc)
            friendly_err = raw_err
            suggested_action = "Please check the video URL and try again."

            if "|||" in raw_err:
                parts = raw_err.split("|||", 1)
                friendly_err = parts[0].strip()
                suggested_action = parts[1].strip()

            job = self._jobs.get(job_id)
            if job:
                job.status = JobStatus.failed
                job.message = "Processing stopped due to an error."
                job.error = friendly_err
                job.suggested_action = suggested_action
            StageLogger.error("JOB", f"Job failed: {friendly_err}", job_id)

    def delete_job(self, job_id: str) -> bool:
        job = self._jobs.pop(job_id, None)
        if not job:
            return False
        job_dir = JOBS_DIR / job_id
        shutil.rmtree(job_dir, ignore_errors=True)
        return True


# Global manager singleton
job_manager = JobManager()
