"""Search-query building and duration matching for downloaded tracks.

Pure helpers (no Qt, no network) — shared by the Spotify provider and the
engine's matched-download mode.
"""

from __future__ import annotations

import re
from typing import Optional

# Tolerance for duration matching between the metadata provider (e.g.
# Spotify track duration) and the resolved YouTube candidate. Covers
# intros/outros and different master versions; bigger gaps usually mean a
# live version, remix or cover.
DURATION_TOLERANCE_SEC = 12

# Common YouTube-noise decorations stripped from titles before search so the
# query matches the plain audio track (spotDL-style cleaning).
_NOISE_PATTERN = re.compile(
    r"\((?:\s*)(?:official\s+(?:music\s+)?(?:video|audio|visualizer)|"
    r"(?:music\s+)?video|audio|lyrics?|lyric\s+video|visualizer|"
    r"official\s+audio|hq|hd|4k|mv|official)\s*(?:\s*(?:video|audio))?(?:\s*)\)"
    r"|\[[^\]]*(?:official|lyrics?|audio|video|hd|hq|mv)[^\]]*\]"
    r"|【[^】]*(?:official|lyrics?|audio|video)[^】]*】",
    re.IGNORECASE,
)
# Bare markers without parentheses commonly appended by uploaders.
_BARE_NOISE = re.compile(
    r"\b(?:official\s+(?:music\s+)?(?:video|audio)|lyrics?|visualizer|mv)\b",
    re.IGNORECASE,
)
_MULTI_SPACE = re.compile(r"\s+")


def clean_title(title: str) -> str:
    """Strip YouTube-style decorations ("(Official Video)", "[Lyrics]") etc."""
    value = str(title or "")
    value = _NOISE_PATTERN.sub(" ", value)
    value = _NOISE_PATTERN.sub(" ", value)  # second pass for nested pairs
    value = _BARE_NOISE.sub(" ", value)
    value = _MULTI_SPACE.sub(" ", value).strip(" -–—|·")
    return value.strip()


def build_search_query(title: str, artist: str = "") -> str:
    """Build the ytsearch query: "Artist - Title" (fallback: cleaned title)."""
    clean = clean_title(title)
    artist_clean = str(artist or "").strip()
    if not clean:
        return artist_clean
    if not artist_clean:
        return clean
    return f"{artist_clean} - {clean}"


def duration_within_tolerance(
    expected_sec: Optional[int],
    actual_sec: Optional[float],
    tolerance: int = DURATION_TOLERANCE_SEC,
) -> bool:
    """True when the candidate duration is within ±tolerance of expected.

    Unknown durations (None on either side) are never rejected by this gate;
    callers treat them as "unknown" match quality instead.
    """
    if expected_sec is None or actual_sec is None:
        return False
    try:
        return abs(float(actual_sec) - float(expected_sec)) <= float(tolerance)
    except Exception:
        return False
