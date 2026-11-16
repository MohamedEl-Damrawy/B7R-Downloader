# Architecture Notes (ARCH-02 / ARCH-03)

Notes on two intentional architectural decisions that surfaced during the
2026 audit. They are documented here so future contributors do not
"fix" them into regressions.

## ARCH-02 — Worker lifetime: signal-disconnect + pop, no deleteLater

**Where:** `app/controllers/download_controller.py` (`_start_worker`,
`_on_finished`), `app/workers/*`.

**Decision:** `DownloadWorker`/`MetadataWorker` instances are stored in
`self._workers[task_id]`, their signals are connected once at start, and on
finish `_on_finished` pops the worker from the dict and discards the task's
active/spec/batch-state entries. Workers are NOT explicitly
`deleteLater()`-ed by the controller.

**Why this is safe:**

- Each `WorkerSignals` object is a fresh `QObject` created per worker; it has
  no parent, so it is owned by Python. Once the controller drops its last
  reference (the `_workers` pop after `finished` fires), the bindings
  garbage-collect it. There is no C++-owned parent keeping it alive, and no
  pending queued signals after `finished` has been emitted and handled.
- The one place where a thread outlives its creator scope — the yt-dlp update
  check in `app/ui/pages/settings.py` — DOES use `deleteLater`
  (`self._update_thread.finished.connect(self._update_thread.deleteLater)`)
  and keeps a reference on the page (`self._update_thread`) so the thread is
  never GC'd mid-run.
- `QThreadPool` owns the native thread until `run()` returns; the Python
  wrapper remaining alive until then is guaranteed by the pool's reference.

**Rule of thumb:** any future long-lived worker class should either be popped
by a `finished` handler exactly like `_on_finished` does, or, if it can be
garbage-collected while running (no kept reference), follow the settings-page
pattern: store the instance on the owner AND connect `finished → deleteLater`.

## ARCH-03 — SQLite connection-per-operation, no pooling

**Where:** `app/database/connection.py` (`db_session`), all repositories.

**Decision:** every repository method opens its own short-lived connection
via `db_session()` (context manager: connect → execute → commit/close).
There is no connection pool and no long-lived shared connection.

**Why this is the right fit here:**

- The database is a small local SQLite file in the user's app-data directory.
  Opening a SQLite connection is an in-process `open()`-level operation
  (microseconds); pooling would add complexity with no measurable win.
- Per-call connections give us free cross-thread isolation: a Qt worker
  thread never shares a connection object with the GUI thread, which avoids
  the classic `sqlite3.threadsafety` hazards and the need for a check-same
  -thread guard.
- WAL mode is enabled in `connection.py`, so concurrent readers never block
  the single writer and vice-versa; short connections keep write locks held
  only for the duration of one statement batch.
- The known write-hotspot (high-frequency progress updates) is already
  throttled at the controller level (`_DB_WRITE_INTERVAL_SEC`, PERF-01), so
  the database sees at most ~2 writes/second per active task.

**When to revisit:** only if the app ever moves to a client/server database
(Postgres/MySQL) or to a network share. In that case introduce an explicit
session/pool layer behind `db_session()` — the repository call-sites will not
need to change because they never touch connection objects directly.

## SRC-01 — Source-provider layer (Spotify Option A)

**Where:** `app/sources/` (`base.py`, `youtube.py`, `spotify.py`,
`registry.py`), schema v3.

**Decision:** user URLs resolve through a provider registry
(`get_provider_for_url`). The YouTube provider is the always-registered
catch-all that delegates to the existing `ytdlp_engine.extract_metadata`
path — YouTube behavior is byte-identical to before the layer existed.
Spotify (Phase B) is a *metadata* provider: audio never comes from Spotify
(DRM); resolved Spotify tracks are matched to YouTube Music via
`ytsearch1:"artist - title"` with a duration sanity gate at download time.

**Consequences:**

- Schema v3: `downloads.source_type` ("youtube" | "spotify"), and
  `download_items.artist/album/cover_url` for music metadata. Migration is
  idempotent (`_column_exists` guards, same pattern as v2).
- PERF-04 playlist batching stays **YouTube-only**: Spotify entries have no
  yt-dlp URL to share a page fetch with, so each matched track is its own
  per-track task (one cheap `ytsearch1:` fetch).
- Spotify provider is registered in Phase B when `resolve()` is implemented;
  until then Spotify URLs fall through to the YouTube catch-all, exactly as
  before (yt-dlp rejects them).
- Matched downloads tag files with **mutagen** (`app/engine/audio_tags.py`)
  instead of yt-dlp postprocessor metadata injection: the YouTube-sourced
  info dict carries YouTube titles, so post-download tagging is the only
  reliable way to write Spotify title/artist/album + embedded cover art.
  Tagging is best-effort and never fails a successful download.
- Loose duration matches (no candidate within ±12 s of the Spotify duration)
  still download (first candidate) and are recorded as
  `match_quality=loose` in `downloads.error_code` so history surfaces them.
- **Spotify Feb-2026 developer rules** (blog 2026-02-06): Development Mode
  now requires a **Premium** app owner, and playlist contents are limited to
  playlists the authenticated owner collaborates on — third-party public
  playlists are no longer readable, so playlist links may fail with an
  actionable SourceError while track/album links keep working (catalog
  endpoints Get Track / Get Album / Get Album Tracks / Search remain
  available; client-credentials still works for catalog metadata). spotipy
  2.26 still calls the removed `GET /playlists/{id}/tracks`; the provider
  falls back to the renamed `GET /playlists/{id}/items` and normalizes the
  `items[].item` field rename.
