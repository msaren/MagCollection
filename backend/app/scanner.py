import os
import threading
import time

from . import config, db, thumbnails

SUPPORTED_EXTENSIONS = {".pdf", ".epub", ".cbz", ".cbr", ".zip"}

# Tracks the state of a rescan_covers()/rescan_collection_covers() run so the admin UI
# can poll it for progress, since regenerating thumbnails can take a long time. "collection"
# is None for a full-library rescan, or a name for a single-collection rescan; only one
# rescan of either kind can run at a time.
_progress_lock = threading.Lock()
_progress = {
    "running": False,
    "current": 0,
    "total": 0,
    "currentFile": None,
    "collection": None,
    "path": None,
    "result": None,
    "error": None,
}


def rescan_covers_progress() -> dict:
    with _progress_lock:
        return dict(_progress)


def _safe_subdir(base, relative: str):
    """Joins a `/`-separated subdirectory path onto `base`, rejecting anything
    that could escape it (`..` segments). Returns None if `relative` is unsafe."""
    parts = [p for p in relative.split("/") if p not in ("", ".")]
    if any(p == ".." for p in parts):
        return None
    return base.joinpath(*parts) if parts else base


def scan(*, remove_orphan_collections: bool = False, collection_name: str | None = None, dirpath: str | None = None) -> dict:
    """Walk the collections/ directory tree and sync the magazines + collections tables.

    Adds new collections/magazines, updates size/mtime for existing ones, and
    removes DB rows for files that no longer exist on disk. When
    remove_orphan_collections is set, collection rows whose directory is no
    longer present under collections/ are deleted too (only safe once every
    magazine row that pointed into that directory has already been removed).

    Pass collection_name (and optionally dirpath, a subdirectory within it) to
    scope the walk to just that directory: only files under it are added,
    updated, or removed as missing; every other collection/file is left alone.
    remove_orphan_collections requires the unscoped, whole-tree scan.
    """
    added = 0
    updated = 0
    removed = 0
    removed_collections = 0
    seen_relpaths: set[str] = set()
    seen_collections: set[str] = set()

    with db.tx() as conn:
        if not config.COLLECTIONS_DIR.exists():
            return {"added": 0, "updated": 0, "removed": 0, "removedCollections": 0, "collections": 0}

        if collection_name is not None:
            collection_dirs = [config.COLLECTIONS_DIR / collection_name]
        else:
            collection_dirs = [d for d in sorted(config.COLLECTIONS_DIR.iterdir()) if d.is_dir()]

        for collection_dir in collection_dirs:
            if not collection_dir.is_dir():
                continue
            cname = collection_dir.name
            seen_collections.add(cname)

            conn.execute(
                "INSERT INTO collections (name, groupID) VALUES (?, ?) "
                "ON CONFLICT(name) DO NOTHING",
                (cname, config.PUBLIC_GROUP_ID),
            )

            walk_root = collection_dir
            if dirpath:
                walk_root = _safe_subdir(collection_dir, dirpath)
                if walk_root is None:
                    continue

            if not walk_root.is_dir():
                # The scoped subdirectory is gone; any DB rows still pointing into it are
                # caught as missing by the removal step below since nothing was seen for them.
                continue

            for entry in sorted(walk_root.rglob("*")):
                if not entry.is_file():
                    continue
                if entry.suffix.lower() not in SUPPORTED_EXTENSIONS:
                    continue

                relpath = str(entry.relative_to(config.COLLECTIONS_DIR))
                seen_relpaths.add(relpath)
                stat = entry.stat()
                title = entry.stem  # filename without extension; naming isn't consistent across
                # magazines (see CLAUDE.md), so this is just a starting point admins can rename
                entry_dirpath = str(entry.parent.relative_to(collection_dir))
                if entry_dirpath == ".":
                    entry_dirpath = ""  # top level of the collection, not a subdirectory

                existing = conn.execute(
                    "SELECT id FROM magazines WHERE relpath = ?", (relpath,)
                ).fetchone()

                if existing is None:
                    conn.execute(
                        "INSERT INTO magazines "
                        "(collection, filename, relpath, dirpath, title, groupID, size, mtime) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            cname,
                            entry.name,
                            relpath,
                            entry_dirpath,
                            title,
                            config.PUBLIC_GROUP_ID,
                            stat.st_size,
                            stat.st_mtime,
                        ),
                    )
                    added += 1
                else:
                    conn.execute(
                        "UPDATE magazines SET size = ?, mtime = ?, dirpath = ? WHERE relpath = ?",
                        (stat.st_size, stat.st_mtime, entry_dirpath, relpath),
                    )
                    updated += 1

        # Anything within scope that wasn't touched by the walk above was deleted/moved on
        # disk. When scoped to a collection (and maybe a subdirectory within it), only rows
        # in that scope are considered, so files elsewhere are never touched.
        if collection_name is not None:
            existing_rows = conn.execute(
                "SELECT id, relpath, dirpath FROM magazines WHERE collection = ?", (collection_name,)
            ).fetchall()
        else:
            existing_rows = conn.execute("SELECT id, relpath, dirpath FROM magazines").fetchall()

        for row in existing_rows:
            if collection_name is not None and dirpath:
                row_dirpath = row["dirpath"] or ""
                in_scope = row_dirpath == dirpath or row_dirpath.startswith(f"{dirpath}/")
                if not in_scope:
                    continue
            if row["relpath"] not in seen_relpaths:
                conn.execute("DELETE FROM magazines WHERE id = ?", (row["id"],))
                removed += 1

        if remove_orphan_collections:
            # Safe only because every magazine row under a removed directory was already
            # deleted above, in this same transaction, so the FOREIGN KEY check won't trip.
            collection_rows = conn.execute("SELECT name FROM collections").fetchall()
            for row in collection_rows:
                if row["name"] not in seen_collections:
                    conn.execute("DELETE FROM collections WHERE name = ?", (row["name"],))
                    removed_collections += 1

        collection_count = conn.execute("SELECT COUNT(*) AS c FROM collections").fetchone()["c"]

    return {
        "added": added,
        "updated": updated,
        "removed": removed,
        "removedCollections": removed_collections,
        "collections": collection_count,
    }


def _regenerate_thumbnails(relpaths: list[str]) -> dict:
    """Render (or re-render) the thumbnail for each relpath, tracking progress as it goes."""
    thumbnails_regenerated = 0
    thumbnails_failed = 0
    with _progress_lock:
        _progress["total"] = len(relpaths)
        _progress["current"] = 0
    for relpath in relpaths:
        with _progress_lock:
            _progress["currentFile"] = relpath
        try:
            thumbnails.ensure_thumbnail(relpath)
            thumbnails_regenerated += 1
        except Exception:
            thumbnails_failed += 1
        with _progress_lock:
            _progress["current"] += 1
    return {"thumbnailsRegenerated": thumbnails_regenerated, "thumbnailsFailed": thumbnails_failed}


def rescan_covers() -> dict:
    """Full rescan: sync the DB (including dropping orphaned collections), then
    wipe and regenerate the thumbnail cache for every magazine still present.

    Updates the module-level progress state as it goes so callers running this
    on a background thread (see start_rescan_covers) can be polled for status.
    """
    result = scan(remove_orphan_collections=True)
    thumbnails.clear_cache()
    conn = db.get_conn()
    relpaths = [row["relpath"] for row in conn.execute("SELECT relpath FROM magazines").fetchall()]
    result.update(_regenerate_thumbnails(relpaths))
    return result


def rescan_collection_covers(collection_name: str, dirpath: str | None = None) -> dict:
    """Regenerate thumbnails for one collection, optionally scoped to just a subdirectory
    within it: re-syncs the DB for that scope only, then wipes and re-renders the covers
    within it, leaving every other collection/directory untouched.
    """
    scan(collection_name=collection_name, dirpath=dirpath)
    conn = db.get_conn()
    rows = conn.execute(
        "SELECT relpath, dirpath FROM magazines WHERE collection = ?", (collection_name,)
    ).fetchall()
    if dirpath:
        rows = [
            row
            for row in rows
            if (row["dirpath"] or "") == dirpath or (row["dirpath"] or "").startswith(f"{dirpath}/")
        ]
    relpaths = [row["relpath"] for row in rows]

    for relpath in relpaths:
        path = thumbnails.thumbnail_path_for(relpath)
        if path.exists():
            path.unlink()

    result = {"collection": collection_name, "path": dirpath}
    result.update(_regenerate_thumbnails(relpaths))
    return result


def start_rescan_covers(collection_name: str | None = None, dirpath: str | None = None) -> bool:
    """Run a full or single-collection (optionally subdirectory-scoped) rescan on a
    background thread so the admin UI can poll progress instead of blocking on one long
    request. Returns False if a rescan (of any kind) is already running.
    """
    with _progress_lock:
        if _progress["running"]:
            return False
        _progress.update(
            running=True,
            current=0,
            total=0,
            currentFile=None,
            collection=collection_name,
            path=dirpath,
            result=None,
            error=None,
        )

    def run():
        try:
            result = (
                rescan_collection_covers(collection_name, dirpath) if collection_name else rescan_covers()
            )
            with _progress_lock:
                _progress["result"] = result
        except Exception as e:
            with _progress_lock:
                _progress["error"] = str(e)
        finally:
            with _progress_lock:
                _progress["running"] = False
                _progress["currentFile"] = None

    threading.Thread(target=run, daemon=True).start()
    return True
