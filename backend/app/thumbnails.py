import io
from pathlib import Path
import os
import zipfile
from lxml import etree
import pymupdf
from PIL import Image

from . import comics, config

THUMBNAIL_ZOOM = 0.4  # scales down the rendered first page
COMIC_EXTENSIONS = {".cbz", ".cbr", ".zip", ".rar", ".7z"}  # archive formats handled by the comics module
COMIC_THUMB_SIZE = (480, 720)  # max (width, height) comic/epub cover thumbnails are downscaled to


# Let's define the required XML namespaces
namespaces = {
   "calibre":"http://calibre.kovidgoyal.net/2009/metadata",
   "dc":"http://purl.org/dc/elements/1.1/",
   "dcterms":"http://purl.org/dc/terms/",
   "opf":"http://www.idpf.org/2007/opf",
   "u":"urn:oasis:names:tc:opendocument:xmlns:container",
   "xsi":"http://www.w3.org/2001/XMLSchema-instance",
   "xhtml":"http://www.w3.org/1999/xhtml"
}


def get_epub_cover(epub_path):
    ''' Return the cover image file from an epub archive. '''
    
    # We open the epub archive using zipfile.ZipFile():
    with zipfile.ZipFile(epub_path) as z:
    
        # We load "META-INF/container.xml" using lxml.etree.fromString():
        t = etree.fromstring(z.read("META-INF/container.xml"))
        # We use xpath() to find the attribute "full-path":
        '''
        <container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
          <rootfiles>
            <rootfile full-path="OEBPS/content.opf" ... />
          </rootfiles>
        </container>
        '''
        rootfile_path =  t.xpath("/u:container/u:rootfiles/u:rootfile",
                                             namespaces=namespaces)[0].get("full-path")
        
        # We load the "root" file, indicated by the "full_path" attribute of "META-INF/container.xml", using lxml.etree.fromString():
        t = etree.fromstring(z.read(rootfile_path))

        cover_href = None
        try:
            # For EPUB 2.0, we use xpath() to find a <meta> 
            # named "cover" and get the attribute "content":
            '''
            <metadata xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:opf="http://www.idpf.org/2007/opf">
              ...
              <meta content="my-cover-image" name="cover"/>
              ...
            </metadata>            '''

            cover_id = t.xpath("//opf:metadata/opf:meta[@name='cover']",
                                      namespaces=namespaces)[0].get("content")
            # Next, we use xpath() to find the <item> (in <manifest>) with this id 
            # and get the attribute "href":
            '''
            <manifest>
                ...
                <item id="my-cover-image" href="images/978.jpg" ... />
                ... 
            </manifest>
            '''
            cover_href = t.xpath("//opf:manifest/opf:item[@id='" + cover_id + "']",
                                 namespaces=namespaces)[0].get("href")
        except IndexError:
            pass
        
        if not cover_href:
            # For EPUB 3.0, We use xpath to find the <item> (in <manifest>) that
            # has properties='cover-image' and get the attribute "href":
            '''
            <manifest>
              ...
              <item href="images/cover.png" id="cover-img" media-type="image/png" properties="cover-image"/>
              ...
            </manifest>
            '''
            try:
                cover_href = t.xpath("//opf:manifest/opf:item[@properties='cover-image']",
                                     namespaces=namespaces)[0].get("href")
            except IndexError:
                pass

        if not cover_href:
            # Some EPUB files do not declare explicitly a cover image.
            # Instead, they use an "<img src=''>" inside the first xhmtl file.
            try:
                # The <spine> is a list that defines the linear reading order
                # of the content documents of the book. The first item in the  
                # list is the first item in the book.  
                '''
                <spine toc="ncx">
                  <itemref idref="cover"/>
                  <itemref idref="nav"/>
                  <itemref idref="s04"/>
                </spine>
                '''
                cover_page_id = t.xpath("//opf:spine/opf:itemref",
                                        namespaces=namespaces)[0].get("idref")
                # Next, we use xpath() to find the item (in manifest) with this id 
                # and get the attribute "href":
                cover_page_href = t.xpath("//opf:manifest/opf:item[@id='" + cover_page_id + "']",
                                          namespaces=namespaces)[0].get("href")
                # In order to get the full path for the cover page,
                # we have to join rootfile_path and cover_page_href:
                cover_page_path = os.path.join(os.path.dirname(rootfile_path), cover_page_href)
                print("Path of cover page found: " + cover_page_path)     
                # We try to find the <img> and get the "src" attribute:
                t = etree.fromstring(z.read(cover_page_path))              
                cover_href = t.xpath("//xhtml:img", namespaces=namespaces)[0].get("src")
            except IndexError:
                pass

        if not cover_href:
            print("Cover image not found.")  
            return None

        # In order to get the full path for the cover image,
        # we have to join rootfile_path and cover_href:
        cover_path = os.path.join(os.path.dirname(rootfile_path), cover_href)
                
        # We return the image
        return z.open(cover_path)


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
        # Already cached from a previous call; skip the (relatively expensive) render.
        return out_path

    source_path = config.COLLECTIONS_DIR / relpath
    if source_path.suffix.lower() in COMIC_EXTENSIONS:
        # Comic archives don't have "pages" pymupdf understands, so they go through
        # the comics module's own page reader instead of pymupdf.
        _render_comic_thumbnail(relpath, out_path)
    else:
        _render_document_thumbnail(source_path, out_path)

    return out_path


def _render_document_thumbnail(source_path: Path, out_path: Path) -> None:
    """Render a thumbnail for a PDF/EPUB/etc. document handled directly by pymupdf."""
    extension=str(source_path.suffix).lower()
    if extension.endswith('epub'):
        # pymupdf can open epub, but its rendering doesn't reliably surface the
        # declared cover image, so we extract it ourselves via get_epub_cover().
        cover = get_epub_cover(source_path)
        image = Image.open(cover)
        image.thumbnail(COMIC_THUMB_SIZE)  # in place, preserves aspect ratio
        image.save(out_path, format="PNG")
    else:
        doc = pymupdf.open(source_path)
        try:
            if doc.is_reflowable:
                # EPUB and similar formats have no fixed page size until laid out.
                doc.layout(width=800, height=1200, fontsize=11)
            page = doc.load_page(0)
            # Render at THUMBNAIL_ZOOM scale rather than full resolution, then rasterize.
            matrix = pymupdf.Matrix(THUMBNAIL_ZOOM, THUMBNAIL_ZOOM)
            pix = page.get_pixmap(matrix=matrix)
            pix.save(out_path)
        finally:
            doc.close()


def _render_comic_thumbnail(relpath: str, out_path: Path) -> None:
    """Render a thumbnail for a comic archive (cbz/cbr/zip/rar/7z) using its first page as the cover."""
    data, _media_type = comics.read_page(relpath, 0)  # first page doubles as the cover
    image = Image.open(io.BytesIO(data))
    # PNG can't encode CMYK; everything else Pillow decodes here saves fine as-is.
    if image.mode not in ("RGB", "RGBA", "L", "P"):
        image = image.convert("RGB")
    image.thumbnail(COMIC_THUMB_SIZE)  # in place, preserves aspect ratio
    image.save(out_path, format="PNG")
