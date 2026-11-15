import csv
import io
import os
import sqlite3
import hashlib
from datetime import datetime
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, Response
from werkzeug.middleware.proxy_fix import ProxyFix

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("DATABASE_PATH", os.path.join(BASE, "orders.db"))

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-me")
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

MENU = {
    "poke": {
        "title": "POKÉ BOWL PLATES",
        "subtitle": "Choose your protein. Every bowl comes with all the fixings.",
        "included": "White rice, avocado, cucumber, edamame, carrots, crispy onions, soy sauce, eel sauce, and spicy mayo.",
        "items": [
            {"id": "poke-salmon", "name": "Teriyaki salmon (cooked)", "price": 16},
            {"id": "poke-tuna", "name": "Tuna", "price": 17},
        ],
    },
    "hibachi": {
        "title": "HIBACHI BOWLS",
        "subtitle": "Choose your protein. Every bowl comes with all the fixings.",
        "included": "Fried rice, broccoli, carrots, soy sauce, and white sauce.",
        "items": [
            {"id": "hibachi-chicken", "name": "Teriyaki chicken", "price": 15},
            {"id": "hibachi-shrimp", "name": "Shrimp", "price": 16},
            {"id": "hibachi-steak", "name": "Teriyaki steak", "price": 17},
        ],
    },
}

ALL_ITEMS = {i["id"]: i for group in MENU.values() for i in group["items"]}


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with db() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            customer_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            notes TEXT DEFAULT '',
            items_json TEXT NOT NULL,
            total REAL NOT NULL,
            paid INTEGER NOT NULL DEFAULT 0,
            completed INTEGER NOT NULL DEFAULT 0
        )""")
        conn.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            name TEXT DEFAULT '',
            rating TEXT DEFAULT '',
            favorite TEXT DEFAULT '',
            comments TEXT DEFAULT ''
        )""")


def password_ok(password):
    salt = os.environ.get("DASHBOARD_PASSWORD_SALT", "")
    expected = os.environ.get("DASHBOARD_PASSWORD_HASH", "")
    if not salt or not expected:
        return False
    actual = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), bytes.fromhex(salt), 310_000
    ).hex()
    return hashlib.compare_digest(actual, expected)


def login_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not session.get("dashboard"):
            return redirect(url_for("dashboard_login"))
        return fn(*args, **kwargs)
    return wrapped


@app.route("/")
def home():
    return render_template("index.html", menu=MENU)


@app.post("/order")
def create_order():
    data = request.get_json(silent=True) or request.form
    name = str(data.get("name", "")).strip()
    phone = str(data.get("phone", "")).strip()
    notes = str(data.get("notes", "")).strip()
    if not name or not phone:
        return jsonify({"ok": False, "error": "Name and phone number are required."}), 400

    raw_items = data.get("items", [])
    if isinstance(raw_items, str):
        import json
        raw_items = json.loads(raw_items)

    items = []
    total = 0
    for row in raw_items:
        item_id = str(row.get("id", ""))
        qty = max(0, int(row.get("quantity", 0)))
        if item_id not in ALL_ITEMS or qty == 0:
            continue
        item = ALL_ITEMS[item_id]
        line_total = item["price"] * qty
        items.append({"id": item_id, "name": item["name"], "price": item["price"], "quantity": qty, "line_total": line_total})
        total += line_total

    if not items:
        return jsonify({"ok": False, "error": "Choose at least one bowl."}), 400

    import json
    with db() as conn:
        cur = conn.execute(
            "INSERT INTO orders (created_at, customer_name, phone, notes, items_json, total) VALUES (?, ?, ?, ?, ?, ?)",
            (datetime.now().isoformat(timespec="seconds"), name, phone, notes, json.dumps(items), total),
        )
        order_id = cur.lastrowid

    return jsonify({"ok": True, "order_id": order_id, "total": total})


@app.route("/feedback", methods=["GET", "POST"])
def feedback():
    if request.method == "POST":
        with db() as conn:
            conn.execute(
                "INSERT INTO feedback (created_at, name, rating, favorite, comments) VALUES (?, ?, ?, ?, ?)",
                (
                    datetime.now().isoformat(timespec="seconds"),
                    request.form.get("name", "").strip(),
                    request.form.get("rating", "").strip(),
                    request.form.get("favorite", "").strip(),
                    request.form.get("comments", "").strip(),
                ),
            )
        return render_template("feedback_thanks.html")
    return render_template("feedback.html")


@app.route("/dashboard/login", methods=["GET", "POST"])
def dashboard_login():
    error = None
    if request.method == "POST":
        if password_ok(request.form.get("password", "")):
            session["dashboard"] = True
            return redirect(url_for("dashboard"))
        error = "Incorrect password."
    return render_template("login.html", error=error)


@app.post("/dashboard/logout")
def dashboard_logout():
    session.clear()
    return redirect(url_for("dashboard_login"))


@app.route("/dashboard")
@login_required
def dashboard():
    with db() as conn:
        active = conn.execute("SELECT * FROM orders WHERE completed = 0 ORDER BY id DESC").fetchall()
        past = conn.execute("SELECT * FROM orders WHERE completed = 1 ORDER BY id DESC").fetchall()
        feedback_rows = conn.execute("SELECT * FROM feedback ORDER BY id DESC").fetchall()
    import json
    def hydrate(rows):
        result = []
        for r in rows:
            d = dict(r)
            d["items"] = json.loads(d["items_json"])
            result.append(d)
        return result
    return render_template("dashboard.html", active=hydrate(active), past=hydrate(past), feedback=feedback_rows)


@app.post("/dashboard/order/<int:order_id>/paid")
@login_required
def toggle_paid(order_id):
    with db() as conn:
        row = conn.execute("SELECT paid FROM orders WHERE id = ?", (order_id,)).fetchone()
        if row:
            conn.execute("UPDATE orders SET paid = ? WHERE id = ?", (0 if row["paid"] else 1, order_id))
    return redirect(url_for("dashboard"))


@app.post("/dashboard/order/<int:order_id>/complete")
@login_required
def complete_order(order_id):
    with db() as conn:
        conn.execute("UPDATE orders SET completed = 1 WHERE id = ?", (order_id,))
    return redirect(url_for("dashboard"))


@app.get("/dashboard/orders.csv")
@login_required
def orders_csv():
    with db() as conn:
        rows = conn.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
    import json
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["Order ID", "Created", "Customer", "Phone", "Items", "Total", "Paid", "Completed", "Notes"])
    for r in rows:
        items = json.loads(r["items_json"])
        item_text = "; ".join(f'{x["quantity"]} × {x["name"]}' for x in items)
        writer.writerow([r["id"], r["created_at"], r["customer_name"], r["phone"], item_text, f'{r["total"]:.2f}', "Paid" if r["paid"] else "Unpaid", "Completed" if r["completed"] else "Active", r["notes"]])
    return Response(out.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=erins-orders.csv"})


@app.get("/health")
def health():
    return {"ok": True}


init_db()

if __name__ == "__main__":
    app.run(debug=True)
