import time
from typing import Any
from deep_translator import GoogleTranslator

from ..utils.logger import StageLogger


def translate_segments(
    segments: list[dict[str, Any]],
    source_language: str = "auto",
    job_id: str | None = None,
) -> list[dict[str, Any]]:
    """
    Translate transcribed speech segments into natural English.
    """
    if not segments:
        raise RuntimeError("No segments provided for translation.")

    StageLogger.info("TRANSLATE", f"Translating {len(segments)} segments to English...", job_id)

    # If already English, keep as-is or clean up
    is_already_english = source_language.lower() in ["en", "english"]
    if is_already_english:
        StageLogger.info("TRANSLATE", "Source language is already English; adapting transcript...", job_id)

    translator = GoogleTranslator(source="auto", target="en")
    translated_segments = []

    for idx, seg in enumerate(segments):
        original_text = seg.get("text", "").strip()
        if not original_text:
            continue

        if is_already_english:
            translated_text = original_text
        else:
            # Attempt translation with retry
            translated_text = original_text
            for attempt in range(3):
                try:
                    res = translator.translate(original_text)
                    if res and res.strip():
                        translated_text = res.strip()
                        break
                except Exception as exc:
                    if attempt < 2:
                        time.sleep(0.5)
                    else:
                        StageLogger.info("TRANSLATE", f"Segment {idx+1} fallback to original: {exc}", job_id)

        translated_segments.append({
            **seg,
            "translation": translated_text,
        })

    if not translated_segments:
        raise RuntimeError("Translation yielded no usable translated segments.|||Check network connectivity or try another video.")

    StageLogger.success("TRANSLATE", f"Successfully translated {len(translated_segments)} segments", job_id)
    return translated_segments
