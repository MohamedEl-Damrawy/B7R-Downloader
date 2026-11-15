"""Format selection helpers (independent of PySide6)."""

from __future__ import annotations

from typing import Iterable

from app.models.video import FormatOption

QUALITY_HEIGHT_MAP = {
    "1080p": 1080,
    "720p": 720,
    "480p": 480,
}


def normalize_formats(raw_formats: Iterable[dict]) -> list[FormatOption]:
    out: list[FormatOption] = []
    for f in raw_formats or []:
        if not isinstance(f, dict):
            continue
        fmt_id = str(f.get("format_id") or "")
        if not fmt_id:
            continue
        height = f.get("height")
        try:
            height = int(height) if height is not None else None
        except Exception:
            height = None
        label_parts = []
        if height:
            label_parts.append(f"{height}p")
        ext = f.get("ext")
        if ext:
            label_parts.append(str(ext))
        note = f.get("format_note") or f.get("resolution")
        if note:
            label_parts.append(str(note))
        label = " / ".join(label_parts) or fmt_id
        out.append(
            FormatOption(
                format_id=fmt_id,
                label=label,
                ext=str(ext) if ext else None,
                height=height,
                fps=f.get("fps"),
                vcodec=f.get("vcodec"),
                acodec=f.get("acodec"),
                filesize=f.get("filesize") or f.get("filesize_approx"),
                note=str(note) if note else None,
            )
        )
    return out


def pick_format_for_quality(formats: list[FormatOption], quality: str) -> str | None:
    """Return a yt-dlp format selector string or format id preference."""
    q = (quality or "best").strip()
    q_lower = q.lower()
    if q_lower == "best":
        return "bv*+ba/b"
    if q_lower.startswith("id:"):
        fmt_id = q.split(":", 1)[1].strip()
        if fmt_id:
            # Try selected video format with best audio; fall back sensibly.
            return f"{fmt_id}+ba/{fmt_id}/b"
        return "bv*+ba/b"
    target = QUALITY_HEIGHT_MAP.get(q_lower)
    if target:
        # Prefer best video at or below target with best audio, fallback gracefully.
        return f"bv*[height<={target}]+ba/b[height<={target}]/bv*+ba/b"
    if q_lower in AUDIO_PRESETS:
        # FEAT-01: audio-only presets select the best audio stream; the actual
        # codec conversion happens via FFmpegExtractAudio in the engine.
        return "bestaudio/best"
    return "bv*+ba/b"


# FEAT-01: audio-only presets -> FFmpegExtractAudio target codec.
AUDIO_PRESETS: dict[str, str] = {
    "audio_mp3": "mp3",
    "audio_m4a": "m4a",
}


def audio_preset_for_quality(quality: str) -> str | None:
    """Return the target audio codec ("mp3"/"m4a") when quality is audio-only."""
    q = (quality or "").strip().lower()
    return AUDIO_PRESETS.get(q)
