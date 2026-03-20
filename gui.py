from __future__ import annotations

import sys
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parent
SRC_DIR = APP_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from as_app.gui import run  # noqa: E402


if __name__ == "__main__":
    run()
