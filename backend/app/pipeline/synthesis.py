import asyncio
from pathlib import Path
from typing import Any
import edge_tts

from ..config import DEFAULT_VOICE
from ..utils.file_utils import verify_file, format_bytes
from ..utils.logger import StageLogger


async def synthesize_speech_segments(
    segments: list[dict[str, Any]],
    out_dir: Path,
    voice: str = DEFAULT_VOICE,
    job_id: str | None = None,
) -> list[tuple[Path, float, float]]:
    """
    Synthesize English speech audio clips for each segment using edge-tts.
    Returns list of tuples: (audio_file_path, start_seconds, end_seconds).
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    StageLogger.info("SYNTHESIZE", f"Generating English speech with voice '{voice}'...", job_id)

    speech_pieces: list[tuple[Path, float, float]] = []
    total_bytes = 0

    for idx, seg in enumerate(segments):
        text = seg.get("translation", "").strip()
        if not text:
            continue

        target_file = out_dir / f"speech_{idx:04d}.mp3"
        start = float(seg.get("start", 0.0))
        end = float(seg.get("end", start + 2.0))

        try:
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(str(target_file))
            verify_file(target_file, f"Synthesized speech piece {idx+1}")
            size = target_file.stat().st_size
            total_bytes += size
            speech_pieces.append((target_file, start, end))
        except Exception as exc:
            StageLogger.error("SYNTHESIZE", f"Failed synthesizing segment {idx+1} ('{text[:30]}...'): {exc}", job_id)
            # If a single non-critical chunk fails, continue or raise if no pieces at all

    if not speech_pieces:
        raise RuntimeError(
            "Speech synthesis failed to generate any audio clips.|||"
            "Check internet connection for TTS service or try a different voice."
        )

    size_str = format_bytes(total_bytes)
    StageLogger.success(
        "SYNTHESIZE",
        f"Generated {len(speech_pieces)} speech clips ({size_str}) using '{voice}'",
        job_id,
    )
    return speech_pieces
