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
        c.executescript("""
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
                skin TEXT,
                linked_code TEXT
            );
            CREATE TABLE IF NOT EXISTS chat(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                ts REAL,
                role TEXT,
                content TEXT,
                source TEXT
            );
            CREATE TABLE IF NOT EXISTS progress(
                user_id TEXT,
                topic_id TEXT,
                task_idx INTEGER,
                correct INTEGER,
                ts REAL,
                PRIMARY KEY(user_id, topic_id, task_idx)
            );
        """)


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
        return {"plan": None, "grades": {}, "game": None, "skin": None, "linked_code": None}
    return {
        "plan": _loads(row["plan"], None),
        "grades": _loads(row["grades"], {}),
        "game": _loads(row["game"], None),
        "skin": _loads(row["skin"], None),
        "linked_code": row["linked_code"],
    }


def set_state(user_id, patch):
    cur = get_state(user_id)
    for k in ("plan", "grades", "game", "skin", "linked_code"):
        if k in patch and patch[k] is not None:
            cur[k] = patch[k]
    with _lock, _conn() as c:
        c.execute(
            "INSERT INTO state(user_id,plan,grades,game,skin,linked_code) VALUES(?,?,?,?,?,?) "
            "ON CONFLICT(user_id) DO UPDATE SET plan=excluded.plan, grades=excluded.grades, "
            "game=excluded.game, skin=excluded.skin, linked_code=excluded.linked_code",
            (
                str(user_id),
                json.dumps(cur["plan"], ensure_ascii=False),
                json.dumps(cur["grades"], ensure_ascii=False),
                json.dumps(cur["game"], ensure_ascii=False),
                json.dumps(cur["skin"], ensure_ascii=False),
                cur["linked_code"],
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
        rows = c.execute("SELECT user_id, username, created_at FROM users").fetchall()
    return [dict(r) for r in rows]


def save_progress(user_id, topic_id, task_idx, correct):
    with _lock, _conn() as c:
        c.execute(
            "INSERT OR REPLACE INTO progress(user_id,topic_id,task_idx,correct,ts) VALUES(?,?,?,?,?)",
            (str(user_id), topic_id, task_idx, int(correct), time.time()),
        )


def get_progress(user_id):
    with _lock, _conn() as c:
        rows = c.execute(
            "SELECT topic_id, task_idx, correct FROM progress WHERE user_id=?",
            (str(user_id),),
        ).fetchall()
    return [dict(r) for r in rows]


init_db()
