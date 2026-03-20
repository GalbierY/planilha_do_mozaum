from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parent
VENV_DIR = APP_ROOT / ".venv"
VENV_PY = VENV_DIR / "Scripts" / "python.exe"  # Windows
REQ = APP_ROOT / "requirements.txt"
STAMP = VENV_DIR / ".requirements.sha256"


def _sha256(path: Path) -> str:
    data = path.read_bytes() if path.exists() else b""
    return hashlib.sha256(data).hexdigest()


def _run(cmd: list[str], *, cwd: Path | None = None) -> None:
    p = subprocess.run(cmd, cwd=str(cwd or APP_ROOT), check=False)
    if p.returncode != 0:
        raise SystemExit(p.returncode)


def ensure_venv() -> None:
    if VENV_PY.exists():
        return
    print("Criando venv em .venv ...")
    _run([sys.executable, "-m", "venv", str(VENV_DIR)])


def ensure_requirements(*, always: bool = False) -> None:
    ensure_venv()
    req_hash = _sha256(REQ)
    prev = STAMP.read_text(encoding="utf-8").strip() if STAMP.exists() else ""
    if (not always) and prev == req_hash:
        return

    print("Instalando/atualizando dependências ...")
    _run([str(VENV_PY), "-m", "pip", "install", "-U", "pip"])
    _run([str(VENV_PY), "-m", "pip", "install", "-r", str(REQ)])
    STAMP.write_text(req_hash, encoding="utf-8")


def run_gui() -> None:
    ensure_venv()
    os.environ["PYTHONUTF8"] = "1"
    os.execv(str(VENV_PY), [str(VENV_PY), str(APP_ROOT / "gui.py")])


def main(argv: list[str]) -> None:
    always = "--always" in argv
    only_deps = "--deps-only" in argv

    ensure_requirements(always=always)
    if not only_deps:
        run_gui()


if __name__ == "__main__":
    main(sys.argv[1:])
