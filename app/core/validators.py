"""Input validation helpers."""

from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


_SENSITIVE_QUERY_KEYS = {
    "token",
    "access_token",
    "auth",
    "authorization",
    "key",
    "api_key",
    "signature",
    "sig",
    "password",
    "pass",
    "session",
    "cookie",
}


def is_http_url(value: str) -> bool:
    if not value or not isinstance(value, str):
        return False
    v = value.strip()
    try:
        parsed = urlparse(v)
    except Exception:
        return False
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def is_valid_playlist_items(value: str) -> bool:
    """Validate yt-dlp ``playlist_items`` syntax: indices/ranges like "3" or "1-5,7".

    Video IDs or arbitrary text are invalid: passing them makes yt-dlp select no
    item at all (or, with the playlist URL fallback, download everything).
    """
    if not value or not isinstance(value, str):
        return False
    for part in value.split(","):
        part = part.strip()
        if not part:
            return False
        if "-" in part:
            bounds = part.split("-")
            if len(bounds) != 2 or not all(b.strip().isdigit() for b in bounds):
                return False
        elif not part.isdigit():
            return False
    return True


def redact_url(value: str | None) -> str:
    """Return URL with sensitive query params redacted for safe logging."""
    if not value:
        return ""
    try:
        parsed = urlparse(value)
        if not parsed.scheme or not parsed.netloc:
            return value
        pairs = parse_qsl(parsed.query, keep_blank_values=True)
        redacted_pairs = []
        changed = False
        for k, v in pairs:
            if k.lower() in _SENSITIVE_QUERY_KEYS or "token" in k.lower() or "key" in k.lower():
                redacted_pairs.append((k, "REDACTED"))
                changed = True
            else:
                redacted_pairs.append((k, v))
        query = urlencode(redacted_pairs, doseq=True) if pairs else parsed.query
        netloc = parsed.netloc
        # redact userinfo if present
        if "@" in netloc:
            netloc = "REDACTED@" + netloc.split("@", 1)[1]
            changed = True
        if not changed and not pairs and "@" not in parsed.netloc:
            return value
        return urlunparse((parsed.scheme, netloc, parsed.path, parsed.params, query, parsed.fragment))
    except Exception:
        return "<invalid-url>"
