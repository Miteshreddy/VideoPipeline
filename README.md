# DubFlow — Automated Video Dubbing System

A robust full-stack web application and Python backend for automated YouTube video dubbing into English.

DubFlow accepts a YouTube link and handles the complete pipeline end-to-end:
1. **Fetch**: Validates YouTube URL and downloads source video via `yt-dlp` (with player-client fallbacks).
2. **Extract**: Extracts 16kHz mono PCM audio track via `ffmpeg`.
3. **Transcribe**: Transcribes spoken speech and auto-detects language using `faster-whisper`.
4. **Translate**: Translates speech segments into natural English using `deep-translator`.
5. **Synthesize**: Synthesizes natural English audio pieces using `edge-tts`.
6. **Remix**: Places audio at exact segment timestamps and replaces video audio via `ffmpeg` stream-copy.
7. **Download**: Exposes the finalized dubbed MP4 video for download.

---

## Quick Start (1-Click Launch)

### Option A: Double-Click Launcher (Windows Batch)
Simply double-click:
```text
start.bat
```
*(Or run `.\start.bat` in CMD / PowerShell)*

### Option B: PowerShell Launcher
```powershell
.\start.ps1
```

The launcher will automatically:
1. Check Python, Node.js, and FFmpeg prerequisites.
2. Initialize backend `venv` and install/verify dependencies.
3. Install frontend `node_modules` if missing.
4. Launch the FastAPI backend (`http://127.0.0.1:8000`).
5. Launch the Vite frontend dashboard (`http://localhost:5173`).
6. Automatically open your browser to the web app.

---

## Folder Structure

```text
idealabs-dubbing/
├── start.bat                    # 1-Click Windows Batch launcher
├── start.ps1                    # 1-Click PowerShell launcher
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI endpoints & CORS
│   │   ├── config.py            # Environment & path configuration
│   │   ├── models.py            # Pydantic data schemas
│   │   ├── job_manager.py       # Asynchronous job queue & progress tracker
│   │   ├── pipeline/
│   │   │   ├── __init__.py      # Pipeline orchestrator
│   │   │   ├── downloader.py    # yt-dlp downloader with client fallbacks
│   │   │   ├── audio_extractor.py # FFmpeg audio track extraction
│   │   │   ├── transcription.py # faster-whisper model caching & transcription
│   │   │   ├── translation.py   # deep-translator English adapter
│   │   │   ├── synthesis.py     # edge-tts speech generation
│   │   │   └── remixer.py       # FFmpeg timeline builder & muxer
│   │   └── utils/
│   │       ├── ffmpeg.py        # FFmpeg runner & system detection
│   │       ├── logger.py        # Structured stage logger ([FETCH], [REMIX], etc.)
│   │       └── file_utils.py    # Workspace management & cleanup
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.jsx              # Dashboard UI & state management
│   │   ├── main.jsx             # React entry point
│   │   └── styles.css           # Cinematic dark theme styles
│   ├── package.json
│   ├── vite.config.js
│   └── index.html
├── .env.example
└── README.md
```

---

## Prerequisites

1. **Python 3.10+**
2. **FFmpeg** installed and added to system `PATH` (Verify with `ffmpeg -version`)
3. **Node.js 18+** & npm

---

## Manual Execution (PowerShell)

### 1. Start Backend Server

```powershell
cd backend
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
*Health Check: `http://127.0.0.1:8000/api/health`*

### 2. Start Frontend Dashboard

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```
*Open in Browser: `http://localhost:5173`*

---

## Environment Configuration

Copy `.env.example` to `.env` in the root or backend folder to customize:

| Variable | Default | Description |
| :--- | :--- | :--- |
| `WHISPER_MODEL` | `small` | Faster-Whisper model (`tiny`, `base`, `small`, `medium`, `large-v3`) |
| `OUTPUT_DIR` | `workspace` | Directory for storing workspace jobs and output media |
| `DEFAULT_VOICE` | `en-US-AriaNeural` | Default Edge-TTS voice identifier |
| `YOUTUBE_COOKIES_FILE` | *(optional)* | Path to cookies.txt for authorized YouTube extraction |
| `YOUTUBE_COOKIES_BROWSER`| *(optional)* | Browser name (e.g. `chrome`, `firefox`) to extract cookies |
