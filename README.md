# Velo Downloader

Baseline implementation scaffold for **Velo Downloader**, a modern Windows desktop downloader for authorized video and playlist content.

## Developer / Publisher
- **Developer:** Mohamed El-Damrawy
  - LinkedIn: https://www.linkedin.com/in/mohamed-eldamrawy/
  - GitHub: https://github.com/MohamedEl-Damrawy
- **Publisher/Legal entity:** فردي (بدون كيان قانوني)
- **Copyright:** Copyright (c) 2026 Mohamed El-Damrawy
- **Application license:** MIT (see `LICENSE`). Third-party bundled/runtime components remain under their own licenses (see `licenses/THIRD_PARTY_NOTICES.txt` and `licenses/third_party/`).

## Current Status
- **Implemented (baseline):** 6-layer app (PySide6/QSS UI, yt-dlp Python API engine, FFmpeg manager, SQLite + repos, QThreadPool/QRunnable workers, dataclasses), metadata/download flow with progress/cancel/retry, queue/concurrency, playlist save/load and per-item handling, settings persistence, startup recovery, validations/preflight warnings.
- **Dev/runtime verification:** PySide6/pytest/pytest-qt/yt-dlp installed; FFmpeg/FFprobe bundled in `vendor/ffmpeg` and resolved; offscreen GUI smoke and real download+merge smoke (network) passed. **Pytest suite: 23 passed**.
- **Release/legal artifacts:** `LICENSE` (MIT), `licenses/THIRD_PARTY_NOTICES.txt`, `resources/legal/privacy_notice.txt`, `resources/legal/usage_notice.txt`, `docs/RELEASE_READINESS.md`, copied third-party license/readme artifacts in `licenses/third_party/`.
- **Packaging (owner-approved in session):** explicit approval recorded to create **Setup + ZIP** using **pyside6-deploy**, with **Desktop and Start Menu shortcuts**, and perform a clean-machine test. **Nuitka/pyside6-deploy packaging not yet installed/configured for this project; Inno Setup compiler (`iscc`) not detected. No EXE/Setup/ZIP release artifacts have been created yet.**
- **Important compliance note:** bundled FFmpeg/FFprobe are from a gyan.dev 8.1.2 full static build (GPLv3 stated). Distributing packages containing these binaries requires satisfying applicable GPLv3 obligations (complete license texts, corresponding-source information/offer for the exact shipped build) and Qt/PySide6 redistribution obligations. Final legal/compliance review of the exact release package is required.

## Runtime Data Location
Mutable application data (config, database, logs, cache/temp) is stored under:

`%LOCALAPPDATA%\VeloDownloader`

## Development (for contributors)
Install dependencies, then:
- Run app: `python main.py` (requires `PySide6`; `yt-dlp` needed for metadata/download; FFmpeg/FFprobe bundled in `vendor/ffmpeg` or available on PATH in dev)
- Run tests: `pytest -q` (default excludes the network-marked real-download smoke test; run it explicitly with `pytest -m network`, or `python -m unittest discover -s tests/unit -p "test_*.py"`)
- The bundled FFmpeg/FFprobe binaries in `vendor/ffmpeg/` are intentionally excluded from version control (462 MB); the full build is preserved in the workspace backup and sourced from gyan.dev 8.1.2 — see `vendor/ffmpeg/README.txt`

Dependencies declared in `pyproject.toml` / `requirements.txt` include PySide6, yt-dlp, pytest, pytest-qt.

## Legal/Compliance Notes
- Support downloads only where users have rights and source terms permit.
- No DRM/paywall/access-control circumvention is planned or supported.
- Draft notices live in `licenses/THIRD_PARTY_NOTICES.txt` and `resources/legal/`; they require audit and owner-confirmed product/legal details before release.
- **No final EXE/Setup packaging may be created without explicit owner approval (Mandatory Pre-Release Approval Gate).**
