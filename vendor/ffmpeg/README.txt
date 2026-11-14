Place bundled FFmpeg and FFprobe binaries for Windows distribution here:
- ffmpeg.exe
- ffprobe.exe

The application should locate these via internal paths (see app/core/paths.py and app/engine/ffmpeg_manager.py).
Do not rely on user PATH in packaged builds. Verify on a clean Windows machine during Phase 8 (post owner approval).

