import sqlite3
import os

from flask import g

DATABASE = os.path.join(os.path.dirname(__file__), "havlist.db")

_initialized = False


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    global _initialized
    if _initialized:
        return
    db = get_db()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            email       TEXT UNIQUE NOT NULL,
            password    TEXT NOT NULL,
            name        TEXT,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS items (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL DEFAULT 0,
            name            TEXT,
            description     TEXT,
            category        TEXT,
            brand           TEXT,
            serial_number   TEXT,
            purchase_date   TEXT,
            purchase_location TEXT,
            purchase_price  REAL,
            warranty_info   TEXT,
            warranty_expiry TEXT,
            location        TEXT,
            condition       TEXT,
            notes           TEXT,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS photos (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id     INTEGER NOT NULL,
            filename    TEXT NOT NULL,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (item_id) REFERENCES items(id)
        );
        """
    )
    # Migration: add user_id column if missing (existing DBs)
    cols = [row[1] for row in db.execute("PRAGMA table_info(items)").fetchall()]
    if "user_id" not in cols:
        db.execute("ALTER TABLE items ADD COLUMN user_id INTEGER NOT NULL DEFAULT 0")
    db.commit()
    _initialized = True


def teardown(app):
    app.teardown_appcontext(close_db)
