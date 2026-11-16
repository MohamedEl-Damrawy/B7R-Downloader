"""yt-dlp engine wrapper (no PySide6 dependency)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Optional

from app.core.exceptions import (
    CancelledError,
    DownloadError,
    MetadataExtractionError,
    UnsupportedSourceError,
)
from app.core.logger import get_logger
from app.core.paths import get_default_download_dir
from app.core.validators import redact_url
from app.engine.format_selector import normalize_formats
from app.engine.progress_parser import parse_progress_hook
from app.models.playlist import PlaylistEntry, PlaylistMetadata
from app.models.video import VideoMetadata

ProgressCallback = Callable[[dict[str, Any]], None]
logger = get_logger(__name__)

# Titles YouTube itself renders in playlist pages for unplayable videos;
# they pass through yt-dlp unchanged, so matching them is the only reliable
# per-entry availability signal for playlist metadata.
_UNAVAILABLE_TITLE_MARKERS = (
    "[private video]",
    "[deleted video]",
    "[unavailable video]",
    "[members-only video]",
    "[age-restricted video]",
    "[premium video]",
    "[region-locked video]",
)


def _entry_is_unavailable(title: str | None) -> bool:
    t = str(title or "").strip().lower()
    return any(t.startswith(marker) or t == marker.strip("[]") for marker in _UNAVAILABLE_TITLE_MARKERS)


def _build_postprocessors(
    audio_format: str | None = None,
    embed_metadata: bool = False,
    embed_thumbnail: bool = False,
    sponsorblock: bool = False,
) -> list[dict[str, Any]]:
    """Build the yt-dlp postprocessor list (FEAT-01/02/03). Pure helper."""
    pps: list[dict[str, Any]] = []
    if sponsorblock:
        pps.append(
            {
                "key": "SponsorBlock",
                "categories": ["sponsor", "intro", "outro", "selfpromo", "preview"],
                "when": "after_video",
            }
        )
    if embed_thumbnail:
        pps.append({"key": "EmbedThumbnail", "already_have_thumbnail": False})
    if audio_format:
        pps.append(
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": audio_format,
                "preferredquality": "192",
            }
        )
    if embed_metadata:
        pps.append({"key": "FFmpegMetadata", "add_metadata": True})
    return pps


def _apply_network_opts(opts: dict[str, Any], cookiefile: Optional[str] = None, proxy: Optional[str] = None) -> None:
    """Add credentials options (DL-07/FEAT-04/FEAT-05). Pure helper."""
    if cookiefile and str(cookiefile).strip():
        # Netscape-format cookie jar; the file may contain session secrets.
        opts["cookiefile"] = str(cookiefile).strip()
    if proxy and str(proxy).strip():
        opts["proxy"] = str(proxy).strip()


class CancelToken:
    def __init__(self) -> None:
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    @property
    def cancelled(self) -> bool:
        return self._cancelled


def get_ytdlp_version() -> str:
    """DL-10/FEAT-07: installed yt-dlp version, empty string when unavailable."""
    try:
        yt_dlp = _lazy_yt_dlp()
        return str(yt_dlp.version.__version__)
    except Exception:
        return ""


def latest_pypi_version(package: str = "yt-dlp", timeout: float = 5.0) -> Optional[str]:
    """Query PyPI for the latest release of a package; None on any failure."""
    try:
        import json
        import urllib.request

        url = f"https://pypi.org/pypi/{package}/json"
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return str(data.get("info", {}).get("version") or "") or None
    except Exception:
        return None


def _lazy_yt_dlp():
    try:
        import yt_dlp  # type: ignore
        return yt_dlp
    except Exception as exc:  # pragma: no cover - environment dependent
        raise MetadataExtractionError(
            "yt-dlp is not available. Install dependencies to enable downloads."
        ) from exc


def _base_opts(ffmpeg_location: Optional[str] = None) -> dict[str, Any]:
    opts: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": False,
        "skip_download": True,
        "extract_flat": False,
        # Tolerate per-entry failures (private/deleted/age-restricted videos) while
        # extracting playlist metadata, instead of aborting the whole extraction.
        "ignoreerrors": True,
        "socket_timeout": 30,
    }
    if ffmpeg_location:
        opts["ffmpeg_location"] = ffmpeg_location
    return opts


class _YTdlpCaptureLogger:
    """Captures yt-dlp stderr messages (logger protocol) for error classification.

    yt-dlp routes every stderr line through ``logger.error(message)`` and every
    stdout line through ``logger.debug(message)``; raised failures keep the
    ``ERROR:`` prefix added by ``YoutubeDL.report_error``.
    """

    def __init__(self) -> None:
        self.errors: list[str] = []

    def debug(self, msg: Any, *args: Any, **kwargs: Any) -> None:
        return

    def info(self, msg: Any, *args: Any, **kwargs: Any) -> None:
        return

    def warning(self, msg: Any, *args: Any, **kwargs: Any) -> None:
        return

    def error(self, msg: Any, *args: Any, **kwargs: Any) -> None:
        try:
            text = str(msg % args) if args else str(msg)
        except Exception:
            text = str(msg)
        self.errors.append(text)
        logger.error("yt-dlp: %s", text)

    def last_error(self) -> str:
        """Return the last real error text (``ERROR:`` prefix stripped) or ""."""
        for msg in reversed(self.errors):
            stripped = str(msg).strip()
            if stripped.upper().startswith("ERROR:"):
                return stripped[len("ERROR:"):].strip()
        return ""


def _classify_error(exc: Exception) -> Exception:
    msg = str(exc).lower()
    if "unsupported url" in msg or "not supported" in msg:
        return UnsupportedSourceError("This source is not supported.")
    if "private video" in msg or "sign in" in msg or "login required" in msg:
        return MetadataExtractionError(
            "This content requires access that is not available. Authorized/public content only."
        )
    if "timed out" in msg or "timeout" in msg:
        return MetadataExtractionError(
            "Network timeout while extracting metadata. Check your connection and try again."
        )
    if "unable to download webpage" in msg or "http error" in msg or "network" in msg or "connection" in msg:
        return MetadataExtractionError("Network error while extracting metadata. Check the URL and your connection.")
    return MetadataExtractionError("Failed to extract metadata from the provided URL.")


def _classify_download_error(exc: Exception) -> Exception:
    if isinstance(exc, CancelledError):
        return exc
    msg_raw = str(exc)
    msg = msg_raw.lower()
    if "unsupported url" in msg or "not supported" in msg:
        return UnsupportedSourceError("This source is not supported.")
    if "ffmpeg" in msg and ("not found" in msg or "no such file" in msg):
        return DownloadError("FFmpeg is missing or could not be run. Check bundled FFmpeg files.")
    if "permission denied" in msg or "access is denied" in msg:
        return DownloadError("Permission denied while writing to the output location.")
    if "no space left" in msg or "disk full" in msg or "not enough space" in msg:
        return DownloadError("Not enough disk space to complete the download.")
    if "timed out" in msg or "timeout" in msg:
        return DownloadError("Network timeout while downloading. Check your connection and try again.")
    if "unable to download" in msg or "http error" in msg or "network" in msg or "connection" in msg:
        return DownloadError("Network error while downloading. Check your connection and try again.")
    return DownloadError("Download failed. Check the URL, network connection, FFmpeg availability, or output path.")


def extract_metadata(
    url: str,
    ffmpeg_location: Optional[str] = None,
    cookiefile: Optional[str] = None,
    proxy: Optional[str] = None,
) -> tuple[VideoMetadata | None, PlaylistMetadata | None]:
    yt_dlp = _lazy_yt_dlp()
    opts = _base_opts(ffmpeg_location)
    # PERF-03/FEAT-15: playlist previews only need titles/URLs; flat extraction
    # avoids fetching one full page per entry (minutes + 429 risk on large
    # playlists). Full per-entry data is still fetched at download time.
    opts["extract_flat"] = "in_playlist"
    _apply_network_opts(opts, cookiefile=cookiefile, proxy=proxy)
    capture = _YTdlpCaptureLogger()
    opts["logger"] = capture
    safe_url = redact_url(url)
    logger.info("Extracting metadata: url=%s ffmpeg=%s", safe_url, ffmpeg_location or "default")
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as exc:
        logger.exception("Metadata extraction failed: url=%s", safe_url)
        raise _classify_error(exc) from exc

    if not isinstance(info, dict):
        # With ignoreerrors enabled, a total failure surfaces as None instead of an
        # exception; classify using the error messages yt-dlp reported to stderr.
        detail = capture.last_error()
        logger.error("Metadata extraction returned no info: url=%s detail=%s", safe_url, detail)
        if detail:
            raise _classify_error(RuntimeError(detail))
        raise MetadataExtractionError("No metadata was returned.")

    is_playlist = info.get("_type") == "playlist" or bool(info.get("entries")) and "entries" in info
    if is_playlist:
        entries_raw = info.get("entries") or []
        entries: list[PlaylistEntry] = []
        for idx, e in enumerate(entries_raw, start=1):
            if not isinstance(e, dict):
                # With ignoreerrors enabled, per-entry extraction failures surface
                # as None; surface them to the UI as unavailable placeholders.
                entries.append(
                    PlaylistEntry(
                        entry_id=f"unavailable-{idx}",
                        source_url="",
                        title=f"Unavailable (entry {idx})",
                        index=idx,
                        available=False,
                    )
                )
                continue
            entry_url = e.get("url") or e.get("webpage_url") or e.get("original_url") or ""
            if entry_url and not str(entry_url).startswith("http"):
                # flat/partial entries may only have ids; keep best effort
                entry_url = e.get("webpage_url") or entry_url
            title = str(e.get("title") or f"Entry {idx}")
            entries.append(
                PlaylistEntry(
                    entry_id=str(e.get("id") or idx),
                    source_url=str(entry_url or ""),
                    title=title,
                    thumbnail_url=str(e.get("thumbnail") or ""),
                    index=e.get("playlist_index") or idx,
                    available=not _entry_is_unavailable(title),
                )
            )
        playlist = PlaylistMetadata(
            source_url=str(info.get("webpage_url") or url),
            title=str(info.get("title") or "Playlist"),
            thumbnail_url=str(info.get("thumbnail") or ""),
            entries=entries,
            total_entries=int(info.get("playlist_count") or len(entries)),
        )
        return None, playlist

    formats = normalize_formats(info.get("formats") or [])
    video = VideoMetadata(
        source_url=str(info.get("webpage_url") or url),
        title=str(info.get("title") or ""),
        thumbnail_url=str(info.get("thumbnail") or ""),
        duration=info.get("duration"),
        uploader=info.get("uploader"),
        is_playlist=False,
        formats=formats,
    )
    return video, None


def download_media(
    url: str,
    output_dir: str,
    format_selector: str = "bv*+ba/b",
    ffmpeg_location: Optional[str] = None,
    progress_callback: Optional[ProgressCallback] = None,
    cancel_token: Optional[CancelToken] = None,
    playlist_items: Optional[str] = None,
    audio_format: Optional[str] = None,
    embed_metadata: bool = False,
    embed_thumbnail: bool = False,
    write_subs: bool = False,
    sponsorblock: bool = False,
    cookiefile: Optional[str] = None,
    proxy: Optional[str] = None,
) -> dict[str, Any]:
    """Download media to output_dir. Returns basic result info."""
    yt_dlp = _lazy_yt_dlp()
    if not str(output_dir or "").strip():
        # Avoid silently writing to the process working directory (e.g. the
        # install folder in packaged builds); fall back to the default location.
        logger.warning("Empty output_dir requested; falling back to default download dir")
        output_dir = str(get_default_download_dir())
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    outtmpl = str(out_dir / "%(title).200B [%(id)s].%(ext)s")

    def hook(d: dict[str, Any]) -> None:
        if cancel_token and cancel_token.cancelled:
            raise CancelledError("Download cancelled by user.")
        if progress_callback:
            try:
                progress_callback(parse_progress_hook(d).to_dict())
            except Exception:
                progress_callback({"status": d.get("status", "unknown")})

    def pp_hook(d: dict[str, Any]) -> None:
        # Cancellation + a visible "Processing" state during the ffmpeg merge,
        # which plain progress hooks never report (they stop at "finished").
        if cancel_token and cancel_token.cancelled:
            raise CancelledError("Download cancelled by user.")
        if progress_callback:
            progress_callback(
                {
                    "status": "postprocessing",
                    "postprocessor": d.get("postprocessor"),
                }
            )

    opts: dict[str, Any] = {
        "outtmpl": outtmpl,
        "format": format_selector or "bv*+ba/b",
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "progress_hooks": [hook],
        "postprocessor_hooks": [pp_hook],
        "merge_output_format": "mp4",
        "concurrent_fragment_downloads": 1,
        "retries": 10,
        "fragment_retries": 10,
        "extractor_retries": 3,
        "socket_timeout": 30,
        # DL-11: keep generated file names short enough for MAX_PATH-less setups.
        "trim_file_name": 150,
        "overwrites": False,
        "continuedl": True,
        "noplaylist": playlist_items is None,
    }
    pps = _build_postprocessors(
        audio_format=audio_format,
        embed_metadata=embed_metadata,
        embed_thumbnail=embed_thumbnail,
        sponsorblock=sponsorblock,
    )
    if pps:
        opts["postprocessors"] = pps
        if audio_format:
            # Audio-only: no video stream and no mp4 merge container.
            opts["format"] = "bestaudio/best"
            opts.pop("merge_output_format", None)
    if write_subs:
        opts["writesubtitles"] = True
        opts["subtitleslangs"] = ["en.*", "ar.*"]
        opts["skip_download"] = False
    _apply_network_opts(opts, cookiefile=cookiefile, proxy=proxy)
    if playlist_items:
        opts["playlist_items"] = playlist_items
        opts["noplaylist"] = False
    if ffmpeg_location:
        opts["ffmpeg_location"] = ffmpeg_location

    safe_url = redact_url(url)
    logger.info(
        "Starting download: url=%s output=%s format=%s playlist_items=%s ffmpeg=%s",
        safe_url,
        output_dir,
        format_selector,
        playlist_items,
        ffmpeg_location or "default",
    )
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
    except CancelledError:
        logger.info("Download cancelled: url=%s", safe_url)
        raise
    except Exception as exc:
        logger.exception("Download failed: url=%s output=%s", safe_url, output_dir)
        raise _classify_download_error(exc) from exc

    result = {"ok": True}
    if isinstance(info, dict):
        result.update(
            {
                "title": info.get("title"),
                "id": info.get("id"),
                "requested_downloads": info.get("requested_downloads"),
                "filepath": info.get("filepath") or info.get("_filename"),
                "ext": info.get("ext"),
            }
        )
        # PERF-04: playlist/batch results have no playlist-level filepath; the
        # per-item paths live in the entries. Expose them so callers (and the
        # "Open Folder" flow) can resolve the batch output directory.
        if info.get("_type") == "playlist" or not result["filepath"]:
            filepaths = [
                str(e.get("filepath") or e.get("_filename"))
                for e in (info.get("entries") or [])
                if isinstance(e, dict) and (e.get("filepath") or e.get("_filename"))
            ]
            if filepaths:
                result["filepaths"] = filepaths
                if not result["filepath"]:
                    # Store the parent folder of the first produced file so the
                    # task record points somewhere openable.
                    result["filepath"] = str(Path(filepaths[0]).parent)
    return result
