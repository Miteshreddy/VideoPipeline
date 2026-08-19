from pathlib import Path
from ..utils.ffmpeg import run_ffmpeg
from ..utils.file_utils import safe_name, verify_file, format_bytes
from ..utils.logger import StageLogger


def remix_video(
    video_path: Path,
    speech_pieces: list[tuple[Path, float, float]],
    out_dir: Path,
    total_duration: float = 0.0,
    job_id: str | None = None,
) -> Path:
    """
    Replace the original video's audio track with the synthesized English audio pieces
    placed at their corresponding timestamps. Uses stream-copy for video whenever possible.
    """
    if not speech_pieces:
        raise RuntimeError("No synthesized speech pieces were provided for remixing.")

    out_dir.mkdir(parents=True, exist_ok=True)
    StageLogger.info("REMIX", f"Building audio timeline for {len(speech_pieces)} speech segments...", job_id)

    timeline_wav = out_dir / "timeline.wav"
    output_mp4 = out_dir / f"dubbed_{safe_name(video_path.stem)}.mp4"

    # Step 1: Build filter graph for placing each piece at its timestamp
    filter_script = out_dir / "filter_complex.txt"
    inputs: list[str] = []
    filter_lines: list[str] = []

    for idx, (piece_path, start_time, _) in enumerate(speech_pieces):
        inputs.extend(["-i", str(piece_path)])
        delay_ms = max(0, int(start_time * 1000))
        filter_lines.append(f"[{idx}:a]adelay={delay_ms}|{delay_ms},aresample=48000[a{idx}];")

    if len(speech_pieces) == 1:
        # No amix needed for single input
        filter_lines[-1] = f"[0:a]adelay={max(0, int(speech_pieces[0][1] * 1000))}|{max(0, int(speech_pieces[0][1] * 1000))},aresample=48000[aout]"
    else:
        mix_inputs = "".join(f"[a{i}]" for i in range(len(speech_pieces)))
        filter_lines.append(f"{mix_inputs}amix=inputs={len(speech_pieces)}:duration=longest:normalize=0[aout]")

    filter_script.write_text("\n".join(filter_lines), encoding="utf-8")

    # Render combined timeline audio track
    timeline_cmd = [
        "-y",
        *inputs,
        "-filter_complex_script", str(filter_script),
        "-map", "[aout]",
        "-ar", "48000",
        "-ac", "2",
        str(timeline_wav),
    ]

    try:
        run_ffmpeg(timeline_cmd, timeout=300)
        verify_file(timeline_wav, "Audio timeline file")
    except Exception as exc:
        StageLogger.error("REMIX", f"Failed building audio timeline: {exc}", job_id)
        raise RuntimeError(f"Audio timeline generation failed: {exc}") from exc

    # Step 2: Mux timeline audio with original video
    StageLogger.info("REMIX", "Muxing synthesized audio with original video stream...", job_id)

    # First attempt: stream-copy visual track for zero quality loss and instant processing
    mux_cmd_copy = [
        "-y",
        "-i", str(video_path),
        "-i", str(timeline_wav),
        "-map", "0:v:0?",
        "-map", "1:a:0",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        str(output_mp4),
    ]

    try:
        run_ffmpeg(mux_cmd_copy, timeout=300)
    except Exception as copy_exc:
        StageLogger.info("REMIX", f"Stream copy failed ({copy_exc}), falling back to re-encoding...", job_id)
        # Fallback: re-encode video track if stream copy failed
        mux_cmd_encode = [
            "-y",
            "-i", str(video_path),
            "-i", str(timeline_wav),
            "-map", "0:v:0?",
            "-map", "1:a:0",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "22",
            "-c:a", "aac",
            "-b:a", "192k",
            "-movflags", "+faststart",
            str(output_mp4),
        ]
        run_ffmpeg(mux_cmd_encode, timeout=600)

    # Step 3: Strict verification of final MP4
    verify_file(output_mp4, "Final dubbed MP4 video")
    size_str = format_bytes(output_mp4.stat().st_size)
    StageLogger.success("REMIX", f"Final dubbed MP4 created ({size_str}) -> {output_mp4.name}", job_id)

    return output_mp4
