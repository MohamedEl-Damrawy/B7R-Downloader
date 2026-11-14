"""Download status definitions and state transitions."""

from __future__ import annotations

from enum import Enum


class DownloadStatus(str, Enum):
    QUEUED = "Queued"
    EXTRACTING = "Extracting"
    DOWNLOADING = "Downloading"
    PROCESSING = "Processing"
    COMPLETED = "Completed"
    FAILED = "Failed"
    CANCELLED = "Cancelled"


TERMINAL_STATUSES = {
    DownloadStatus.COMPLETED,
    DownloadStatus.FAILED,
    DownloadStatus.CANCELLED,
}

ALLOWED_TRANSITIONS: dict[DownloadStatus, set[DownloadStatus]] = {
    DownloadStatus.QUEUED: {
        DownloadStatus.EXTRACTING,
        DownloadStatus.DOWNLOADING,
        DownloadStatus.CANCELLED,
        DownloadStatus.FAILED,
    },
    DownloadStatus.EXTRACTING: {
        DownloadStatus.DOWNLOADING,
        DownloadStatus.FAILED,
        DownloadStatus.CANCELLED,
    },
    DownloadStatus.DOWNLOADING: {
        DownloadStatus.PROCESSING,
        DownloadStatus.COMPLETED,
        DownloadStatus.FAILED,
        DownloadStatus.CANCELLED,
    },
    DownloadStatus.PROCESSING: {
        DownloadStatus.COMPLETED,
        DownloadStatus.FAILED,
        DownloadStatus.CANCELLED,
    },
    DownloadStatus.COMPLETED: set(),
    DownloadStatus.FAILED: {DownloadStatus.QUEUED},
    DownloadStatus.CANCELLED: {DownloadStatus.QUEUED},
}


def can_transition(from_status: DownloadStatus, to_status: DownloadStatus) -> bool:
    if from_status == to_status:
        return True
    return to_status in ALLOWED_TRANSITIONS.get(from_status, set())


def assert_transition(from_status: DownloadStatus, to_status: DownloadStatus) -> None:
    if not can_transition(from_status, to_status):
        raise ValueError(f"Invalid status transition: {from_status.value} -> {to_status.value}")
