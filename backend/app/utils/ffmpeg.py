import shutil
import subprocess
from typing import Any


def get_ffmpeg_path() -> str | None:
    """Find the path to the ffmpeg executable in PATH or standard locations."""
    return shutil.which("ffmpeg")


def is_ffmpeg_available() -> bool:
    """Check if ffmpeg executable is available in PATH."""
    return get_ffmpeg_path() is not None


def get_ffmpeg_info() -> dict[str, Any]:
    """Retrieve FFmpeg version information and status."""
    path = get_ffmpeg_path()
    if not path:
        return {
            "available": False,
            "path": None,
            "version": None,
            "error": "FFmpeg executable not found in system PATH",
        }

    try:
        res = subprocess.run(
            [path, "-version"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        first_line = res.stdout.splitlines()[0] if res.stdout else "Unknown version"
        return {
            "available": True,
            "path": path,
            "version": first_line,
        }
    except Exception as exc:
        return {
            "available": False,
            "path": path,
            "version": None,
            "error": str(exc),
        }


def run_ffmpeg(args: list[str], timeout: int = 300) -> subprocess.CompletedProcess:
    """
    Run an FFmpeg command safely cross-platform.
    Raises RuntimeError with clean stderr description if FFmpeg fails.
    """
    ffmpeg_bin = get_ffmpeg_path()
    if not ffmpeg_bin:
        raise RuntimeError(
            "FFmpeg is required for video and audio processing but was not found in system PATH. "
            "Please install FFmpeg and make sure it is added to your PATH environment variable."
        )

    cmd = [ffmpeg_bin, *args]
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"FFmpeg operation timed out after {timeout} seconds")
    except Exception as exc:
        raise RuntimeError(f"Failed to execute FFmpeg process: {exc}")

    if result.returncode != 0:
        err_msg = result.stderr.strip()
        # Keep last few lines of stderr if verbose
        lines = [line.strip() for line in err_msg.splitlines() if line.strip()]
        relevant_err = "\n".join(lines[-5:]) if lines else "Unknown FFmpeg error"
        raise RuntimeError(f"FFmpeg failed with exit code {result.returncode}:\n{relevant_err}")

    return result
