from pathlib import Path
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from .config import CORS_ORIGINS, DEFAULT_WHISPER_MODEL
from .job_manager import job_manager
from .models import DubRequest, HealthResponse, JobState
from .pipeline.downloader import validate_youtube_url
from .utils.ffmpeg import get_ffmpeg_info


app = FastAPI(
    title="DubFlow API",
    description="Automated Video Dubbing System API",
    version="1.0.0",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint providing status of API, FFmpeg, and model configuration."""
    ffmpeg_info = get_ffmpeg_info()
    return HealthResponse(
        ok=ffmpeg_info.get("available", False),
        status="healthy" if ffmpeg_info.get("available") else "degraded",
        service="DubFlow API",
        version="1.0.0",
        ffmpeg=ffmpeg_info,
        whisper_model=DEFAULT_WHISPER_MODEL,
    )


@app.post("/api/jobs", response_model=JobState, status_code=status.HTTP_202_ACCEPTED)
async def create_dubbing_job(request: DubRequest):
    """Validate YouTube URL and start asynchronous video dubbing pipeline."""
    try:
        validated_url = validate_youtube_url(request.url)
        request.url = validated_url
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(val_err),
        )

    job_state = job_manager.create_job(request)
    return job_state


@app.get("/api/jobs/{job_id}", response_model=JobState)
async def get_job_status(job_id: str):
    """Retrieve current progress, stage, and metadata for a dubbing job."""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


@app.get("/api/jobs/{job_id}/download")
async def download_dubbed_video(job_id: str):
    """Download the finalized dubbed MP4 video."""
    job = job_manager.get_job(job_id)
    if not job or not job.output_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dubbed output video is not available yet.",
        )

    output_path = Path(job.output_file)
    if not output_path.exists() or output_path.stat().st_size == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dubbed output video file was not found on server.",
        )

    clean_filename = f"{output_path.stem}.mp4"
    return FileResponse(
        path=output_path,
        media_type="video/mp4",
        filename=clean_filename,
        headers={
            "Content-Disposition": f'attachment; filename="{clean_filename}"',
            "Accept-Ranges": "bytes",
        },
    )


@app.delete("/api/jobs/{job_id}")
async def delete_dubbing_job(job_id: str):
    """Cancel or remove a dubbing job and clean its working directory."""
    success = job_manager.delete_job(job_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return {"ok": True, "message": f"Job {job_id} deleted successfully."}
