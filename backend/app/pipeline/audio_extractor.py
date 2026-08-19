from pathlib import Path
from ..utils.ffmpeg import run_ffmpeg
from ..utils.file_utils import verify_file, format_bytes
from ..utils.logger import StageLogger


def extract_audio_track(video_path: Path, out_dir: Path, job_id: str | None = None) -> Path:
    """
    Extract a clean 16kHz mono WAV audio track from the video for Whisper transcription.
    """
    StageLogger.info("EXTRACT", f"Extracting audio track from {video_path.name}...", job_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    audio_path = out_dir / "extracted_audio.wav"

    # FFmpeg args: -vn (no video), -acodec pcm_s16le (WAV PCM), -ar 16000 (16kHz), -ac 1 (mono)
    args = [
        "-y",
        "-i", str(video_path),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        str(audio_path),
    ]

    try:
        run_ffmpeg(args, timeout=120)
        verify_file(audio_path, "Extracted audio file")
        size_str = format_bytes(audio_path.stat().st_size)
        StageLogger.success("EXTRACT", f"Audio track extracted ({size_str})", job_id)
        return audio_path
    except Exception as exc:
        StageLogger.error("EXTRACT", f"Failed to extract audio track: {exc}", job_id)
        raise RuntimeError(f"Audio extraction failed: {exc}") from exc
