import os
import time

from . import config, db

SUPPORTED_EXTENSIONS = {".pdf"}


def scan() -> dict:
    """Walk the collections/ directory tree and sync the magazines + collections tables.

    Adds new collections/magazines, updates size/mtime for existing ones, and
    removes DB rows for files that no longer exist on disk.
    """
    added = 0
    updated = 0
    removed = 0
    seen_relpaths: set[str] = set()

    with db.tx() as conn:
        if not config.COLLECTIONS_DIR.exists():
            return {"added": 0, "updated": 0, "removed": 0, "collections": 0}

        for collection_dir in sorted(config.COLLECTIONS_DIR.iterdir()):
            if not collection_dir.is_dir():
                continue
            collection_name = collection_dir.name

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
                title = entry.stem

                existing = conn.execute(
                    "SELECT id FROM magazines WHERE relpath = ?", (relpath,)
                ).fetchone()

                if existing is None:
                    conn.execute(
                        "INSERT INTO magazines "
                        "(collection, filename, relpath, title, groupID, size, mtime) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (
                            collection_name,
                            entry.name,
                            relpath,
                            title,
                            config.PUBLIC_GROUP_ID,
                            stat.st_size,
                            stat.st_mtime,
                        ),
                    )
                    added += 1
                else:
                    conn.execute(
                        "UPDATE magazines SET size = ?, mtime = ? WHERE relpath = ?",
                        (stat.st_size, stat.st_mtime, relpath),
                    )
                    updated += 1

        existing_rows = conn.execute("SELECT id, relpath FROM magazines").fetchall()
        for row in existing_rows:
            if row["relpath"] not in seen_relpaths:
                conn.execute("DELETE FROM magazines WHERE id = ?", (row["id"],))
                removed += 1

        collection_count = conn.execute("SELECT COUNT(*) AS c FROM collections").fetchone()["c"]

    return {"added": added, "updated": updated, "removed": removed, "collections": collection_count}
