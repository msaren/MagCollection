import io
from pathlib import Path

import pymupdf
from PIL import Image

from . import comics, config

THUMBNAIL_ZOOM = 0.4  # scales down the rendered first page
COMIC_EXTENSIONS = {".cbz", ".cbr", ".zip"}
COMIC_THUMB_SIZE = (480, 720)


def thumbnail_path_for(relpath: str) -> Path:
    # Flatten the relpath into a single filename (rather than mirroring subdirectories
    # under THUMBNAIL_DIR) so the cache doesn't need its own mkdir-parents dance per magazine.
    safe_name = relpath.replace("/", "__").replace("\\", "__")
    return config.THUMBNAIL_DIR / f"{safe_name}.png"


def clear_cache() -> None:
    """Delete every cached thumbnail so the next ensure_thumbnail call re-renders it."""
    for cached in config.THUMBNAIL_DIR.glob("*.png"):
        cached.unlink()


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
    doc = pymupdf.open(source_path)
    try:
        if doc.is_reflowable:
            # EPUB and similar formats have no fixed page size until laid out.
            doc.layout(width=800, height=1200, fontsize=11)
        page = doc.load_page(0)
        matrix = pymupdf.Matrix(THUMBNAIL_ZOOM, THUMBNAIL_ZOOM)
        pix = page.get_pixmap(matrix=matrix)
        pix.save(out_path)
    finally:
        doc.close()


def _render_comic_thumbnail(relpath: str, out_path: Path) -> None:
    data, _media_type = comics.read_page(relpath, 0)  # first page doubles as the cover
    image = Image.open(io.BytesIO(data))
    # PNG can't encode CMYK; everything else Pillow decodes here saves fine as-is.
    if image.mode not in ("RGB", "RGBA", "L", "P"):
        image = image.convert("RGB")
    image.thumbnail(COMIC_THUMB_SIZE)  # in place, preserves aspect ratio
    image.save(out_path, format="PNG")
