"""Application update check against the project's GitHub Releases.

The app's own "Check Updates" feature queries the GitHub API for the latest
published release of MohamedEl-Damrawy/B7R-Downloader and compares its tag
with the bundled APP_VERSION. This is separate from the yt-dlp library check
(app/engine/ytdlp_engine.py:latest_pypi_version), which tracks PyPI.
"""

from __future__ import annotations

import json
import re
from typing import Any, Optional

from app.core.constants import APP_RELEASES_API, APP_VERSION


def normalize_tag(tag: str | None) -> str:
    """Strip a leading 'v'/'V' and surrounding whitespace from a release tag."""
    return (tag or "").strip().lstrip("vV").strip()


def parse_version(value: str | None) -> Optional[tuple[int, ...]]:
    """Parse '1.2.3' (or 'v1.2.3') into a tuple of ints; None if not parseable.

    Non-numeric suffixes ('1.2.3-beta') keep only the leading numeric parts.
    """
    cleaned = normalize_tag(value)
    if not cleaned:
        return None
    match = re.match(r"^(\d+(?:\.\d+)*)", cleaned)
    if not match:
        return None
    try:
        return tuple(int(p) for p in match.group(1).split("."))
    except ValueError:
        return None


def compare_versions(current: str | None, latest: str | None) -> int:
    """Compare two version strings; -1 current<latest, 0 equal, +1 current>latest.

    Missing numeric parts count as 0 ('1.2' == '1.2.0'). Unparseable values
    sort as lower so a malformed tag never hides a real update.
    """
    cur = parse_version(current)
    lat = parse_version(latest)
    if cur is None and lat is None:
        return 0
    if cur is None:
        return -1
    if lat is None:
        return 1
    width = max(len(cur), len(lat))
    cur = cur + (0,) * (width - len(cur))
    lat = lat + (0,) * (width - len(lat))
    if cur < lat:
        return -1
    if cur > lat:
        return 1
    return 0


def _fetch_latest_release(timeout: float) -> dict[str, Any] | None:
    """GET the latest GitHub release; None on any network/parse failure.

    A 404 (repository has no published releases) also yields None but is
    distinguishable from a network error via latest_release_state().
    """
    import urllib.request

    req = urllib.request.Request(
        APP_RELEASES_API,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "VeloDownloader"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data if isinstance(data, dict) else None


def latest_release_state(timeout: float = 5.0) -> str:
    """Raw connectivity state: "ok" (found or 404) or "unreachable"."""
    try:
        _fetch_latest_release(timeout)
        return "ok"
    except Exception:
        return "unreachable"


def check_for_app_update(timeout: float = 5.0) -> dict[str, Any]:
    """Check GitHub Releases for a newer version of the app.

    Returns a dict:
      - status: "update_available" | "up_to_date" | "no_releases" | "unreachable"
      - current: bundled APP_VERSION
      - latest: normalized latest tag (or "" when unknown)
      - url: releases page (for the "download the update" link)
    """
    import urllib.error

    result: dict[str, Any] = {
        "status": "unreachable",
        "current": APP_VERSION,
        "latest": "",
        "url": "",
    }
    try:
        data = _fetch_latest_release(timeout)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            result["status"] = "no_releases"
        return result
    except Exception:
        return result

    tag = normalize_tag(str(data.get("tag_name") or ""))
    result["url"] = str(data.get("html_url") or "")
    if not tag:
        result["status"] = "no_releases"
        return result
    result["latest"] = tag
    result["status"] = "update_available" if compare_versions(APP_VERSION, tag) < 0 else "up_to_date"
    return result
