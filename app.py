
import os
import csv
import io
import json
import sqlite3
import secrets
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from functools import wraps
from flask import (
    Flask, request, redirect, url_for, session,
    render_template_string, send_file, abort
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)

DASHBOARD_PASSWORD = os.environ.get("DASHBOARD_PASSWORD")
DB_PATH = os.environ.get("DATABASE_PATH", "orders.db")
PHONE = "(912) 327-0026"

PAYMENTS = {
    "Cash App": "$ErinASayer",
    "Venmo": "@ErinASayer",
    "Apple Cash": PHONE,
    "Cash": "Pay with cash"
}

MENU = {
    "Hibachi Tuesdays": [
        {"name": "Teriyaki Chicken", "price": 15},
        {"name": "Shrimp", "price": 16},
        {"name": "Teriyaki Steak", "price": 17}
    ],
    "Poké Thursdays": [
        {"name": "Teriyaki Salmon (Cooked)", "price": 16},
        {"name": "Tuna", "price": 17}
    ]
}

DESCRIPTIONS = {
    "Hibachi Tuesdays": (
        "Fried rice, broccoli, carrots, soy sauce "
        "and white sauce."
    ),
    "Poké Thursdays": (
        "White rice, avocado, cucumber, edamame, "
        "carrots, crispy onions, soy sauce, "
        "eel sauce and spicy mayo."
    )
}

PROTEINS = {
    "Hibachi Tuesdays": ["Chicken", "Shrimp", "Steak"],
    "Poké Thursdays": ["Salmon", "Tuna"]
}

def next_day(weekday):
    today = datetime.now(ZoneInfo("America/New_York")).date()
    return today + timedelta(days=(weekday - today.weekday()) % 7)

def service_dates():
    return {
        "Hibachi Tuesdays": next_day(1),
        "Poké Thursdays": next_day(3)
    }

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS weekly_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                phone TEXT,
                details TEXT,
                notes TEXT,
                payment TEXT,
                total REAL,
                service_date TEXT,
                menu_day TEXT,
                paid INTEGER DEFAULT 0,
                completed INTEGER DEFAULT 0,
                created TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS weekly_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                message TEXT,
                created TEXT
            )
        """)

init_db()

STYLE = """
<style>
* {box-sizing:border-box}
body {
    margin:0;
    background:#f8f6f0;
    color:#303b32;
    font-family:Arial,sans-serif;
    line-height:1.6;
}
header {
    text-align:center;
    background:#344b39;
    color:#fff;
    padding:45px 18px;
}
h1,h2,h3 {
    font-family:Georgia,serif;
    line-height:1.25;
}
h1 {font-size:36px;margin:8px 0}
h2 {font-size:27px;margin:5px 0 12px}
.eyebrow {
    text-transform:uppercase;
    letter-spacing:3px;
    font-size:11px;
    font-weight:bold;
}
.container {
    max-width:780px;
    margin:auto;
    padding:22px 16px;
}
.intro {
    text-align:center;
    margin:8px 0 25px;
}
.card {
    background:white;
    border:1px solid #e1e3d9;
    border-radius:18px;
    padding:22px;
    margin-bottom:22px;
    box-shadow:0 4px 15px #00000006;
}
.hibachi {background:#f5e9db}
.poke {background:#e6eee0}
.item {
    padding:17px 0;
    border-top:1px solid #00000015;
}
.item-title {
    display:flex;
    justify-content:space-between;
    gap:10px;
    font-weight:bold;
}
label {
    display:block;
    font-size:14px;
    font-weight:bold;
    margin:12px 0 5px;
}
input,select,textarea {
    width:100%;
    padding:12px;
    border:1px solid #d5d8cf;
    background:white;
    border-radius:9px;
    font-size:16px;
    color:#303b32;
}
textarea {min-height:90px}
button,.button {
    display:block;
    width:100%;
    background:#344b39;
    color:white;
    padding:14px;
    border:0;
    border-radius:10px;
    font-size:16px;
    font-weight:bold;
    text-decoration:none;
    text-align:center;
    cursor:pointer;
    margin-top:12px;
}
.total {
    font-size:25px;
    font-weight:bold;
    text-align:center;
    padding:15px;
}
.muted {color:#657064;font-size:14px}
footer {
    text-align:center;
    padding:25px;
    font-size:14px;
}
a {color:#344b39}
.order {
    border-top:1px solid #ddd;
    padding:15px 0;
}
.tag {
    display:inline-block;
    padding:4px 12px;
    background:#e6eee0;
    border-radius:20px;
    font-size:13px;
}
.actions {
    display:flex;
    gap:10px;
    flex-wrap:wrap;
}
.actions form {flex:1}
.small {font-size:13px}
</style>
"""

BASE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport"
      content="width=device-width, initial-scale=1">
<title>Erin’s Poké & Hibachi</title>
{{ style|safe }}
</head>
<body>
<header>
<div class="eyebrow">Fresh • Homemade • Delicious</div>
<h1>Erin’s Poké & Hibachi</h1>
<div>Hibachi Tuesdays • Poké Thursdays</div>
</header>
<main class="container">
""" 

FOOTER = """
</main>
<footer>
<p>Made fresh with love ♡</p>
<a href="/">Order</a> ·
<a href="/feedback">Feedback</a>
</footer>
</body>
</html>
"""

def page(content, **kwargs):
    return render_template_string(
        BASE + content + FOOTER,
        style=STYLE,
        **kwargs
    )

HOME = """
<div class="intro">
<h2>Your weekly bowl fix</h2>
<p>Two days. Two menus. Something delicious
to look forward to.</p>
<p class="muted">
Preorder your bowls below for the designated day.
</p>
</div>

<form method="POST" action="/order" id="orderForm">

{% for category, items in menu.items() %}
{% set category_index = loop.index0 %}

<section class="card {{ 'hibachi' if loop.first else 'poke' }}">
<div class="eyebrow">
{{ 'Every Tuesday' if loop.first else 'Every Thursday' }}
</div>

<h2>
{{ '🥢' if loop.first else '🥑' }}
{{ category }}
</h2>

<p class="tag">
Next service: {{ dates[category].strftime('%B %d') }}
</p>

<p>{{ descriptions[category] }}</p>

{% for item in items %}
{% set key = category_index|string + '_' + loop.index0|string %}

<div class="item">
<div class="item-title">
<span>{{ item.name }}</span>
<span>${{ item.price }}</span>
</div>

<label>Quantity</label>
<select name="qty_{{ key }}"
        class="quantity"
        data-key="{{ key }}"
        data-price="{{ item.price }}"
        onchange="updateTotal()">
{% for n in range(11) %}
<option value="{{ n }}">{{ n }}</option>
{% endfor %}
</select>

<label>Add extra protein — $5 per bowl</label>
<select name="extra_{{ key }}"
        id="extra_{{ key }}"
        onchange="updateTotal()">
<option value="">No extra protein</option>
{% for protein in proteins[category] %}
<option value="{{ protein }}">{{ protein }} +$5</option>
{% endfor %}
</select>
</div>
{% endfor %}
</section>
{% endfor %}

<section class="card">
<h2>Your information</h2>
<label>Name</label>
<input name="name" required autocomplete="name">

<label>Phone number</label>
<input name="phone" type="tel" required autocomplete="tel">

<label>Order notes</label>
<textarea name="notes"
placeholder="Special instructions or requests"></textarea>

<label>Payment method</label>
<select name="payment" required>
<option value="">Select payment method</option>
{% for payment in payments %}
<option>{{ payment }}</option>
{% endfor %}
</select>

<p class="muted">
Need delivery? Please text {{ phone }}.
</p>

<div class="total">
Total: $<span id="total">0.00</span>
</div>

<button type="submit">Place My Order</button>
</section>
</form>

<script>
function updateTotal() {
    let total = 0;

    document.querySelectorAll('.quantity').forEach(function(el) {
        let qty = Number(el.value);
        let price = Number(el.dataset.price);
        let extra = document.getElementById(
            'extra_' + el.dataset.key
        ).value;

        total += qty * (price + (extra ? 5 : 0));
    });

    document.getElementById('total').textContent =
        total.toFixed(2);

    return total;
}

document.getElementById('orderForm')
.addEventListener('submit', function(e) {
    if (updateTotal() <= 0) {
        e.preventDefault();
        alert('Please select at least one bowl.');
    }
});
</script>
"""

@app.route("/")
def home():
    return page(
        HOME,
        menu=MENU,
        descriptions=DESCRIPTIONS,
        proteins=PROTEINS,
        payments=PAYMENTS,
        dates=service_dates(),
        phone=PHONE
    )

@app.route("/order", methods=["POST"])
def order():
    name = request.form.get("name", "").strip()
    phone = request.form.get("phone", "").strip()
    notes = request.form.get("notes", "").strip()
    payment = request.form.get("payment", "")

    if not name or not phone or payment not in PAYMENTS:
        abort(400, "Please complete your information.")

    dates = service_dates()
    groups = []
    grand_total = 0

    for ci, (category, items) in enumerate(MENU.items()):
        details = []
        subtotal = 0

        for ii, item in enumerate(items):
            key = f"{ci}_{ii}"

            try:
                qty = int(request.form.get(f"qty_{key}", 0))
            except ValueError:
                abort(400)

            if qty < 0 or qty > 10:
                abort(400)

            if qty == 0:
                continue

            extra = request.form.get(f"extra_{key}", "")

            if extra and extra not in PROTEINS[category]:
                abort(400)

            price = item["price"] + (5 if extra else 0)
            subtotal += price * qty

            description = f"{qty} × {item['name']}"

            if extra:
                description += f" (+ extra {extra} per bowl)"

            details.append(description)

        if details:
            groups.append({
                "category": category,
                "date": dates[category].isoformat(),
                "details": details,
                "subtotal": subtotal
            })
            grand_total += subtotal

    if not groups:
        abort(400, "Please select at least one bowl.")

    with db() as conn:
        for group in groups:
            conn.execute("""
                INSERT INTO weekly_orders
                (name, phone, details, notes, payment,
                 total, service_date, menu_day, created)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                name, phone,
                json.dumps(group["details"], ensure_ascii=False),
                notes, payment, group["subtotal"],
                group["date"], group["category"],
                datetime.now().isoformat()
            ))

    session["confirmation"] = {
        "name": name,
        "groups": groups,
        "total": grand_total,
        "payment": payment
    }

    return redirect(url_for("confirmation"))

@app.route("/confirmation")
def confirmation():
    info = session.get("confirmation")

    if not info:
        return redirect(url_for("home"))

    return page("""
    <section class="card">
    <div style="text-align:center">
    <h2>Order received! ♡</h2>
    <p>Thank you, {{ info.name }}!</p>
    </div>

    {% for group in info.groups %}
    <div class="order">
    <h3>{{ group.category }}</h3>
    <p>Service date: {{ group.date }}</p>
    {% for item in group.details %}
    <div>{{ item }}</div>
    {% endfor %}
    <p><strong>${{ "%.2f"|format(group.subtotal) }}</strong></p>
    </div>
    {% endfor %}

    <h3>Total: ${{ "%.2f"|format(info.total) }}</h3>
    <p>Payment method: {{ info.payment }}</p>
    <p><strong>{{ payment_details }}</strong></p>
    <p>For delivery, please text {{ phone }}.</p>
    <a class="button" href="/">Back to Menu</a>
    </section>
    """, info=info,
        payment_details=PAYMENTS[info["payment"]],
        phone=PHONE)

def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("login"))
        return func(*args, **kwargs)
    return wrapper

@app.route("/login", methods=["GET", "POST"])
def login():
    error = ""

    if request.method == "POST":
        submitted = request.form.get("password", "")

        if DASHBOARD_PASSWORD and secrets.compare_digest(
            submitted, DASHBOARD_PASSWORD
        ):
            session["admin"] = True
            session["csrf"] = secrets.token_hex(24)
            return redirect(url_for("dashboard"))

        error = "Incorrect password or password not configured."

    return page("""
    <section class="card">
    <h2>Admin Login</h2>
    <p>{{ error }}</p>
    <form method="POST">
    <label>Password</label>
    <input type="password" name="password" required>
    <button>Log In</button>
    </form>
    </section>
    """, error=error)

@app.route("/dashboard")
@login_required
def dashboard():
    selected = request.args.get("day", "All")

    with db() as conn:
        if selected in MENU:
            rows = conn.execute("""
                SELECT * FROM weekly_orders
                WHERE menu_day=?
                ORDER BY service_date, id DESC
            """, (selected,)).fetchall()
        else:
            rows = conn.execute("""
                SELECT * FROM weekly_orders
                ORDER BY service_date, id DESC
            """).fetchall()

        feedback = conn.execute("""
            SELECT * FROM weekly_feedback ORDER BY id DESC
        """).fetchall()

    orders = []

    for row in rows:
        record = dict(row)
        record["items"] = json.loads(record["details"])
        orders.append(record)

    revenue = sum(o["total"] for o in orders)
    paid_total = sum(o["total"] for o in orders if o["paid"])

    return page("""
    <section class="card">
    <h2>Order Dashboard</h2>
    <p>
    <a href="/dashboard">All Orders</a> ·
    <a href="/dashboard?day=Hibachi+Tuesdays">Hibachi</a> ·
    <a href="/dashboard?day=Poké+Thursdays">Poké</a>
    </p>
    <p>Orders: {{ orders|length }}</p>
    <p>Order total: ${{ "%.2f"|format(revenue) }}</p>
    <p>Collected: ${{ "%.2f"|format(paid_total) }}</p>
    <a class="button" href="/export">Download Orders CSV</a>
    </section>

    {% for o in orders %}
    <section class="card">
    <span class="tag">{{ o.menu_day }}</span>
    <h3>{{ o.service_date }}</h3>
    <strong>#{{ o.id }} — {{ o.name }}</strong>
    <p>{{ o.phone }}</p>
    {% for item in o["items"] %}
    <div>{{ item }}</div>
    {% endfor %}
    <p>Notes: {{ o.notes or 'None' }}</p>
    <p>{{ o.payment }} — ${{ "%.2f"|format(o.total) }}</p>

    <div class="actions">
    <form method="POST" action="/toggle/{{ o.id }}/paid">
    <input type="hidden" name="csrf" value="{{ csrf }}">
    <button>{{ '✓ Paid' if o.paid else 'Mark Paid' }}</button>
    </form>

    <form method="POST" action="/toggle/{{ o.id }}/completed">
    <input type="hidden" name="csrf" value="{{ csrf }}">
    <button>
    {{ '✓ Completed' if o.completed else 'Mark Completed' }}
    </button>
    </form>
    </div>
    </section>
    {% else %}
    <p>No orders yet.</p>
    {% endfor %}

    <section class="card">
    <h2>Feedback</h2>
    {% for f in feedback %}
    <div class="order">
    <strong>{{ f.name or 'Anonymous' }}</strong>
    <p>{{ f.message }}</p>
    </div>
    {% else %}
    <p>No feedback yet.</p>
    {% endfor %}
    </section>

    <form method="POST" action="/logout">
    <input type="hidden" name="csrf" value="{{ csrf }}">
    <button>Log Out</button>
    </form>
    """, orders=orders, feedback=feedback,
        revenue=revenue, paid_total=paid_total,
        csrf=session["csrf"])

def check_csrf():
    token = session.get("csrf", "")
    submitted = request.form.get("csrf", "")

    if not token or not secrets.compare_digest(token, submitted):
        abort(403)

@app.route("/toggle/<int:order_id>/<field>", methods=["POST"])
@login_required
def toggle(order_id, field):
    check_csrf()

    if field not in ("paid", "completed"):
        abort(400)

    with db() as conn:
        conn.execute(
            f"UPDATE weekly_orders SET {field}=1-{field} WHERE id=?",
            (order_id,)
        )

    return redirect(url_for("dashboard"))

@app.route("/export")
@login_required
def export():
    with db() as conn:
        cursor = conn.execute("""
            SELECT * FROM weekly_orders
            ORDER BY service_date, id
        """)
        rows = cursor.fetchall()
        headers = [column[0] for column in cursor.description]

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)

    for row in rows:
        values = []

        for value in row:
            if isinstance(value, str) and value.startswith(
                ("=", "+", "-", "@", "\t", "\r")
            ):
                value = "'" + value

            values.append(value)

        writer.writerow(values)

    return send_file(
        io.BytesIO(output.getvalue().encode("utf-8-sig")),
        mimetype="text/csv",
        as_attachment=True,
        download_name="weekly_orders.csv"
    )

@app.route("/feedback", methods=["GET", "POST"])
def feedback():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        message = request.form.get("message", "").strip()

        if not message:
            abort(400, "Please enter feedback.")

        with db() as conn:
            conn.execute("""
                INSERT INTO weekly_feedback
                (name, message, created)
                VALUES (?, ?, ?)
            """, (name, message, datetime.now().isoformat()))

        return redirect(url_for("feedback_thanks"))

    return page("""
    <section class="card">
    <h2>Feedback</h2>
    <p>I'd love to hear what you think!</p>
    <form method="POST">
    <label>Name (optional)</label>
    <input name="name">
    <label>Your feedback</label>
    <textarea name="message" required></textarea>
    <button>Submit Feedback</button>
    </form>
    </section>
    """)

@app.route("/feedback/thanks")
def feedback_thanks():
    return page("""
    <section class="card">
    <h2>Thank you for your feedback! ♡</h2>
    <a class="button" href="/">Back to Menu</a>
    </section>
    """)

@app.route("/logout", methods=["POST"])
@login_required
def logout():
    check_csrf()
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 10000))
    )
