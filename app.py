
import os
import sqlite3
import json
import csv
import io
import secrets
import hmac
from datetime import datetime
from functools import wraps
from flask import Flask, request, session, redirect, render_template_string, Response, abort

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)

PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "")
DB = os.environ.get("DATABASE_PATH", "erin_orders_v2.db")
PHONE = "(912) 327-0026"

PAYMENTS = {
    "Cash App": "$ErinASayer",
    "Venmo": "@ErinASayer",
    "Apple Cash": PHONE,
    "Cash": "Pay with cash"
}

MENU = [
    ("Poké Bowls", "Teriyaki Salmon", 16,
     "Cooked teriyaki salmon, white rice, avocado, cucumber, edamame, carrots, crispy onions, soy sauce, eel sauce and spicy mayo."),
    ("Poké Bowls", "Tuna", 17,
     "Tuna, white rice, avocado, cucumber, edamame, carrots, crispy onions, soy sauce, eel sauce and spicy mayo."),
    ("Hibachi Bowls", "Teriyaki Chicken", 15,
     "Teriyaki chicken, fried rice, broccoli, carrots, soy sauce and white sauce."),
    ("Hibachi Bowls", "Shrimp", 16,
     "Shrimp, fried rice, broccoli, carrots, soy sauce and white sauce."),
    ("Hibachi Bowls", "Teriyaki Steak", 17,
     "Teriyaki steak, fried rice, broccoli, carrots, soy sauce and white sauce.")
]

PROTEINS = ["None", "Chicken", "Steak", "Shrimp", "Salmon", "Tuna"]

def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

with db() as conn:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY,
            created TEXT,
            name TEXT,
            phone TEXT,
            items TEXT,
            total INTEGER,
            payment TEXT,
            notes TEXT,
            paid INTEGER DEFAULT 0,
            completed INTEGER DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY,
            created TEXT,
            name TEXT,
            rating TEXT,
            message TEXT
        )
    """)

def csrf():
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(24)
    return session["csrf"]

app.jinja_env.globals["csrf"] = csrf

@app.before_request
def protect():
    if request.method == "POST":
        if not hmac.compare_digest(
            session.get("csrf", ""),
            request.form.get("csrf", "") or "invalid"
        ):
            abort(400)

BASE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Erin’s Poké & Hibachi</title>
<style>
* { box-sizing: border-box; }

body {
    margin: 0;
    background: #faf7ef;
    color: #193e32;
    font-family: Arial, sans-serif;
    line-height: 1.6;
}

header {
    background: #193e32;
    color: #faf7ef;
    text-align: center;
    padding: 55px 20px 35px;
}

.brandline {
    color: #d9c8a1;
    font-size: 10px;
    letter-spacing: 3px;
    text-transform: uppercase;
}

h1, h2, h3 {
    font-family: Georgia, serif;
    font-weight: normal;
    line-height: 1.2;
}

h1 {
    font-size: clamp(42px, 8vw, 68px);
    margin: 20px 0;
}

h2 {
    font-size: 34px;
    text-align: center;
}

.tagline {
    color: #d9c8a1;
    font-family: Georgia, serif;
    font-style: italic;
}

nav {
    display: flex;
    justify-content: center;
    gap: 25px;
    margin-top: 28px;
    flex-wrap: wrap;
}

nav a {
    color: #faf7ef;
    text-decoration: none;
    font-size: 13px;
}

main {
    max-width: 760px;
    margin: auto;
    padding: 25px 20px 50px;
}

.category {
    color: #927b4c;
    font-size: 12px;
    letter-spacing: 3px;
    text-transform: uppercase;
    margin-top: 35px;
    font-weight: bold;
}

.card {
    background: #fffdf8;
    border: 1px solid #e4ded0;
    border-radius: 15px;
    padding: 22px;
    margin-bottom: 16px;
}

.line {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 14px;
}

.line h3 {
    font-size: 24px;
    margin: 0;
}

.price {
    font-weight: bold;
    white-space: nowrap;
}

.description {
    font-size: 14px;
    color: #647064;
}

.fields {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
}

label {
    display: block;
    font-size: 13px;
    font-weight: bold;
    margin: 12px 0;
}

input, select, textarea {
    width: 100%;
    padding: 13px;
    margin-top: 7px;
    border: 1px solid #d5d1c3;
    background: white;
    color: #193e32;
    border-radius: 9px;
    font-size: 16px;
}

button, .button {
    display: inline-block;
    background: #193e32;
    color: white;
    border: none;
    border-radius: 9px;
    padding: 14px 22px;
    font-size: 15px;
    text-decoration: none;
    cursor: pointer;
}

.full { width: 100%; }

.soft { background: #e9ede3; }

.total {
    font-size: 28px;
    font-weight: bold;
}

.center { text-align: center; }

.actions {
    display: flex;
    gap: 9px;
    flex-wrap: wrap;
}

.badge {
    background: #e9ede3;
    border-radius: 20px;
    padding: 6px 12px;
    font-size: 12px;
}

footer {
    text-align: center;
    padding: 30px 15px;
    border-top: 1px solid #dedacf;
    font-size: 12px;
}

footer a { color: #193e32; }

@media(max-width: 420px) {
    .fields { grid-template-columns: 1fr; }
    header { padding-top: 40px; }
}
</style>
</head>
<body>

<header>
    <div class="brandline">
        Fresh • Handcrafted • Made to order
    </div>

    <h1>Erin’s Poké<br>&amp; Hibachi</h1>

    <div class="tagline">
        Fresh ingredients. Bold flavors.
    </div>

    <nav>
        <a href="/">Menu & Order</a>
        <a href="/feedback">Feedback</a>
        <a href="sms:9123270026">Contact</a>
    </nav>
</header>

<main>
CONTENT
</main>

<footer>
    Erin’s Poké & Hibachi
    <br>
    Freshly prepared with care.
    <br><br>
    <a href="/login">Owner Login</a>
</footer>

</body>
</html>
"""

def page(content, **kwargs):
    return render_template_string(
        BASE.replace("CONTENT", content), **kwargs
    )

@app.route("/")
def home():
    return page("""
    <h2>The Menu</h2>

    <p class="center description">
        Choose your favorite bowl and make it your own.
    </p>

    <form method="post" action="/order">
    <input type="hidden" name="csrf" value="{{csrf()}}">

    {% for category, name, price, description in menu %}

    {% if loop.first or category != menu[loop.index0-1][0] %}
        <div class="category">{{category}}</div>
    {% endif %}

    <div class="card bowl">

        <div class="line">
            <h3>{{name}}</h3>
            <span class="price">${{price}}.00</span>
        </div>

        <p class="description">{{description}}</p>

        <div class="fields">
            <label>
                Quantity
                <select class="qty"
                    name="qty{{loop.index0}}"
                    data-price="{{price}}">
                    {% for n in range(11) %}
                        <option>{{n}}</option>
                    {% endfor %}
                </select>
            </label>

            <label>
                Extra protein (+$5 per bowl)
                <select class="extra"
                    name="extra{{loop.index0}}">
                    {% for protein in proteins %}
                        <option>{{protein}}</option>
                    {% endfor %}
                </select>
            </label>
        </div>
    </div>

    {% endfor %}

    <div class="card soft">
        <h3>A little extra</h3>
        <p>Add an extra protein to any bowl for just $5.</p>
        <hr>
        <div class="line">
            <strong>Order Total</strong>
            <span id="total" class="total">$0.00</span>
        </div>
    </div>

    <h2>Your Details</h2>

    <div class="card">
        <label>
            Full Name
            <input name="name" required maxlength="100">
        </label>

        <label>
            Phone Number
            <input name="phone" type="tel" required maxlength="40">
        </label>

        <label>
            Payment Method
            <select name="payment" required>
                {% for payment in payments %}
                    <option>{{payment}}</option>
                {% endfor %}
            </select>
        </label>

        <label>
            Special Requests
            <textarea name="notes" rows="3"
                maxlength="1000"
                placeholder="Anything we should know?"></textarea>
        </label>

        <p class="description">
            For delivery, please text (912) 327-0026.
            Payments are made separately.
        </p>

        <button class="full">Place My Order</button>
    </div>
    </form>

    <script>
    function updateTotal() {
        let total = 0;

        document.querySelectorAll(".bowl").forEach(bowl => {
            let qty = bowl.querySelector(".qty");
            let extra = bowl.querySelector(".extra");

            let price = Number(qty.dataset.price);
            let quantity = Number(qty.value);

            if (extra.value !== "None") {
                price += 5;
            }

            total += price * quantity;
        });

        document.getElementById("total").textContent =
            "$" + total.toFixed(2);
    }

    document.querySelectorAll("select").forEach(select => {
        select.addEventListener("change", updateTotal);
    });

    updateTotal();
    </script>
    """, menu=MENU, proteins=PROTEINS, payments=PAYMENTS)

@app.route("/order", methods=["POST"])
def order():
    items = []
    total = 0

    for i, (_, name, price, _) in enumerate(MENU):
        try:
            qty = int(request.form.get(f"qty{i}", "0"))
        except ValueError:
            abort(400)

        extra = request.form.get(f"extra{i}", "None")

        if not 0 <= qty <= 10 or extra not in PROTEINS:
            abort(400)

        if qty > 0:
            subtotal = qty * (price + (5 if extra != "None" else 0))
            total += subtotal

            items.append({
                "name": name,
                "qty": qty,
                "extra": extra,
                "subtotal": subtotal * 100
            })

    name = request.form.get("name", "").strip()[:100]
    phone = request.form.get("phone", "").strip()[:40]
    payment = request.form.get("payment", "")
    notes = request.form.get("notes", "")[:1000]

    if not items or not name or not phone or payment not in PAYMENTS:
        return page("""
            <h2>Please check your order</h2>
            <p>Select at least one bowl and complete your details.</p>
            <a class="button" href="/">Back to Menu</a>
        """), 400

    with db() as conn:
        cursor = conn.execute("""
            INSERT INTO orders
            (created, name, phone, items, total, payment, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(timespec="minutes"),
            name, phone, json.dumps(items), total * 100,
            payment, notes
        ))

        session["last_order"] = cursor.lastrowid

    return redirect("/confirmation")

@app.route("/confirmation")
def confirmation():
    with db() as conn:
        order = conn.execute(
            "SELECT * FROM orders WHERE id=?",
            (session.get("last_order"),)
        ).fetchone()

    if not order:
        return redirect("/")

    return page("""
        <div class="card center">
            <h2>Thank You!</h2>
            <p>Your order has been received.</p>

            <p>Order #{{order.id}}</p>

            <div class="total">
                ${{"%.2f"|format(order.total / 100)}}
            </div>

            <h3>{{order.payment}}</h3>
            <p>{{handle}}</p>

            <p class="description">
                Payment is not automatically processed.
            </p>

            <p>
                For delivery, please text
                <a href="sms:9123270026">{{phone}}</a>.
            </p>

            <a class="button" href="/">Back to Menu</a>
        </div>
    """, order=order, handle=PAYMENTS[order["payment"]], phone=PHONE)

@app.route("/feedback", methods=["GET", "POST"])
def feedback():
    if request.method == "POST":
        message = request.form.get("message", "").strip()[:2000]
        rating = request.form.get("rating", "")

        if not message or rating not in ["1", "2", "3", "4", "5"]:
            abort(400)

        with db() as conn:
            conn.execute("""
                INSERT INTO feedback
                (created, name, rating, message)
                VALUES (?, ?, ?, ?)
            """, (
                datetime.now().isoformat(timespec="minutes"),
                request.form.get("name", "")[:100],
                rating, message
            ))

        return redirect("/feedback?thanks=1")

    return page("""
        <h2>Feedback</h2>

        {% if thanks %}
            <div class="card center">
                <h3>Thank you!</h3>
                <p>We appreciate your feedback.</p>
                <a class="button" href="/">Back to Menu</a>
            </div>
        {% else %}
            <p class="center description">
                We'd love to hear what you think.
            </p>

            <form method="post" class="card">
                <input type="hidden" name="csrf" value="{{csrf()}}">

                <label>
                    Name (optional)
                    <input name="name" maxlength="100">
                </label>

                <label>
                    Rating
                    <select name="rating">
                        <option value="5">★★★★★ Excellent</option>
                        <option value="4">★★★★ Very Good</option>
                        <option value="3">★★★ Good</option>
                        <option value="2">★★ Fair</option>
                        <option value="1">★ Poor</option>
                    </select>
                </label>

                <label>
                    Your Feedback
                    <textarea name="message" rows="5"
                        maxlength="2000" required></textarea>
                </label>

                <button class="full">Submit Feedback</button>
            </form>
        {% endif %}
    """, thanks=request.args.get("thanks"))

def owner_required(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        if not session.get("owner"):
            return redirect("/login")
        return func(*args, **kwargs)
    return wrapped

@app.route("/login", methods=["GET", "POST"])
def login():
    error = ""

    if request.method == "POST":
        entered = request.form.get("password", "")

        if PASSWORD and hmac.compare_digest(
            entered.encode(), PASSWORD.encode()
        ):
            session.clear()
            session["owner"] = True
            return redirect("/dashboard")

        error = "Incorrect password or password not configured."

    return page("""
        <h2>Owner Login</h2>

        <form method="post" class="card">
            <input type="hidden" name="csrf" value="{{csrf()}}">

            <label>
                Password
                <input type="password" name="password" required>
            </label>

            <p>{{error}}</p>

            <button class="full">Log In</button>
        </form>
    """, error=error)

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect("/")

@app.route("/dashboard")
@owner_required
def dashboard():
    with db() as conn:
        orders = [
            dict(row) for row in conn.execute(
                "SELECT * FROM orders ORDER BY id DESC"
            )
        ]

        reviews = conn.execute(
            "SELECT * FROM feedback ORDER BY id DESC"
        ).fetchall()

    for order in orders:
        order["items"] = json.loads(order["items"])

    revenue = sum(o["total"] for o in orders if o["paid"]) / 100

    return page("""
        <h2>Owner Dashboard</h2>

        <div class="card soft">
            <div class="category">Paid Revenue</div>
            <div class="total">${{"%.2f"|format(revenue)}}</div>
            <p>{{orders|length}} total orders</p>

            <div class="actions">
                <a class="button" href="/dashboard/export">
                    Download CSV
                </a>

                <form action="/logout" method="post">
                    <input type="hidden" name="csrf" value="{{csrf()}}">
                    <button>Log Out</button>
                </form>
            </div>
        </div>

        <h2>Orders</h2>

        {% for order in orders %}
            <div class="card">
                <div class="line">
                    <h3>#{{order.id}} — {{order.name}}</h3>
                    <strong>${{"%.2f"|format(order.total / 100)}}</strong>
                </div>

                <p class="description">{{order.created}}</p>
                <p>Phone: {{order.phone}}</p>
                <p>Payment: {{order.payment}}</p>

                {% for item in order["items"] %}
                    <p>
                        {{item.qty}} × {{item.name}}
                        {% if item.extra != "None" %}
                            <br>Extra {{item.extra}} (+$5 each)
                        {% endif %}
                    </p>
                {% endfor %}

                <p>Notes: {{order.notes}}</p>

                <p>
                    <span class="badge">
                        {{ "Paid" if order.paid else "Unpaid" }}
                    </span>
                    <span class="badge">
                        {{ "Completed" if order.completed else "Pending" }}
                    </span>
                </p>

                <div class="actions">

                    <form method="post"
                        action="/dashboard/{{order.id}}/paid">
                        <input type="hidden" name="csrf" value="{{csrf()}}">
                        <button>
                            {{ "Mark Unpaid" if order.paid else "Mark Paid" }}
                        </button>
                    </form>

                    <form method="post"
                        action="/dashboard/{{order.id}}/completed">
                        <input type="hidden" name="csrf" value="{{csrf()}}">
                        <button>
                            {{ "Reopen" if order.completed else "Complete" }}
                        </button>
                    </form>

                </div>
            </div>
        {% else %}
            <p class="center">No orders yet.</p>
        {% endfor %}

        <h2>Feedback</h2>

        {% for review in reviews %}
            <div class="card">
                <strong>{{review.name or "Anonymous"}}</strong>
                <p>{{review.rating}} / 5 stars</p>
                <p>{{review.message}}</p>
                <p class="description">{{review.created}}</p>
            </div>
        {% else %}
            <p class="center">No feedback yet.</p>
        {% endfor %}
    """, orders=orders, reviews=reviews, revenue=revenue)

@app.route("/dashboard/<int:order_id>/<field>", methods=["POST"])
@owner_required
def update_order(order_id, field):
    if field not in ["paid", "completed"]:
        abort(400)

    with db() as conn:
        conn.execute(
            f"UPDATE orders SET {field}=1-{field} WHERE id=?",
            (order_id,)
        )

    return redirect("/dashboard")

@app.route("/dashboard/export")
@owner_required
def export_orders():
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "ID", "Date", "Name", "Phone", "Items",
        "Total", "Payment", "Notes", "Paid", "Completed"
    ])

    with db() as conn:
        for order in conn.execute(
            "SELECT * FROM orders ORDER BY id DESC"
        ):
            values = list(order)
            values[5] = f"{values[5] / 100:.2f}"
            writer.writerow([
                "'" + v if isinstance(v, str)
                and v.startswith(("=", "+", "-", "@", "\t", "\r"))
                else v for v in values
            ])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=orders.csv"
        }
    )

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )
