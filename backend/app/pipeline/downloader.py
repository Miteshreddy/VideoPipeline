import os
import re
from pathlib import Path
from typing import Any
import yt_dlp
from yt_dlp.utils import DownloadError, ExtractorError

from ..config import YOUTUBE_COOKIES_BROWSER, YOUTUBE_COOKIES_FILE
from ..utils.file_utils import verify_file, format_bytes
from ..utils.logger import StageLogger

YOUTUBE_URL_REGEX = re.compile(
    r"^(https?://)?(www\.|m\.)?(youtube\.com/(watch\?v=|embed/|v/|shorts/)|youtu\.be/)([\w-]{11})",
    re.IGNORECASE,
)


def validate_youtube_url(url: str) -> str:
    """
    Validate that the given URL is a valid YouTube video link.
    Returns the sanitized URL string or raises ValueError.
    """
    cleaned = url.strip()
    if not cleaned:
        raise ValueError("Please provide a YouTube video URL.")

    match = YOUTUBE_URL_REGEX.search(cleaned)
    if not match:
        raise ValueError(
            "Invalid YouTube URL. Please enter a valid link (e.g., https://www.youtube.com/watch?v=... or https://youtu.be/...)."
        )
    return cleaned


def clean_ansi(text: str) -> str:
    """Strip ANSI escape sequences from error strings."""
    ansi_regex = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_regex.sub("", text).strip()


def classify_youtube_error(exc: Exception) -> tuple[str, str]:
    """
    Translate raw yt-dlp exceptions into a clean user-facing error message
    and an actionable suggested next step.
    Returns (friendly_error, suggested_action).
    """
    raw_msg = clean_ansi(str(exc))
    lower = raw_msg.lower()

    if "private video" in lower or "sign in if you've been granted access" in lower:
        return (
            "This YouTube video is set to private.",
            "Please paste a link to a public YouTube video.",
        )
    if "video unavailable" in lower or "not available" in lower or "deleted" in lower:
        return (
            "This YouTube video is unavailable or has been removed.",
            "Check that the video still exists on YouTube and is publicly accessible.",
        )
    if "confirm your age" in lower or "age-restricted" in lower or "requires authentication" in lower:
        return (
            "This video is age-restricted and requires user login.",
            "Try a publicly accessible video without age restrictions.",
        )
    if "not available in your country" in lower or "geo" in lower or "region" in lower:
        return (
            "This video is geo-restricted and not available in this region.",
            "Try a video available in your region or without geographic restrictions.",
        )
    if "too many requests" in lower or "429" in lower or "rate" in lower:
        return (
            "YouTube temporarily rate-limited automated requests.",
            "Wait a moment and try again, or try another video.",
        )
    if "timed out" in lower or "connection refused" in lower or "unreachable" in lower:
        return (
            "Network timeout while connecting to YouTube.",
            "Check your internet connection and try again.",
        )
    if "is not a valid url" in lower or "unsupported url" in lower:
        return (
            "The provided URL could not be recognized as a valid video.",
            "Verify the URL format (e.g. https://www.youtube.com/watch?v=...).",
        )

    # Generic clean error
    first_line = raw_msg.splitlines()[0] if raw_msg else "Unknown download error"
    # Remove 'ERROR: ' prefix if present
    if first_line.startswith("ERROR:"):
        first_line = first_line[6:].strip()
    return (
        f"Unable to download YouTube video: {first_line}",
        "Ensure the video is public and valid, then try again.",
    )


class CustomYTDLPLogger:
    """Silences noisy yt-dlp logs while forwarding errors to StageLogger."""
    def __init__(self, job_id: str | None = None):
        self.job_id = job_id

    def debug(self, msg: str):
        pass

    def info(self, msg: str):
        pass

    def warning(self, msg: str):
        pass

    def error(self, msg: str):
        clean_msg = clean_ansi(msg)
        StageLogger.error("FETCH", clean_msg, self.job_id)


def download_youtube_video(url: str, out_dir: Path, job_id: str | None = None) -> tuple[Path, dict[str, Any]]:
    """
    Download a YouTube video robustly with player-client fallbacks, format selection,
    and strict file verification.
    """
    sanitized_url = validate_youtube_url(url)
    out_dir.mkdir(parents=True, exist_ok=True)
    template = str(out_dir / "source.%(ext)s")

    StageLogger.info("FETCH", f"Starting YouTube download for {sanitized_url}", job_id)

    opts: dict[str, Any] = {
        "outtmpl": template,
        "format": "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
        "extractor_args": {
            "youtube": {
                # Fallback across modern YouTube clients to bypass app restrictions
                "player_client": ["android", "ios", "web", "mweb"]
            }
        },
        "noplaylist": True,
        "no_color": True,
        "logger": CustomYTDLPLogger(job_id),
        "socket_timeout": 30,
        "retries": 3,
        "overwrites": True,
    }

    # Optional cookie configuration
    if YOUTUBE_COOKIES_FILE and Path(YOUTUBE_COOKIES_FILE).exists():
        opts["cookiefile"] = str(Path(YOUTUBE_COOKIES_FILE).resolve())
        StageLogger.info("FETCH", f"Using cookies from file: {YOUTUBE_COOKIES_FILE}", job_id)
    elif YOUTUBE_COOKIES_BROWSER:
        opts["cookiesfrombrowser"] = (YOUTUBE_COOKIES_BROWSER,)
        StageLogger.info("FETCH", f"Using cookies from browser: {YOUTUBE_COOKIES_BROWSER}", job_id)

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            StageLogger.info("FETCH", "Extracting video metadata...", job_id)
            info = ydl.extract_info(sanitized_url, download=True)
            if not info:
                raise RuntimeError("yt-dlp returned empty metadata for the given URL.")

            title = info.get("title", "Untitled Video")
            duration = float(info.get("duration") or 0)
            StageLogger.info("FETCH", f"Metadata received: \"{title}\" ({duration:.1f}s)", job_id)

            # Locate the output file
            expected_path = Path(ydl.prepare_filename(info))
            if expected_path.exists():
                video_path = expected_path
            else:
                mp4_path = expected_path.with_suffix(".mp4")
                if mp4_path.exists():
                    video_path = mp4_path
                else:
                    # Scan directory for downloaded source video
                    candidates = list(out_dir.glob("source.*"))
                    if candidates:
                        video_path = candidates[0]
                    else:
                        raise RuntimeError(f"Expected download file '{expected_path.name}' was not found.")

            # Strict verification
            verify_file(video_path, "Downloaded video file")
            size_str = format_bytes(video_path.stat().st_size)
            StageLogger.success("FETCH", f"Video saved to {video_path.name} ({size_str})", job_id)

            return video_path, {
                "title": title,
                "duration": duration,
                "uploader": info.get("uploader", "Unknown"),
                "view_count": info.get("view_count", 0),
                "file_size": video_path.stat().st_size,
            }

    except (DownloadError, ExtractorError, Exception) as exc:
        friendly_err, suggested_action = classify_youtube_error(exc)
        StageLogger.error("FETCH", f"{friendly_err} [Technical: {exc}]", job_id)
        raise RuntimeError(f"{friendly_err}|||{suggested_action}") from exc
