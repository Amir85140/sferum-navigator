import json
import sqlite3
import threading
import time

DB_PATH = "navigator.db"
_lock = threading.Lock()


def _conn():
    c = sqlite3.connect(DB_PATH, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    return c


def init_db():
    with _lock, _conn() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS users(
                user_id TEXT PRIMARY KEY,
                username TEXT,
                created_at REAL
            );
            CREATE TABLE IF NOT EXISTS state(
                user_id TEXT PRIMARY KEY,
                plan TEXT,
                grades TEXT,
                game TEXT,
                skin TEXT
            );
            CREATE TABLE IF NOT EXISTS chat(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                ts REAL,
                role TEXT,
                content TEXT,
                source TEXT
            );
            """
        )


def ensure_user(user_id, username=""):
    with _lock, _conn() as c:
        c.execute(
            "INSERT OR IGNORE INTO users(user_id,username,created_at) VALUES(?,?,?)",
            (str(user_id), username, time.time()),
        )


def _loads(s, default):
    try:
        return json.loads(s) if s else default
    except Exception:
        return default


def get_state(user_id):
    with _lock, _conn() as c:
        row = c.execute("SELECT * FROM state WHERE user_id=?", (str(user_id),)).fetchone()
    if not row:
        return {"plan": None, "grades": {}, "game": None, "skin": None}
    return {
        "plan": _loads(row["plan"], None),
        "grades": _loads(row["grades"], {}),
        "game": _loads(row["game"], None),
        "skin": _loads(row["skin"], None),
    }


def set_state(user_id, patch):
    cur = get_state(user_id)
    for k in ("plan", "grades", "game", "skin"):
        if k in patch and patch[k] is not None:
            cur[k] = patch[k]
    with _lock, _conn() as c:
        c.execute(
            "INSERT INTO state(user_id,plan,grades,game,skin) VALUES(?,?,?,?,?) "
            "ON CONFLICT(user_id) DO UPDATE SET plan=excluded.plan, grades=excluded.grades, "
            "game=excluded.game, skin=excluded.skin",
            (
                str(user_id),
                json.dumps(cur["plan"], ensure_ascii=False),
                json.dumps(cur["grades"], ensure_ascii=False),
                json.dumps(cur["game"], ensure_ascii=False),
                json.dumps(cur["skin"], ensure_ascii=False),
            ),
        )


def append_chat(user_id, role, content, source="max"):
    with _lock, _conn() as c:
        c.execute(
            "INSERT INTO chat(user_id,ts,role,content,source) VALUES(?,?,?,?,?)",
            (str(user_id), time.time(), role, content, source),
        )


def get_chat(user_id, limit=50):
    with _lock, _conn() as c:
        rows = c.execute(
            "SELECT role,content,source,ts FROM chat WHERE user_id=? ORDER BY ts DESC LIMIT ?",
            (str(user_id), limit),
        ).fetchall()
    return [dict(r) for r in reversed(rows)]


def all_users():
    with _lock, _conn() as c:
        rows = c.execute("SELECT user_id, username FROM users").fetchall()
    return [dict(r) for r in rows]


init_db()
