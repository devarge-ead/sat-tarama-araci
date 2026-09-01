"""PyInstaller entry point.

This script imports the application package so that relative imports inside
``app`` resolve correctly when bundled. It should not contain any other logic.
"""

from __future__ import annotations

import os
import sys

# Make the repository root importable (also used when bundled).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.main import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())