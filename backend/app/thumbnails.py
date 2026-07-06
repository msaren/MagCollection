from pathlib import Path

import fitz  # PyMuPDF

from . import config

THUMBNAIL_ZOOM = 0.4  # scales down the rendered first page


def thumbnail_path_for(relpath: str) -> Path:
    safe_name = relpath.replace("/", "__").replace("\\", "__")
    return config.THUMBNAIL_DIR / f"{safe_name}.png"


def ensure_thumbnail(relpath: str) -> Path:
    """Render and cache the first page of the PDF at relpath as a PNG. Returns the cached path."""
    out_path = thumbnail_path_for(relpath)
    if out_path.exists():
        return out_path

    source_path = config.COLLECTIONS_DIR / relpath
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

    return out_path
