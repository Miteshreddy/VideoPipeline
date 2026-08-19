import asyncio
import time
from pathlib import Path
from typing import Any, Callable

from .downloader import download_youtube_video, validate_youtube_url
from .audio_extractor import extract_audio_track
from .transcription import transcribe_audio
from .translation import translate_segments
from .synthesis import synthesize_speech_segments
from .remixer import remix_video
from ..utils.file_utils import clean_job_temp_files
from ..utils.logger import StageLogger

ProgressFn = Callable[[str, int, str], None]


async def run_dubbing_pipeline(
    job_dir: Path,
    url: str,
    voice: str,
    whisper_model: str,
    progress_callback: ProgressFn,
    job_id: str | None = None,
) -> dict[str, Any]:
    """
    Execute the complete end-to-end automated video dubbing pipeline.
    """
    start_time = time.time()
    job_dir.mkdir(parents=True, exist_ok=True)

    # 1. Validation & Fetch stage
    progress_callback("downloading", 10, "Connecting to YouTube and fetching video…")
    source_video, info = await asyncio.to_thread(
        download_youtube_video, url, job_dir, job_id
    )
    title = info.get("title", source_video.stem)
    duration = float(info.get("duration", 0.0))

    # 2. Extract Audio stage
    progress_callback("extracting", 26, "Extracting audio track for transcription…")
    extracted_audio = await asyncio.to_thread(
        extract_audio_track, source_video, job_dir, job_id
    )

    # 3. Transcribe stage
    progress_callback("transcribing", 38, "Transcribing spoken speech with Whisper…")
    segments, detected_language, duration_from_audio = await asyncio.to_thread(
        transcribe_audio, extracted_audio, whisper_model, job_id
    )
    total_duration = duration or duration_from_audio

    # 4. Translate stage
    progress_callback("translating", 56, f"Translating {len(segments)} segments to natural English…")
    translated_segments = await asyncio.to_thread(
        translate_segments, segments, detected_language, job_id
    )

    # 5. Synthesize stage
    progress_callback("synthesizing", 74, f"Synthesizing English speech with voice '{voice}'…")
    speech_pieces = await synthesize_speech_segments(
        translated_segments, job_dir, voice, job_id
    )

    # 6. Remix stage
    progress_callback("remixing", 88, "Replacing original audio and producing dubbed MP4…")
    final_output = await asyncio.to_thread(
        remix_video, source_video, speech_pieces, job_dir, total_duration, job_id
    )

    # Clean intermediate temporary speech files while keeping final MP4
    clean_job_temp_files(job_dir, final_output)

    elapsed_time = round(time.time() - start_time, 2)
    progress_callback("completed", 100, f"Dub completed successfully in {elapsed_time}s.")
    StageLogger.success("COMPLETE", f"Job finished in {elapsed_time}s. Output: {final_output.name}", job_id)

    return {
        "title": title,
        "language": detected_language,
        "duration": total_duration,
        "output": str(final_output),
        "segments": len(translated_segments),
        "speech_segments": len(speech_pieces),
        "processing_time": elapsed_time,
        "output_size": final_output.stat().st_size if final_output.exists() else 0,
    }
