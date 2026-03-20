from __future__ import annotations

import argparse
import os
import re
import struct
import sys
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parent


def _png_size(png_bytes: bytes) -> tuple[int, int] | None:
    sig = b"\x89PNG\r\n\x1a\n"
    if not png_bytes.startswith(sig):
        return None
    # IHDR chunk is the first chunk: length(4) type(4) data(13) crc(4)
    if len(png_bytes) < 33:
        return None
    if png_bytes[12:16] != b"IHDR":
        return None
    w = int.from_bytes(png_bytes[16:20], "big", signed=False)
    h = int.from_bytes(png_bytes[20:24], "big", signed=False)
    if w <= 0 or h <= 0:
        return None
    return w, h


def ensure_ico(icon_png: Path, icon_ico: Path) -> bool:
    if icon_ico.exists():
        return True
    if not icon_png.exists():
        return False

    png = icon_png.read_bytes()
    size = _png_size(png)
    if size is None:
        return False
    w, h = size
    if w > 256 or h > 256:
        return False

    width_b = 0 if w == 256 else w
    height_b = 0 if h == 256 else h

    # ICO with a single PNG image.
    header = struct.pack("<HHH", 0, 1, 1)
    entry = struct.pack(
        "<BBBBHHII",
        width_b,
        height_b,
        0,  # color count
        0,  # reserved
        1,  # planes
        32,  # bit count
        len(png),
        6 + 16,  # image offset
    )
    icon_ico.parent.mkdir(parents=True, exist_ok=True)
    icon_ico.write_bytes(header + entry + png)
    return True


def write_url_shortcut(dst: Path, *, target_cmd: Path, icon_ico: Path | None) -> None:
    url = target_cmd.resolve().as_uri()
    lines = ["[InternetShortcut]", f"URL={url}"]
    if icon_ico and icon_ico.exists():
        lines.append(f"IconFile={icon_ico.resolve()}")
        lines.append("IconIndex=0")
    # Windows tends to handle BOM INI files better for unicode paths.
    dst.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")


def _desktop_dir() -> Path | None:
    userprofile = os.environ.get("USERPROFILE") or ""
    if userprofile:
        d = Path(userprofile) / "Desktop"
        if d.exists():
            return d
    return None


def _start_menu_programs_dir() -> Path | None:
    appdata = os.environ.get("APPDATA") or ""
    if appdata:
        d = Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
        if d.exists():
            return d
    return None


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")  # type: ignore[attr-defined]
            sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")  # type: ignore[attr-defined]
        except Exception:
            pass

    ap = argparse.ArgumentParser(description="Cria um atalho com ícone para abrir o SAS 🥰 | Civitas.")
    ap.add_argument("--name", default="SAS 🥰 | Civitas", help="Nome do atalho (arquivo .url).")
    ap.add_argument("--desktop", action=argparse.BooleanOptionalAction, default=True, help="Criar no Desktop.")
    ap.add_argument(
        "--start-menu",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Criar no Menu Iniciar (Programs).",
    )
    ap.add_argument("--dry-run", action="store_true", help="Não escreve arquivos; só mostra o que faria.")
    args = ap.parse_args()

    target_cmd = APP_ROOT / "start_gui.cmd"
    if not target_cmd.exists():
        raise SystemExit(f"Não encontrei {target_cmd}")

    icon_png = APP_ROOT / "assets" / "icon.png"
    icon_ico = APP_ROOT / "assets" / "icon.ico"
    if not ensure_ico(icon_png, icon_ico):
        icon_ico = None

    def safe_filename(name: str) -> str:
        # Windows filenames can't contain: <>:"/\|?*
        s = re.sub(r'[<>:"/\\\\|?*]+', "-", (name or "").strip())
        s = re.sub(r"\\s+", " ", s).strip()
        s = s.strip(". ")
        return s or "SAS Civitas"

    fname = safe_filename(args.name)
    created: list[Path] = []

    if args.desktop:
        desktop = _desktop_dir()
        if desktop:
            out = desktop / f"{fname}.url"
            if not args.dry_run:
                write_url_shortcut(out, target_cmd=target_cmd, icon_ico=icon_ico)
            created.append(out)

    if args.start_menu:
        programs = _start_menu_programs_dir()
        if programs:
            out = programs / f"{fname}.url"
            if not args.dry_run:
                write_url_shortcut(out, target_cmd=target_cmd, icon_ico=icon_ico)
            created.append(out)

    if not created:
        raise SystemExit("Não consegui detectar Desktop/Start Menu para criar o atalho.")

    print("Atalho" + (" (dry-run)" if args.dry_run else "") + ":")
    for p in created:
        print(f"- {p}")


if __name__ == "__main__":
    main()
