"""Integration tests for runtime environment and core wiring."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest


def test_ffmpeg_bundled_resolution():
    from app.engine.ffmpeg_manager import get_ffmpeg_location_for_ytdlp, get_ffmpeg_path, get_ffprobe_path

    ffmpeg = get_ffmpeg_path()
    ffprobe = get_ffprobe_path()
    assert ffmpeg is not None and ffmpeg.exists(), "ffmpeg should be resolved"
    assert ffprobe is not None and ffprobe.exists(), "ffprobe should be resolved"
    loc = get_ffmpeg_location_for_ytdlp()
    assert loc is not None
    vendor = Path(__file__).resolve().parents[2] / "vendor" / "ffmpeg"
    assert vendor in ffmpeg.parents or ffmpeg.parent == vendor
    assert vendor in ffprobe.parents or ffprobe.parent == vendor


def test_database_migrations_apply(tmp_path, monkeypatch):
    import app.core.paths as paths

    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    from app.database.migrations import apply_migrations

    apply_migrations()
    db_path = paths.get_database_path()
    assert db_path.exists()
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        names = {r[0] for r in cur.fetchall()}
        assert {"settings", "downloads", "playlists", "download_items"}.issubset(names)
    finally:
        conn.close()


def test_config_load_and_save(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    from app.core.config import AppConfig

    cfg = AppConfig.load()
    assert isinstance(cfg.values, dict)
    cfg.set("ui_theme", "dark")
    cfg.save()
    cfg2 = AppConfig.load()
    assert cfg2.get("ui_theme") == "dark"


@pytest.mark.network
def test_real_download_smoke(tmp_path, monkeypatch):
    """Real download+merge smoke test (requires network and YouTube access)."""
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    from app.engine.ffmpeg_manager import get_ffmpeg_location_for_ytdlp
    from app.engine.ytdlp_engine import download_media

    ff = get_ffmpeg_location_for_ytdlp()
    out = tmp_path / "out"
    out.mkdir()
    url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"
    fmt = "worstvideo[height<=240]+worstaudio/worst[height<=240]/worst"
    result = download_media(url, str(out), format_selector=fmt, ffmpeg_location=ff)
    assert result.get("ok") is True
    files = [p for p in out.rglob("*") if p.is_file()]
    assert files, "expected downloaded file(s)"
    assert any(p.stat().st_size > 0 for p in files)
