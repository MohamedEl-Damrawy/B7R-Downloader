# Release Readiness Checklist (Pre-Packaging)

> **Status:** IN PROGRESS — owner identity/license and packaging approval recorded; packaging tools/artifacts and clean-machine test pending.
> **Owner approval recorded (explicit):** "الناشر: فردي (بدون كيان قانوني) | رخصة التطبيق: MIT | موافقة نهائية: أوافق صراحة على إنشاء Setup و ZIP باستخدام pyside6-deploy، مع اختصار سطح المكتب وقائمة ابدأ، وإجراء اختبار على جهاز نظيف"
> **Gate note:** Packaging actions are permitted per above approval, but release artifacts must not be distributed until compliance obligations for bundled third-party components are satisfied for the exact package.

## 1. Implementation & Quality
- [x] Core automated/runtime checks in dev env: PySide6/yt-dlp installed, FFmpeg/FFprobe bundled in `vendor/ffmpeg` and resolved, GUI offscreen smoke OK, real download+merge smoke (network) OK.
- [x] Unit/integration/GUI tests passing in dev env: `python -m pytest -q` → **23 passed** (includes `tests/gui/`, `tests/integration/`, network-marked download smoke).
- [ ] **Manual interactive verification on Windows (human):** full UX flow, metadata extraction, single/playlist selection & download, queue/progress/cancel/retry, persistence/history, settings, About/Legal dialogs, error states, thumbnail behavior in list views.
- [ ] Lint/typecheck (if configured) passing.

## 2. Runtime & Packaging Prereqs
- [x] PySide6, yt-dlp, FFmpeg/FFprobe available and correctly resolved (bundled paths preferred by app when present).
- [x] Mutable data stored under `%LOCALAPPDATA%\VeloDownloader` (per app design/config).
- [x] `pyside6-deploy` CLI detected (`Scripts/pyside6-deploy.exe`).
- [ ] **Nuitka/pyside6-deploy deployment dependencies installed and configured** (project `pysidedeploy.spec` not yet created; `python -m nuitka`/nuitka package availability to confirm during deploy).
- [ ] **Inno Setup compiler (`iscc`) not detected** — required to build `Setup.exe` from `scripts/create_installer.iss` (or alternative installer tool must be chosen/installed).
- [ ] No console windows during normal GUI/FFmpeg operations — verify in packaged run.
- [ ] **Clean-machine test executed** (approved; not yet performed).

## 3. Identity & Branding
- [x] App name (current): Velo Downloader.
- [x] Developer: Mohamed El-Damrawy (LinkedIn/GitHub provided).
- [x] Copyright: **Copyright (c) 2026 Mohamed El-Damrawy**.
- [x] Publisher/Legal entity: **فردي (بدون كيان قانوني)**.
- [x] Application license: **MIT** (`LICENSE`, `pyproject.toml`, UI/legal notices updated).
- [x] Packaging/distribution intent approved: **Setup + ZIP via pyside6-deploy, Desktop + Start Menu shortcuts**.
- [ ] Version and naming scheme confirmed for release.
- [ ] Final logo / Windows `.ico` icon provided or approved (required for polished EXE/Setup/shortcuts).
- [ ] Website/contact info (if any) confirmed.

## 4. Legal & Compliance (audit required for exact release package)
- [x] Notices updated to reflect observed behavior and declared identity/license: `licenses/THIRD_PARTY_NOTICES.txt`, `resources/legal/privacy_notice.txt`, `resources/legal/usage_notice.txt`.
- [x] Components identified (dev/bundled): PySide6/Qt/shiboken6 6.12.0 (LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only per metadata), yt-dlp 2026.10.26 (Unlicense per metadata), FFmpeg/FFprobe 8.1.2 full static build from gyan.dev (**GPLv3** stated by bundled README) in `vendor/ffmpeg/`.
- [x] Copied available license/readme artifacts into `licenses/third_party/` — **not sufficient alone for distribution compliance**.
- [ ] **Compatibility/compliance decision documented:** MIT app code with bundled GPLv3 FFmpeg in distributed package (ensure all GPLv3 obligations met for shipped FFmpeg build and review overall distribution terms).
- [ ] Qt/PySide6 redistribution option chosen and all obligations satisfied (notices, full texts, LGPL relinking/replaceability or chosen path as applicable).
- [ ] FFmpeg GPLv3 redistribution obligations fully satisfied for exact shipped binaries/config (complete corresponding source/offer, full license texts, notices).
- [ ] Final dependency/bundled-binary audit for the exact release package (Qt modules/plugins, Python runtime, all bundled files).
- [ ] Privacy/usage notices finalized to match shipped behavior.

## 5. Owner Approval
- [x] **Explicit owner approval received** for: Setup + ZIP, pyside6-deploy, Desktop + Start Menu shortcuts, clean-machine test.
- [x] Publisher and app license declared by owner.

## 6. Packaging (IN PROGRESS per approval)
- [ ] Create/verify `pysidedeploy.spec` and include `resources/`, `vendor/ffmpeg/`, `licenses/` and required data in bundle.
- [ ] Produce deploy build with `pyside6-deploy` (no release artifacts created yet).
- [ ] Create **ZIP** from packaged output.
- [ ] Create **Setup.exe** (requires Inno Setup or alternative) with Desktop + Start Menu shortcuts.
- [ ] Execute clean-machine test and record results.
- [ ] Inspect/report release artifacts. **No EXE/Setup/ZIP created in this step.**
