"""Entry point for the frozen PyInstaller executable.

When invoked without arguments → opens the desktop UI.
When invoked with arguments    → delegates to the normal CLI.
"""

from __future__ import annotations

import sys

from app.main import main


def launcher() -> int:
    if len(sys.argv) <= 1:
        # No sub-command given → default to the UI
        return main(["ui"])
    return main(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(launcher())
