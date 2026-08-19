import sys
from datetime import datetime


class StageLogger:
    """Structured stage logger that prints formatted, clean logs to terminal."""

    @staticmethod
    def _timestamp() -> str:
        return datetime.now().strftime("%H:%M:%S")

    @classmethod
    def log(cls, stage: str, message: str, job_id: str | None = None):
        prefix = f"[{stage.upper():<10}]"
        job_tag = f"({job_id}) " if job_id else ""
        print(f"{cls._timestamp()} {prefix} {job_tag}{message}", flush=True)

    @classmethod
    def info(cls, stage: str, message: str, job_id: str | None = None):
        cls.log(stage, message, job_id)

    @classmethod
    def error(cls, stage: str, message: str, job_id: str | None = None):
        prefix = f"[{stage.upper():<10}]"
        job_tag = f"({job_id}) " if job_id else ""
        print(f"{cls._timestamp()} {prefix} {job_tag}FAILED: {message}", file=sys.stderr, flush=True)

    @classmethod
    def success(cls, stage: str, message: str, job_id: str | None = None):
        prefix = f"[{stage.upper():<10}]"
        job_tag = f"({job_id}) " if job_id else ""
        print(f"{cls._timestamp()} {prefix} {job_tag}COMPLETE: {message}", flush=True)
