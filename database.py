# ─── database.py ──────────────────────────────────────────────────────────────
import sqlite3
import random
import string
from datetime import datetime
from contextlib import contextmanager

DB_PATH = "greenpeace.db"


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as c:
        c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            tg_id        INTEGER PRIMARY KEY,
            short_id     TEXT    UNIQUE,
            username     TEXT,
            full_name    TEXT,
            source       TEXT,
            want_to_buy  TEXT,
            status       TEXT    DEFAULT 'pending',   -- pending | approved | blocked
            balance      REAL    DEFAULT 0,
            orders_count INTEGER DEFAULT 0,
            surcharge    REAL    DEFAULT 1.5,
            reject_count INTEGER DEFAULT 0,
            created_at   TEXT    DEFAULT (datetime('now'))
        )""")
        c.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            tg_id        INTEGER,
            description  TEXT,
            amount       REAL,
            status       TEXT DEFAULT 'pending',      -- pending | approved | rejected
            created_at   TEXT DEFAULT (datetime('now'))
        )""")
        c.execute("""
        CREATE TABLE IF NOT EXISTS promo_codes (
            code         TEXT PRIMARY KEY,
            amount       REAL,
            activations  INTEGER,
            used         INTEGER DEFAULT 0,
            created_at   TEXT DEFAULT (datetime('now'))
        )""")
        c.execute("""
        CREATE TABLE IF NOT EXISTS promo_uses (
            tg_id INTEGER,
            code  TEXT,
            PRIMARY KEY (tg_id, code)
        )""")
        c.execute("""
        CREATE TABLE IF NOT EXISTS bot_state (
            key   TEXT PRIMARY KEY,
            value TEXT
        )""")


# ── helpers ────────────────────────────────────────────────────────────────────

def _gen_short_id() -> str:
    """Generate unique 5-char alphanumeric ID."""
    chars = string.ascii_uppercase + string.digits
    while True:
        sid = "".join(random.choices(chars, k=5))
        with get_conn() as c:
            row = c.execute("SELECT 1 FROM users WHERE short_id=?", (sid,)).fetchone()
        if not row:
            return sid


# ── user operations ────────────────────────────────────────────────────────────

def get_user(tg_id: int):
    with get_conn() as c:
        return c.execute("SELECT * FROM users WHERE tg_id=?", (tg_id,)).fetchone()


def create_user(tg_id: int, username: str, full_name: str, source: str, want_to_buy: str):
    sid = _gen_short_id()
    with get_conn() as c:
        c.execute("""
        INSERT OR IGNORE INTO users (tg_id, short_id, username, full_name, source, want_to_buy)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (tg_id, sid, username, full_name, source, want_to_buy))
    return sid


def update_user_status(tg_id: int, status: str):
    with get_conn() as c:
        c.execute("UPDATE users SET status=? WHERE tg_id=?", (status, tg_id))


def increment_reject(tg_id: int) -> int:
    with get_conn() as c:
        c.execute("UPDATE users SET reject_count = reject_count + 1 WHERE tg_id=?", (tg_id,))
        row = c.execute("SELECT reject_count FROM users WHERE tg_id=?", (tg_id,)).fetchone()
        return row["reject_count"] if row else 0


def update_balance(tg_id: int, delta: float):
    with get_conn() as c:
        c.execute("UPDATE users SET balance = balance + ? WHERE tg_id=?", (delta, tg_id))


def get_balance(tg_id: int) -> float:
    with get_conn() as c:
        row = c.execute("SELECT balance FROM users WHERE tg_id=?", (tg_id,)).fetchone()
        return row["balance"] if row else 0.0


def set_surcharge(tg_id: int, amount: float):
    with get_conn() as c:
        c.execute("UPDATE users SET surcharge=? WHERE tg_id=?", (amount, tg_id))


def get_surcharge(tg_id: int) -> float:
    with get_conn() as c:
        row = c.execute("SELECT surcharge FROM users WHERE tg_id=?", (tg_id,)).fetchone()
        return row["surcharge"] if row else 1.5


def get_user_by_short_id(short_id: str):
    with get_conn() as c:
        return c.execute("SELECT * FROM users WHERE short_id=?", (short_id,)).fetchone()


# ── stats ──────────────────────────────────────────────────────────────────────

def stats():
    with get_conn() as c:
        total   = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        blocked = c.execute("SELECT COUNT(*) FROM users WHERE status='blocked'").fetchone()[0]
        orders  = c.execute("SELECT COUNT(*) FROM orders WHERE status='approved'").fetchone()[0]
        return total, blocked, orders


def blocked_users():
    with get_conn() as c:
        return c.execute("SELECT tg_id, short_id, full_name FROM users WHERE status='blocked'").fetchall()


def all_approved_users():
    with get_conn() as c:
        return c.execute("SELECT tg_id FROM users WHERE status='approved'").fetchall()


# ── orders ─────────────────────────────────────────────────────────────────────

def create_order(tg_id: int, description: str, amount: float) -> int:
    with get_conn() as c:
        cur = c.execute("""
        INSERT INTO orders (tg_id, description, amount) VALUES (?, ?, ?)
        """, (tg_id, description, amount))
        order_id = cur.lastrowid
    return order_id


def get_order(order_id: int):
    with get_conn() as c:
        return c.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()


def update_order_status(order_id: int, status: str):
    with get_conn() as c:
        c.execute("UPDATE orders SET status=? WHERE id=?", (status, order_id))
        if status == "approved":
            tg_id = c.execute("SELECT tg_id FROM orders WHERE id=?", (order_id,)).fetchone()["tg_id"]
            c.execute("UPDATE users SET orders_count = orders_count + 1 WHERE tg_id=?", (tg_id,))


# ── promo codes ────────────────────────────────────────────────────────────────

def create_promo(code: str, amount: float, activations: int):
    with get_conn() as c:
        c.execute("""
        INSERT INTO promo_codes (code, amount, activations) VALUES (?, ?, ?)
        """, (code, amount, activations))


def use_promo(tg_id: int, code: str):
    """Returns (success: bool, message: str, amount: float)"""
    with get_conn() as c:
        promo = c.execute("SELECT * FROM promo_codes WHERE code=?", (code.upper(),)).fetchone()
        if not promo:
            return False, "❌ Промокод не найден.", 0
        already = c.execute("SELECT 1 FROM promo_uses WHERE tg_id=? AND code=?", (tg_id, code.upper())).fetchone()
        if already:
            return False, "❌ Вы уже использовали этот промокод.", 0
        if promo["used"] >= promo["activations"]:
            return False, "❌ Промокод исчерпан.", 0
        c.execute("UPDATE promo_codes SET used = used + 1 WHERE code=?", (code.upper(),))
        c.execute("INSERT INTO promo_uses (tg_id, code) VALUES (?, ?)", (tg_id, code.upper()))
        c.execute("UPDATE users SET balance = balance + ? WHERE tg_id=?", (promo["amount"], tg_id))
        return True, f"✅ Промокод активирован! Начислено {promo['amount']} EUR.", promo["amount"]


def list_promos():
    with get_conn() as c:
        return c.execute("SELECT * FROM promo_codes").fetchall()


# ── bot state (for pending actions stored as JSON text) ────────────────────────

def set_state(key: str, value: str):
    with get_conn() as c:
        c.execute("INSERT OR REPLACE INTO bot_state (key, value) VALUES (?, ?)", (key, value))


def get_state(key: str) -> str | None:
    with get_conn() as c:
        row = c.execute("SELECT value FROM bot_state WHERE key=?", (key,)).fetchone()
        return row["value"] if row else None


def del_state(key: str):
    with get_conn() as c:
        c.execute("DELETE FROM bot_state WHERE key=?", (key,))
