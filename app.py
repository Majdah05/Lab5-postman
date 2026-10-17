"""Lab 5 SQLite user database and CRUD operations."""

import sqlite3
from contextlib import closing
from pathlib import Path

from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

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


app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
create_db_table()


def validate_user(user, updating=False):
    if not isinstance(user, dict):
        return "Request body must be a JSON object"
    for field in FIELDS:
        if not isinstance(user.get(field), str) or not user[field].strip():
            return f"{field} must be a nonempty string"
    if updating and (type(user.get("user_id")) is not int or not 0 < user["user_id"] <= 2**63 - 1):
        return "user_id must be a positive SQLite integer"
    return None


def valid_id(user_id):
    return user_id.isascii() and user_id.isdigit() and len(user_id) <= 19 and 0 < int(user_id) <= 2**63 - 1


@app.errorhandler(HTTPException)
def http_error(error):
    return jsonify(error=error.description), error.code


@app.route('/api/users', methods=['GET'])
def api_get_users():
    return jsonify(get_users())


@app.route('/api/users/<user_id>', methods=['GET'])
def api_get_user(user_id):
    if not valid_id(user_id):
        return jsonify(error="Invalid user_id"), 400
    user = get_user_by_id(int(user_id))
    return jsonify(user) if user else (jsonify(error="User not found"), 404)


@app.route('/api/users/add', methods=['POST'])
def api_add_user():
    user = request.get_json()
    error = validate_user(user)
    if error:
        return jsonify(error=error), 400
    return jsonify(insert_user(user))


@app.route('/api/users/update', methods=['PUT'])
def api_update_user():
    user = request.get_json()
    error = validate_user(user, updating=True)
    if error:
        return jsonify(error=error), 400
    updated = update_user(user)
    return jsonify(updated) if updated else (jsonify(error="User not found"), 404)


@app.route('/api/users/delete/<user_id>', methods=['DELETE'])
def api_delete_user(user_id):
    if not valid_id(user_id):
        return jsonify(error="Invalid user_id"), 400
    message = delete_user(int(user_id))
    return jsonify(message) if message else (jsonify(error="User not found"), 404)


if __name__ == "__main__":
    app.run(host="localhost", port=5000)
