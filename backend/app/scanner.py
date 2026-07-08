import os
import threading
import time

from . import config, db, thumbnails

SUPPORTED_EXTENSIONS = {".pdf", ".epub", ".cbz", ".cbr", ".zip"}

# Tracks the state of a rescan_covers() run so the admin UI can poll it for progress,
# since regenerating every thumbnail can take a long time for large libraries.
_progress_lock = threading.Lock()
_progress = {"running": False, "current": 0, "total": 0, "currentFile": None, "result": None, "error": None}


def rescan_covers_progress() -> dict:
    with _progress_lock:
        return dict(_progress)


def scan(*, remove_orphan_collections: bool = False) -> dict:
    """Walk the collections/ directory tree and sync the magazines + collections tables.

    Adds new collections/magazines, updates size/mtime for existing ones, and
    removes DB rows for files that no longer exist on disk. When
    remove_orphan_collections is set, collection rows whose directory is no
    longer present under collections/ are deleted too (only safe once every
    magazine row that pointed into that directory has already been removed).
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

        for collection_dir in sorted(config.COLLECTIONS_DIR.iterdir()):
            if not collection_dir.is_dir():
                continue
            collection_name = collection_dir.name
            seen_collections.add(collection_name)

            conn.execute(
                "INSERT INTO collections (name, groupID) VALUES (?, ?) "
                "ON CONFLICT(name) DO NOTHING",
                (collection_name, config.PUBLIC_GROUP_ID),
            )

            for entry in sorted(collection_dir.rglob("*")):
                if not entry.is_file():
                    continue
                if entry.suffix.lower() not in SUPPORTED_EXTENSIONS:
                    continue

                relpath = str(entry.relative_to(config.COLLECTIONS_DIR))
                seen_relpaths.add(relpath)
                stat = entry.stat()
                title = entry.stem  # filename without extension; naming isn't consistent across
                # magazines (see CLAUDE.md), so this is just a starting point admins can rename
                dirpath = str(entry.parent.relative_to(collection_dir))
                if dirpath == ".":
                    dirpath = ""  # top level of the collection, not a subdirectory

                existing = conn.execute(
                    "SELECT id FROM magazines WHERE relpath = ?", (relpath,)
                ).fetchone()

                if existing is None:
                    conn.execute(
                        "INSERT INTO magazines "
                        "(collection, filename, relpath, dirpath, title, groupID, size, mtime) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            collection_name,
                            entry.name,
                            relpath,
                            dirpath,
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
                        (stat.st_size, stat.st_mtime, dirpath, relpath),
                    )
                    updated += 1

        # Anything in the DB that wasn't touched by the walk above was deleted/moved on disk.
        existing_rows = conn.execute("SELECT id, relpath FROM magazines").fetchall()
        for row in existing_rows:
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

    result["thumbnailsRegenerated"] = thumbnails_regenerated
    result["thumbnailsFailed"] = thumbnails_failed
    return result


def start_rescan_covers() -> bool:
    """Run rescan_covers() on a background thread so the admin UI can poll progress
    instead of blocking on one long request. Returns False if a rescan is already running.
    """
    with _progress_lock:
        if _progress["running"]:
            return False
        _progress.update(running=True, current=0, total=0, currentFile=None, result=None, error=None)

    def run():
        try:
            result = rescan_covers()
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
