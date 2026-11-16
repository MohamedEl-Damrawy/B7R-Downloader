"""GUI tests for the Spotify plan UI wiring (Phase C)."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _ensure_app():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _stub_dialogs(monkeypatch):
    """Offscreen runs must never open modal QMessageBox dialogs."""
    from PySide6.QtWidgets import QMessageBox

    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: None))
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: QMessageBox.Ok))
    monkeypatch.setattr(QMessageBox, "critical", staticmethod(lambda *a, **k: None))


def _stub_thumbnail(page, monkeypatch):
    """Avoid QtNetwork fetches for cover-art previews in tests."""
    monkeypatch.setattr(page, "_set_thumbnail", lambda url, title="": None, raising=False)


def _spotify_track_plan(kind="track", count=1):
    from app.sources.base import SourcePlan, TrackSpec

    entries = [
        TrackSpec(
            title=f"Song {i}",
            artist="The Artist",
            album="Album X",
            duration_sec=200,
            cover_url="https://img/c.jpg",
            source_url=f"https://open.spotify.com/track/id{i}",
            source_type="spotify",
            search_query=f"The Artist - Song {i}",
            index=i + 1,
            available=True,
        )
        for i in range(count)
    ]
    return SourcePlan(
        kind=kind,
        title="Playlist P" if kind == "playlist" else entries[0].title,
        entries=entries,
        source_url="https://open.spotify.com/playlist/pid",
        thumbnail_url="https://img/p.jpg",
    )


def test_new_download_track_plan_enables_download_with_music_presets(qtbot, tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    _ensure_app()
    _stub_dialogs(monkeypatch)
    from app.ui.pages.new_download import NewDownloadPage

    page = NewDownloadPage()
    qtbot.addWidget(page)
    _stub_thumbnail(page, monkeypatch)

    page.on_source_plan(_spotify_track_plan())
    assert page.download_btn.isEnabled()
    presets = [page.format_combo.itemData(i) for i in range(page.format_combo.count())]
    assert "mp3_320" in presets and "flac" in presets
    assert "Spotify" in page.preview_label.text()


def test_new_download_playlist_plan_disables_download(qtbot, tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    _ensure_app()
    _stub_dialogs(monkeypatch)
    from app.ui.pages.new_download import NewDownloadPage

    page = NewDownloadPage()
    qtbot.addWidget(page)
    _stub_thumbnail(page, monkeypatch)

    page.on_source_plan(_spotify_track_plan(kind="playlist", count=3))
    assert not page.download_btn.isEnabled()


def test_playlist_page_shows_artist_and_uses_source_plan(qtbot, tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    _ensure_app()
    _stub_dialogs(monkeypatch)
    from PySide6.QtCore import Qt

    import app.engine.ffmpeg_manager as ffmpeg_mod
    from app.sources.base import SourcePlan
    from app.ui.pages.playlist import PlaylistsPage

    monkeypatch.setattr(ffmpeg_mod, "get_ffmpeg_path", lambda: "ffmpeg.exe")
    monkeypatch.setattr(ffmpeg_mod, "get_ffprobe_path", lambda: "ffprobe.exe")

    page = PlaylistsPage()
    qtbot.addWidget(page)
    page.set_playlist(_spotify_track_plan(kind="playlist", count=2))
    assert page.list_widget.count() == 2
    first = page.list_widget.item(0)
    assert "—" in first.text() and "The Artist" in first.text()

    queued = {}

    class FakeCtrl:
        def start_source_plan(self, plan, output_dir, quality, playlist_id=None):
            queued["plan"] = plan
            queued["quality"] = quality
            return ["t1"]

    page._controller = FakeCtrl()
    page.output_input.setText(str(tmp_path))
    page.list_widget.item(0).setCheckState(Qt.Checked)
    page._download_selected()
    assert "plan" in queued
    plan: SourcePlan = queued["plan"]
    assert plan.kind == "playlist"
    assert all(getattr(e, "search_query", "") for e in plan.entries)
