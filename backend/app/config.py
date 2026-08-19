import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from backend or root directory if present
BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = Path(__file__).resolve().parents[2]

if (ROOT_DIR / ".env").exists():
    load_dotenv(ROOT_DIR / ".env")
elif (BACKEND_DIR / ".env").exists():
    load_dotenv(BACKEND_DIR / ".env")
else:
    load_dotenv()

# App paths
WORKSPACE_DIR = Path(os.getenv("OUTPUT_DIR", BACKEND_DIR / "workspace")).resolve()
WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)

JOBS_DIR = WORKSPACE_DIR / "jobs"
JOBS_DIR.mkdir(parents=True, exist_ok=True)

# Settings
DEFAULT_WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")
DEFAULT_VOICE = os.getenv("DEFAULT_VOICE", "en-US-AriaNeural")

# YouTube authentication (optional)
YOUTUBE_COOKIES_FILE = os.getenv("YOUTUBE_COOKIES_FILE")
YOUTUBE_COOKIES_BROWSER = os.getenv("YOUTUBE_COOKIES_BROWSER")

# Server
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))
CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
