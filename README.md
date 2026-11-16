# Velo Downloader

A modern Windows desktop app for downloading videos and playlists, built with PySide6 and yt-dlp.

## Download

Get the latest version from the [Releases page](https://github.com/MohamedEl-Damrawy/B7R-Downloader/releases):

- **Setup (recommended):** run `VeloDownloader-<version>-setup.exe` — installs with Start Menu and Desktop shortcuts.
- **Portable ZIP:** extract anywhere and run `VeloDownloader.exe`.

The app can also check for updates itself: **Settings → Check App Updates**.

## Features

- Video and playlist downloads with quality selection (up to best available)
- Audio-only presets (MP3 / M4A)
- Optional subtitles, embedded metadata and thumbnail, SponsorBlock marking
- Playlist inspector: see all entries and pick exactly the items you want
- Live queue with per-item progress, cancel, retry, and searchable history
- Dark and light themes; interface in **English** and **العربية (RTL)**
- Optional cookies file and proxy for content that requires them

## Requirements

- Windows 10 or later (64-bit). The installers bundle everything — no Python required.

## Running from source

```bash
git clone https://github.com/MohamedEl-Damrawy/B7R-Downloader.git
cd B7R-Downloader
pip install -r requirements.txt
python main.py
```

FFmpeg/FFprobe: put the binaries in `vendor/ffmpeg/` (see `vendor/ffmpeg/README.txt`) or have them on PATH.

## Legal

- Licensed under [MIT](LICENSE).
- Third-party components (Qt/PySide6, yt-dlp, FFmpeg, Tajawal font) keep their own licenses — see `licenses/THIRD_PARTY_NOTICES.txt`.
- Use only with content you have the right to download. No DRM or paywall circumvention.
