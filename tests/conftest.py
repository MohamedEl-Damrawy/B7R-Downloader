"""Pytest configuration for foundation tests."""

from __future__ import annotations

import os


def pytest_configure():
    # Ensure Qt tests (future) can run headless in CI/dev environments when added.
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
