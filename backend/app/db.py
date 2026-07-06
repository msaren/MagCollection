import sqlite3
import threading
from contextlib import contextmanager

from . import config

_local = threading.local()  # one sqlite3 connection per thread; FastAPI's thread pool needs this

SCHEMA = """
CREATE TABLE IF NOT EXISTS collections (
    name TEXT PRIMARY KEY,
    groupID TEXT NOT NULL DEFAULT 'public',
    icon TEXT
);

CREATE TABLE IF NOT EXISTS magazines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    collection TEXT NOT NULL,
    filename TEXT NOT NULL,
    relpath TEXT NOT NULL UNIQUE,
    dirpath TEXT NOT NULL DEFAULT '',
    title TEXT NOT NULL,
    userID TEXT,
    groupID TEXT NOT NULL DEFAULT 'public',
    size INTEGER,
    mtime REAL,
    thumbnail TEXT,
    last_read REAL,
    FOREIGN KEY (collection) REFERENCES collections(name)
);

CREATE INDEX IF NOT EXISTS idx_magazines_collection ON magazines(collection);
"""

INDEX_SCHEMA = """
CREATE INDEX IF NOT EXISTS idx_magazines_dirpath ON magazines(collection, dirpath);
"""


def get_conn() -> sqlite3.Connection:
    conn = getattr(_local, "conn", None)
    if conn is None:
        conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        _local.conn = conn
    return conn


def init_db() -> None:
    """Create the schema if missing, then apply column additions for existing DBs.

    CREATE TABLE IF NOT EXISTS won't add columns to a table that already exists, so
    each new column added after the initial release needs its own ALTER TABLE guard
    here rather than just being added to SCHEMA above.
    """
    conn = get_conn()
    conn.executescript(SCHEMA)
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(magazines)")}
    if "dirpath" not in columns:
        conn.execute("ALTER TABLE magazines ADD COLUMN dirpath TEXT NOT NULL DEFAULT ''")
    if "last_read" not in columns:
        conn.execute("ALTER TABLE magazines ADD COLUMN last_read REAL")
    conn.executescript(INDEX_SCHEMA)
    conn.commit()


@contextmanager
def tx():
    """Wrap a block of writes in a commit/rollback pair around the thread-local connection."""
    conn = get_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
