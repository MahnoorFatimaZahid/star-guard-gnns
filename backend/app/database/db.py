import sqlite3
import json
import contextlib
from app.config import settings


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    handle TEXT NOT NULL,
    created_at TEXT,
    followers INTEGER,
    following INTEGER,
    public_repos INTEGER,
    public_gists INTEGER,
    commits INTEGER,
    score REAL,
    level TEXT,
    tags TEXT,
    age_label TEXT,
    links INTEGER,
    why TEXT,
    factors TEXT,
    peers TEXT
);

CREATE TABLE IF NOT EXISTS repos (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    url TEXT,
    created_at TEXT,
    pushed_at TEXT,
    language TEXT,
    description TEXT,
    stars INTEGER,
    score REAL,
    color TEXT,
    tags TEXT,
    flagged_count INTEGER,
    sparkline_path TEXT
);

CREATE TABLE IF NOT EXISTS stars (
    user_id TEXT,
    repo_id TEXT,
    starred_at TEXT
);

CREATE TABLE IF NOT EXISTS follows (
    follower_id TEXT,
    following_id TEXT
);

CREATE TABLE IF NOT EXISTS clusters (
    id TEXT PRIMARY KEY,
    tag TEXT,
    name TEXT,
    detail TEXT,
    size INTEGER,
    members TEXT,
    risk_level TEXT
);

CREATE TABLE IF NOT EXISTS model_scores (
    label TEXT PRIMARY KEY,
    val TEXT,
    width TEXT,
    color TEXT,
    is_current INTEGER,
    precision REAL,
    recall REAL,
    f1 REAL,
    auc REAL
);

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE INDEX IF NOT EXISTS idx_stars_repo ON stars(repo_id);
CREATE INDEX IF NOT EXISTS idx_stars_user ON stars(user_id);
"""


@contextlib.contextmanager
def get_conn():
    conn = sqlite3.connect(settings.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)


def wipe_db():
    with get_conn() as conn:
        for t in ["users", "repos", "stars", "follows", "clusters", "model_scores", "meta"]:
            conn.execute(f"DELETE FROM {t}")


def set_meta(key, value):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO meta (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, json.dumps(value)),
        )


def get_meta(key, default=None):
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return json.loads(row["value"]) if row else default
