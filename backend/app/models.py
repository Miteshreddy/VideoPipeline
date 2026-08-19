from enum import Enum
from typing import Any
from pydantic import BaseModel, Field, HttpUrl


class JobStatus(str, Enum):
    queued = "queued"
    downloading = "downloading"  # FETCH stage
    extracting = "extracting"    # EXTRACT stage
    transcribing = "transcribing" # TRANSCRIBE stage
    translating = "translating"  # TRANSLATE stage
    synthesizing = "synthesizing" # SYNTHESIZE stage
    remixing = "remixing"        # REMIX stage
    completed = "completed"
    failed = "failed"


class JobStage(str, Enum):
    fetch = "fetch"
    extract = "extract"
    transcribe = "transcribe"
    translate = "translate"
    synthesize = "synthesize"
    remix = "remix"


class DubRequest(BaseModel):
    url: str = Field(..., description="YouTube video URL")
    voice: str = Field(default="en-US-AriaNeural", description="Voice identifier for speech synthesis")
    whisper_model: str = Field(default="small", description="Whisper model: tiny, base, small, medium, large-v3")


class JobMetrics(BaseModel):
    segments: int = 0
    speech_segments: int = 0
    source_duration: float = 0.0
    download_size_bytes: int = 0
    output_size_bytes: int = 0
    processing_time_seconds: float = 0.0


class JobState(BaseModel):
    id: str
    status: JobStatus
    stage: str | None = None
    progress: int = 0
    message: str = "Waiting…"
    source_title: str | None = None
    detected_language: str | None = None
    duration_seconds: float | None = None
    output_file: str | None = None
    error: str | None = None
    suggested_action: str | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    ok: bool = True
    status: str = "healthy"
    service: str = "DubFlow API"
    version: str = "1.0.0"
    ffmpeg: dict[str, Any] = Field(default_factory=dict)
    whisper_model: str = "small"
