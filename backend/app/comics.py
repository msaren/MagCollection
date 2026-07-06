"""Read pages out of comic archives (.cbz/.zip and .cbr).

CBZ/ZIP are plain zip files, handled with the stdlib zipfile module. CBR is RAR,
which needs a proprietary decompressor that no pure-Python library provides
reliably (the `rarfile` package was tried and found to mis-extract entries
against its own bsdtar backend) - so .cbr shells out to whichever external
archive tool is available: `unrar` if installed, else `bsdtar` (libarchive,
preinstalled on macOS and widely available on Linux).
"""

import re
import shutil
import subprocess
import zipfile
from pathlib import Path

from . import config

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}

IMAGE_MEDIA_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
}

# Resolved once at import time. shutil.which() correctly returns None for a broken
# symlink (e.g. a stale `unrar` cask install), so this won't pick a dead binary.
RAR_TOOL = shutil.which("unrar") or shutil.which("bsdtar")


def _natural_key(name: str) -> list:
    """Sort key so 'page_2.jpg' < 'page_10.jpg' instead of ordering by character code."""
    return [int(p) if p.isdigit() else p.lower() for p in re.split(r"(\d+)", name)]


def _is_image(name: str) -> bool:
    return Path(name).suffix.lower() in IMAGE_EXTENSIONS


def _list_rar_pages(path: Path) -> list[str]:
    """List entry names via unrar's "list bare" mode, or bsdtar's -t (list) as a fallback."""
    if RAR_TOOL is None:
        raise RuntimeError("No archive tool (unrar or bsdtar) found on PATH for CBR support")
    if RAR_TOOL.endswith("unrar"):
        out = subprocess.run(
            [RAR_TOOL, "lb", "-p-", str(path)], capture_output=True, check=True, text=True
        ).stdout
    else:
        out = subprocess.run(
            [RAR_TOOL, "-tf", str(path)], capture_output=True, check=True, text=True
        ).stdout
    names = [line for line in out.splitlines() if line and _is_image(line)]
    return sorted(names, key=_natural_key)


def _read_rar_page(path: Path, name: str) -> bytes:
    """Extract a single entry straight to stdout instead of unpacking the whole archive to disk."""
    if RAR_TOOL is None:
        raise RuntimeError("No archive tool (unrar or bsdtar) found on PATH for CBR support")
    if RAR_TOOL.endswith("unrar"):
        cmd = [RAR_TOOL, "p", "-inul", "-p-", str(path), name]
    else:
        cmd = [RAR_TOOL, "-xOf", str(path), name]
    return subprocess.run(cmd, capture_output=True, check=True).stdout


def list_pages(relpath: str) -> list[str]:
    """Return the natural-sorted list of image entry names inside a comic archive."""
    path = config.COLLECTIONS_DIR / relpath
    suffix = path.suffix.lower()
    if suffix == ".cbr":
        return _list_rar_pages(path)
    with zipfile.ZipFile(path) as zf:
        names = [info.filename for info in zf.infolist() if not info.is_dir() and _is_image(info.filename)]
        return sorted(names, key=_natural_key)


def read_page(relpath: str, index: int) -> tuple[bytes, str]:
    """Return (bytes, media_type) for the page at `index` (0-based) in a comic archive."""
    path = config.COLLECTIONS_DIR / relpath
    pages = list_pages(relpath)
    if index < 0 or index >= len(pages):
        raise IndexError(f"Page {index} out of range (0-{len(pages) - 1})")
    name = pages[index]
    media_type = IMAGE_MEDIA_TYPES.get(Path(name).suffix.lower(), "application/octet-stream")

    if path.suffix.lower() == ".cbr":
        return _read_rar_page(path, name), media_type
    with zipfile.ZipFile(path) as zf:
        return zf.read(name), media_type
