import io
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image

from . import comics, config

THUMBNAIL_ZOOM = 0.4  # scales down the rendered first page
COMIC_EXTENSIONS = {".cbz", ".cbr", ".zip"}
COMIC_THUMB_SIZE = (480, 720)


def thumbnail_path_for(relpath: str) -> Path:
    safe_name = relpath.replace("/", "__").replace("\\", "__")
    return config.THUMBNAIL_DIR / f"{safe_name}.png"


def ensure_thumbnail(relpath: str) -> Path:
    """Render and cache the first page of the magazine at relpath as a PNG. Returns the cached path."""
    out_path = thumbnail_path_for(relpath)
    if out_path.exists():
        return out_path

    source_path = config.COLLECTIONS_DIR / relpath
    if source_path.suffix.lower() in COMIC_EXTENSIONS:
        _render_comic_thumbnail(relpath, out_path)
    else:
        _render_document_thumbnail(source_path, out_path)

    return out_path


def _render_document_thumbnail(source_path: Path, out_path: Path) -> None:
    doc = fitz.open(source_path)
    try:
        if doc.is_reflowable:
            # EPUB and similar formats have no fixed page size until laid out.
            doc.layout(width=800, height=1200, fontsize=11)
        page = doc.load_page(0)
        matrix = fitz.Matrix(THUMBNAIL_ZOOM, THUMBNAIL_ZOOM)
        pix = page.get_pixmap(matrix=matrix)
        pix.save(out_path)
    finally:
        doc.close()


def _render_comic_thumbnail(relpath: str, out_path: Path) -> None:
    data, _media_type = comics.read_page(relpath, 0)
    image = Image.open(io.BytesIO(data))
    if image.mode not in ("RGB", "RGBA", "L", "P"):
        image = image.convert("RGB")
    image.thumbnail(COMIC_THUMB_SIZE)
    image.save(out_path, format="PNG")
