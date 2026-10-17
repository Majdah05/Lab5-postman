"""Lab 5 SQLite user database and CRUD operations."""

import sqlite3
from contextlib import closing
from pathlib import Path

DATABASE = Path(__file__).resolve().with_name("database.db")
FIELDS = ("name", "email", "phone", "address", "country")


def connect_to_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def create_db_table():
    with closing(connect_to_db()) as conn, conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY NOT NULL,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT NOT NULL,
                address TEXT NOT NULL,
                country TEXT NOT NULL
            )
        """)


def insert_user(user):
    with closing(connect_to_db()) as conn, conn:
        cur = conn.execute(
            "INSERT INTO users (name, email, phone, address, country) VALUES (?, ?, ?, ?, ?)",
            tuple(user[field] for field in FIELDS),
        )
        user_id = cur.lastrowid
    return get_user_by_id(user_id)


def get_users():
    with closing(connect_to_db()) as conn:
        return [dict(row) for row in conn.execute("SELECT * FROM users ORDER BY user_id")]


def get_user_by_id(user_id):
    with closing(connect_to_db()) as conn:
        row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
        return dict(row) if row else {}


def update_user(user):
    with closing(connect_to_db()) as conn, conn:
        conn.execute(
            "UPDATE users SET name = ?, email = ?, phone = ?, address = ?, country = ? WHERE user_id = ?",
            tuple(user[field] for field in FIELDS) + (user["user_id"],),
        )
    return get_user_by_id(user["user_id"])


def delete_user(user_id):
    with closing(connect_to_db()) as conn, conn:
        cur = conn.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        if cur.rowcount == 0:
            return {}
    return {"status": "User deleted successfully"}


if __name__ == "__main__":
    create_db_table()
