"""Application-wide constants."""

from __future__ import annotations

APP_NAME = "Velo Downloader"
APP_ORG = "Velo"
APP_VERSION = "0.1.0"
APP_DESCRIPTION = "Modern desktop downloader for authorized video and playlist content."

APP_COPYRIGHT = "Copyright (c) 2026 Mohamed El-Damrawy"
APP_DEVELOPER = "Mohamed El-Damrawy"
APP_DEVELOPER_LINKEDIN = "https://www.linkedin.com/in/mohamed-eldamrawy/"
APP_DEVELOPER_GITHUB = "https://github.com/MohamedEl-Damrawy"
APP_PUBLISHER = "فردي (بدون كيان قانوني)"
APP_LICENSE = "MIT"

APP_DATA_DIR_NAME = "VeloDownloader"
DB_FILENAME = "velo.db"
LOG_DIR_NAME = "logs"
LOG_FILENAME = "velo.log"
CACHE_DIR_NAME = "cache"
TEMP_DIR_NAME = "temp"

DEFAULT_MAX_CONCURRENT_DOWNLOADS = 2
MIN_CONCURRENT_DOWNLOADS = 1
MAX_CONCURRENT_DOWNLOADS = 6

# UI palette (centralized)
COLOR_MAIN_BG = "#0B1018"
COLOR_SIDEBAR = "#101A28"
COLOR_CARD = "#152235"
COLOR_PRIMARY_TEAL = "#3B9797"
COLOR_SECONDARY_BLUE = "#16476A"
COLOR_DEEP_NAVY = "#132440"
COLOR_ACCENT_RED = "#BF092F"
COLOR_TEXT_MAIN = "#F4F7FA"
COLOR_TEXT_SECONDARY = "#91A2B5"

SETTINGS_DEFAULT_DOWNLOAD_PATH = "default_download_path"
SETTINGS_MAX_CONCURRENT_DOWNLOADS = "max_concurrent_downloads"
SETTINGS_THEME = "theme"
SETTINGS_SCHEMA_VERSION = "schema_version"
# Phase 3 engine options (DL-07/FEAT-03/FEAT-04/FEAT-05)
SETTINGS_COOKIEFILE = "ytdlp_cookiefile"
SETTINGS_PROXY = "ytdlp_proxy"
SETTINGS_SPONSORBLOCK = "sponsorblock_mark"

# FEAT-06: refuse enqueueing when the destination drive has less free space.
MIN_FREE_SPACE_BYTES = 100 * 1024 * 1024  # 100 MB

DEFAULT_SETTINGS = {
    SETTINGS_MAX_CONCURRENT_DOWNLOADS: str(DEFAULT_MAX_CONCURRENT_DOWNLOADS),
    SETTINGS_THEME: "dark",
    SETTINGS_SPONSORBLOCK: "0",
}

SUPPORTED_QUALITY_PRESETS = ["best", "1080p", "720p", "480p"]
SCHEMA_VERSION = 1
