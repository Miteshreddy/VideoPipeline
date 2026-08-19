import asyncio
import os
import re
import subprocess
from pathlib import Path
from typing import Callable

import edge_tts
import yt_dlp
from deep_translator import GoogleTranslator
from faster_whisper import WhisperModel

ProgressFn = Callable[[str, int, str], None]


def safe_name(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9._-]+", "_", value).strip("._")
    return value[:100] or "video"


def download_video(url: str, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    template = str(out_dir / "source.%(ext)s")
    opts = {
        "outtmpl": template,
        "format": "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/b",
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        path = Path(ydl.prepare_filename(info))
        if path.suffix.lower() != ".mp4":
            merged = path.with_suffix(".mp4")
            if merged.exists():
                path = merged
        return path, info


def transcribe(video: Path, model_name: str, model_cache: dict[str, WhisperModel]):
    if model_name not in model_cache:
        model_cache[model_name] = WhisperModel(model_name, device="auto", compute_type="int8")
    model = model_cache[model_name]
    segments, info = model.transcribe(str(video), vad_filter=True, beam_size=5)
    data = [
        {"start": float(s.start), "end": float(s.end), "text": s.text.strip()}
        for s in segments
        if s.text.strip()
    ]
    return data, info.language, float(info.duration or 0)


def translate_segments(segments: list[dict]) -> list[dict]:
    translator = GoogleTranslator(source="auto", target="en")
    output = []
    for seg in segments:
        try:
            text = translator.translate(seg["text"])
        except Exception:
            text = seg["text"]
        output.append({**seg, "translation": text.strip()})
    return output


async def synthesize(segments: list[dict], out_dir: Path, voice: str, total_duration: float):
    pieces = []
    for idx, seg in enumerate(segments):
        text = seg["translation"]
        if not text:
            continue
        target = out_dir / f"speech_{idx:04d}.mp3"
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(str(target))
        pieces.append((target, seg["start"], seg["end"]))
    return pieces


def remix(video: Path, speech_pieces: list[tuple[Path, float, float]], out_dir: Path, total_duration: float) -> Path:
    # Build a silent base, then place each synthesized speech clip at the original
    # segment start timestamp. The original visuals are stream-copied.
    timeline = out_dir / "timeline.wav"
    output = out_dir / f"dubbed_{safe_name(video.stem)}.mp4"
    if not speech_pieces:
        raise RuntimeError("No speech segments were generated.")

    inputs = []
    filters = []
    for idx, (piece, start, _) in enumerate(speech_pieces):
        inputs += ["-i", str(piece)]
        delay = max(0, int(start * 1000))
        filters.append(f"[{idx}:a]adelay={delay}|{delay},aresample=48000[a{idx}]")

    mix_inputs = "".join(f"[a{idx}]" for idx in range(len(speech_pieces)))
    filters.append(f"{mix_inputs}amix=inputs={len(speech_pieces)}:duration=longest:normalize=0[aout]")

    cmd = ["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(filters), "-map", "[aout]", "-t", str(total_duration), "-ar", "48000", "-ac", "2", str(timeline)]
    subprocess.run(cmd, check=True, capture_output=True)

    # Prefer stream-copy for video to keep the original visuals untouched.
    cmd2 = [
        "ffmpeg", "-y", "-i", str(video), "-i", str(timeline),
        "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-shortest", str(output)
    ]
    subprocess.run(cmd2, check=True, capture_output=True)
    return output


async def run_pipeline(job_dir: Path, url: str, voice: str, whisper_model: str, progress: ProgressFn):
    job_dir.mkdir(parents=True, exist_ok=True)
    model_cache: dict[str, WhisperModel] = {}

    progress("downloading", 12, "Downloading source video…")
    source, info = download_video(url, job_dir)
    title = info.get("title") or source.stem
    duration = float(info.get("duration") or 0)

    progress("transcribing", 30, "Transcribing speech with Whisper…")
    segments, language, duration_from_whisper = await asyncio.to_thread(transcribe, source, whisper_model, model_cache)
    duration = duration or duration_from_whisper

    progress("translating", 52, "Translating speech into natural English…")
    translated = await asyncio.to_thread(translate_segments, segments)

    progress("synthesizing", 72, "Generating natural English speech…")
    speech = await synthesize(translated, job_dir, voice, duration)

    progress("remixing", 88, "Replacing the original audio track…")
    output = await asyncio.to_thread(remix, source, speech, job_dir, duration)

    progress("completed", 100, "Dub completed successfully.")
    return {
        "title": title,
        "language": language,
        "duration": duration,
        "output": str(output),
        "segments": len(translated),
        "speech_segments": len(speech),
    }
