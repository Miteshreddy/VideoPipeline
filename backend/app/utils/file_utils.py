import re
import shutil
from pathlib import Path
from ..config import JOBS_DIR


def safe_name(value: str) -> str:
    """Sanitize string for safe filenames across Windows and Unix."""
    # Replace invalid Windows and Unix filename characters
    value = re.sub(r'[\\/*?:"<>|]', '_', value)
    value = re.sub(r'[\s_]+', '_', value).strip('._')
    return value[:80] or "video"


def get_job_dir(job_id: str) -> Path:
    """Get the isolated working directory for a given job."""
    path = JOBS_DIR / job_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def verify_file(file_path: Path, description: str = "Output file") -> None:
    """
    Verify that a file exists and has non-zero size.
    Raises RuntimeError if file is missing or empty.
    """
    if not file_path.exists():
        raise RuntimeError(f"{description} was not created: '{file_path.name}' does not exist.")
    if file_path.stat().st_size == 0:
        raise RuntimeError(f"{description} is empty (0 bytes): '{file_path.name}'.")


def format_bytes(size: int) -> str:
    """Format bytes to human readable string (KB, MB, GB)."""
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    elif size < 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    else:
        return f"{size / (1024 * 1024 * 1024):.2f} GB"


def clean_job_temp_files(job_dir: Path, final_output_file: Path | None = None) -> None:
    """
    Clean intermediate scratch files (speech_*.mp3, temp.wav, etc.) while preserving
    the final dubbed MP4 and metadata.
    """
    if not job_dir.exists():
        return

    for item in job_dir.iterdir():
        if item.is_file():
            # Keep final output file and info.json
            if final_output_file and item.resolve() == final_output_file.resolve():
                continue
            if item.suffix.lower() == ".json":
                continue
            # Remove intermediate speech mp3s, timeline wav, extracted audio
            if item.name.startswith("speech_") or item.suffix.lower() in [".wav", ".m4a", ".tmp"]:
                try:
                    item.unlink(missing_ok=True)
                except Exception:
                    pass
