import sqlite3
import threading
from contextlib import contextmanager

from . import config

_local = threading.local()

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
    title TEXT NOT NULL,
    userID TEXT,
    groupID TEXT NOT NULL DEFAULT 'public',
    size INTEGER,
    mtime REAL,
    thumbnail TEXT,
    FOREIGN KEY (collection) REFERENCES collections(name)
);

CREATE INDEX IF NOT EXISTS idx_magazines_collection ON magazines(collection);
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
    conn = get_conn()
    conn.executescript(SCHEMA)
    conn.commit()


@contextmanager
def tx():
    conn = get_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
