"""Audio metadata tagging (mutagen) for matched downloads.

Embeds Spotify-derived title/artist/album and album cover art into the
downloaded file. Format-aware (MP3/ID3, M4A/MP4, FLAC/Vorbis); failures
never break a successful download — callers treat tagging as best-effort.
"""

from __future__ import annotations

from typing import Optional

from app.core.logger import get_logger

logger = get_logger(__name__)


def _id3_picture_bytes(image: bytes, mime: str):
    from mutagen.id3 import APIC

    return APIC(encoding=3, mime=mime, type=3, desc="Cover", data=image)


def embed_metadata(
    filepath: str,
    title: str = "",
    artist: str = "",
    album: str = "",
    cover_image: Optional[bytes] = None,
    cover_mime: str = "image/jpeg",
) -> bool:
    """Best-effort tag embedding. Returns True on success."""
    path = str(filepath or "")
    if not path:
        return False
    lower = path.lower()
    try:
        if lower.endswith(".mp3"):
            return _embed_mp3(path, title, artist, album, cover_image, cover_mime)
        if lower.endswith(".m4a") or lower.endswith(".mp4"):
            return _embed_m4a(path, title, artist, album, cover_image)
        if lower.endswith(".flac"):
            return _embed_flac(path, title, artist, album, cover_image, cover_mime)
        # Unknown container (e.g. webm): skip tagging quietly.
        logger.info("Tagging skipped for unsupported container: %s", path)
        return False
    except Exception:
        logger.warning("Tagging failed (download kept): %s", path, exc_info=True)
        return False


def _embed_mp3(path: str, title: str, artist: str, album: str, cover: Optional[bytes], mime: str) -> bool:
    from mutagen.id3 import ID3, TALB, TIT2, TPE1, ID3NoHeaderError

    try:
        tags = ID3(path)
    except ID3NoHeaderError:
        tags = ID3()
    if title:
        tags.setall("TIT2", [TIT2(encoding=3, text=[title])])
    if artist:
        tags.setall("TPE1", [TPE1(encoding=3, text=[artist])])
    if album:
        tags.setall("TALB", [TALB(encoding=3, text=[album])])
    if cover:
        tags.setall("APIC", [_id3_picture_bytes(cover, mime)])
    tags.save(path)
    return True


def _embed_m4a(path: str, title: str, artist: str, album: str, cover: Optional[bytes]) -> bool:
    from mutagen.mp4 import MP4, MP4Cover

    tags = MP4(path)
    if title:
        tags["\xa9nam"] = [title]
    if artist:
        tags["\xa9ART"] = [artist]
    if album:
        tags["\xa9alb"] = [album]
    if cover:
        tags["covr"] = [MP4Cover(cover, imagetype=3)]  # 3 = front cover
    tags.save()
    return True


def _embed_flac(path: str, title: str, artist: str, album: str, cover: Optional[bytes], mime: str) -> bool:
    from mutagen.flac import FLAC, Picture

    audio = FLAC(path)
    if title:
        audio["title"] = title
    if artist:
        audio["artist"] = artist
    if album:
        audio["album"] = album
    if cover:
        pic = Picture()
        pic.type = 3  # front cover
        pic.mime = mime
        pic.data = cover
        audio.clear_pictures()
        audio.add_picture(pic)
    audio.save()
    return True
