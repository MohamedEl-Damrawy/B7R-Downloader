"""Velo Downloader entry point."""

from __future__ import annotations

import sys

from app.bootstrap import bootstrap


def main() -> int:
    bootstrap()
    try:
        from app.application import run
        return run()
    except RuntimeError as exc:
        # Phase 1 foundation may run in environments without GUI deps installed yet.
        print(str(exc))
        return 1


if __name__ == "__main__":
    sys.exit(main())
