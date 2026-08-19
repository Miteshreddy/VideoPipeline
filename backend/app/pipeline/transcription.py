import os
import threading
from pathlib import Path
from typing import Any
from faster_whisper import WhisperModel

from ..utils.logger import StageLogger

# Global thread-safe model cache
_MODEL_CACHE: dict[str, WhisperModel] = {}
_CACHE_LOCK = threading.Lock()


def get_whisper_model(model_name: str = "small", job_id: str | None = None) -> WhisperModel:
    """
    Retrieve or load a cached faster-whisper model singleton.
    Defaults to CPU with int8 quantization for maximum cross-platform Windows stability.
    """
    with _CACHE_LOCK:
        if model_name not in _MODEL_CACHE:
            StageLogger.info("TRANSCRIBE", f"Loading Whisper model '{model_name}'...", job_id)
            device = os.getenv("WHISPER_DEVICE", "cpu")
            compute_type = os.getenv("WHISPER_COMPUTE_TYPE", "int8")

            try:
                model = WhisperModel(model_name, device=device, compute_type=compute_type)
            except Exception as exc:
                StageLogger.info("TRANSCRIBE", f"Failed loading on {device} ({exc}); falling back to CPU int8", job_id)
                model = WhisperModel(model_name, device="cpu", compute_type="int8")

            _MODEL_CACHE[model_name] = model
            StageLogger.info("TRANSCRIBE", f"Whisper model '{model_name}' ready (device: {model.model.device})", job_id)
        return _MODEL_CACHE[model_name]


def transcribe_audio(
    audio_path: Path,
    model_name: str = "small",
    job_id: str | None = None,
) -> tuple[list[dict[str, Any]], str, float]:
    """
    Transcribe an audio file using faster-whisper.
    Returns (segments, detected_language, duration).
    """
    StageLogger.info("TRANSCRIBE", f"Starting speech transcription with model '{model_name}'...", job_id)

    try:
        model = get_whisper_model(model_name, job_id)
        # Use Voice Activity Detection (VAD) filter and beam search
        segments_iter, info = model.transcribe(
            str(audio_path),
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=400),
            beam_size=5,
        )

        detected_lang = info.language or "unknown"
        lang_prob = f"{info.language_probability * 100:.1f}%" if info.language_probability else "N/A"
        duration = float(info.duration or 0.0)

        StageLogger.info(
            "TRANSCRIBE",
            f"Detected language: '{detected_lang}' ({lang_prob} confidence), Duration: {duration:.1f}s",
            job_id,
        )

        segments = []
        for s in segments_iter:
            text = s.text.strip()
            if text:
                segments.append({
                    "start": round(float(s.start), 2),
                    "end": round(float(s.end), 2),
                    "text": text,
                })

        if not segments:
            raise RuntimeError(
                "No spoken dialogue was detected in the video audio track to translate.|||"
                "Try selecting a video that contains clear spoken speech."
            )

        StageLogger.success(
            "TRANSCRIBE",
            f"Transcribed {len(segments)} speech segments in '{detected_lang}'",
            job_id,
        )
        return segments, detected_lang, duration

    except Exception as exc:
        StageLogger.error("TRANSCRIBE", f"Transcription failed: {exc}", job_id)
        raise
