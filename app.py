import os
import csv
import io
import sqlite3
from datetime import datetime
from functools import wraps

from flask import (
    Flask, request, redirect, url_for, session,
    render_template_string, send_file, jsonify
)

app = Flask(__name__)

# --------------------------------------------------
# SETTINGS
# --------------------------------------------------

app.secret_key = os.environ.get("SECRET_KEY", "erins-poke-bowls-secret-key-2026")

DASHBOARD_PASSWORD = os.environ.get(
    "DASHBOARD_PASSWORD",
    "bige16123"
)

DB_PATH = os.environ.get("DATABASE_PATH", "orders.db")

PHONE = "(912) 327-0026"

PAYMENTS = {
    "Cash App": "$ErinASayer",
    "Venmo": "@ErinASayer",
    "Apple Cash": "(912) 327-0026",
    "Cash": "Cash"
}

MENU = {
    "Poké Bowls": [
        {
            "name": "Teriyaki Salmon",
            "description": "Cooked teriyaki salmon with white rice, avocado, cucumber, edamame, carrots, crispy onions, soy sauce, eel sauce, and spicy mayo.",
            "price": 16.00
        },
        {
            "name": "Tuna",
            "description": "Tuna with white rice, avocado, cucumber, edamame, carrots, crispy onions, soy sauce, eel sauce, and spicy mayo.",
            "price": 17.00
        }
    ],
    "Hibachi Bowls": [
        {
            "name": "Teriyaki Chicken",
            "description": "Teriyaki chicken with fried rice, broccoli, carrots, soy sauce, and white sauce.",
            "price": 15.00
        },
        {
            "name": "Shrimp",
            "description": "Shrimp with fried rice, broccoli, carrots, soy sauce, and white sauce.",
            "price": 16.00
        },
        {
            "name": "Teriyaki Steak",
            "description": "Teriyaki steak with fried rice, broccoli, carrots, soy sauce, and white sauce.",
            "price": 17.00
        }
    ]
}


# --------------------------------------------------
# DATABASE
# --------------------------------------------------

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            item TEXT NOT NULL,
            category TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            price REAL NOT NULL,
            total REAL NOT NULL,
            notes TEXT,
            payment_method TEXT,
            paid INTEGER NOT NULL DEFAULT 0,
            completed INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            rating TEXT,
            favorite TEXT,
            comments TEXT,
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


init_db()


# --------------------------------------------------
# HELPERS
# --------------------------------------------------

def money(value):
    return f"${float(value):.2f}"


def dashboard_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("dashboard_logged_in"):
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped


# --------------------------------------------------
# STYLING / HTML
# --------------------------------------------------

BASE_STYLE = """
<style>
* {
    box-sizing: border-box;
}

body {
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
    background: #fff8f0;
    color: #222;
}

header {
    background: linear-gradient(135deg, #111827, #273449);
    color: white;
    padding: 28px 20px;
    text-align: center;
}

header h1 {
    margin: 0;
    font-size: 30px;
}

header p {
    margin: 8px 0 0;
    opacity: .9;
}

.container {
    max-width: 900px;
    margin: 0 auto;
    padding: 22px 16px 50px;
}

.card {
    background: white;
    border-radius: 18px;
    padding: 20px;
    margin: 18px 0;
    box-shadow: 0 4px 18px rgba(0,0,0,.08);
}

h2 {
    margin-top: 0;
}

.item {
    border: 1px solid #eee;
    border-radius: 14px;
    padding: 16px;
    margin: 12px 0;
}

.item h3 {
    margin: 0 0 5px;
}

.description {
    color: #666;
    line-height: 1.5;
    font-size: 14px;
}

.price {
    font-weight: 800;
    font-size: 18px;
    margin: 10px 0;
}

button, .button {
    border: 0;
    border-radius: 12px;
    padding: 12px 17px;
    background: #111827;
    color: white;
    font-size: 15px;
    font-weight: 700;
    cursor: pointer;
    text-decoration: none;
    display: inline-block;
}

button:hover, .button:hover {
    opacity: .9;
}

input, textarea, select {
    width: 100%;
    padding: 13px;
    border: 1px solid #ddd;
    border-radius: 10px;
    font-size: 16px;
    margin-top: 6px;
}

label {
    display: block;
    font-weight: 700;
    margin-top: 14px;
}

.total {
    font-size: 24px;
    font-weight: 900;
    margin: 20px 0;
}

.notice {
    background: #fff3cd;
    border-radius: 12px;
    padding: 15px;
    margin: 15px 0;
}

.success {
    background: #e7f7ed;
    border-radius: 12px;
    padding: 18px;
}

.error {
    background: #ffe7e7;
    border-radius: 12px;
    padding: 18px;
}

.nav {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    margin-bottom: 18px;
}

.nav a {
    text-decoration: none;
    color: white;
    background: #374151;
    padding: 9px 13px;
    border-radius: 9px;
    font-size: 14px;
}

.order {
    border-left: 5px solid #111827;
    background: white;
    padding: 18px;
    margin: 14px 0;
    border-radius: 12px;
    box-shadow: 0 2px 12px rgba(0,0,0,.07);
}

.order h3 {
    margin-top: 0;
}

.small {
    color: #666;
    font-size: 13px;
}

table {
    width: 100%;
    border-collapse: collapse;
    background: white;
}

th, td {
    padding: 10px;
    border-bottom: 1px solid #eee;
    text-align: left;
    vertical-align: top;
}

@media (max-width: 600px) {
    header h1 {
        font-size: 25px;
    }

    .container {
        padding: 15px 12px 40px;
    }

    .card {
        padding: 16px;
    }
}
</style>
"""


# --------------------------------------------------
# CUSTOMER HOME PAGE
# --------------------------------------------------

@app.route("/")
def home():
    return render_template_string("""
<!doctype html>
<html>
<head>
<title>Erin's Poké & Hibachi Bowls</title>
""" + BASE_STYLE + """
</head>
<body>

<header>
    <h1>Erin's Poké & Hibachi Bowls</h1>
    <p>Fresh bowls made to order</p>
</header>

<div class="container">

<div class="notice">
<strong>Delivery:</strong> Text <strong>{{ phone }}</strong> for delivery.
</div>

<form method="POST" action="/order">

<div class="card">
<h2>Poké Bowls</h2>

{% for item in poke %}
<div class="item">
    <h3>{{ item.name }}</h3>
    <div class="description">{{ item.description }}</div>
    <div class="price">${{ "%.2f"|format(item.price) }}</div>

    <label>Quantity</label>
    <select name="qty_{{ item.name|replace(' ', '_')|replace('-', '_') }}">
        {% for n in range(0, 11) %}
        <option value="{{ n }}">{{ n }}</option>
        {% endfor %}
    </select>
</div>
{% endfor %}

</div>

<div class="card">
<h2>Hibachi Bowls</h2>

{% for item in hibachi %}
<div class="item">
    <h3>{{ item.name }}</h3>
    <div class="description">{{ item.description }}</div>
    <div class="price">${{ "%.2f"|format(item.price) }}</div>

    <label>Quantity</label>
    <select name="qty_{{ item.name|replace(' ', '_')|replace('-', '_') }}">
        {% for n in range(0, 11) %}
        <option value="{{ n }}">{{ n }}</option>
        {% endfor %}
    </select>
</div>
{% endfor %}

</div>

<div class="card">
<h2>Your Information</h2>

<label>Customer Name</label>
<input name="customer_name" required>

<label>Phone Number</label>
<input name="phone" type="tel" required>

<label>Payment Method</label>
<select name="payment_method" required>
    <option value="">Select payment method</option>
    <option>Cash App</option>
    <option>Venmo</option>
    <option>Apple Cash</option>
    <option>Cash</option>
</select>

<label>Notes / Special Instructions</label>
<textarea name="notes" rows="4"></textarea>

<div class="total">
Order Total: $<span id="total">0.00</span>
</div>

<button type="submit">Place Order</button>
</div>

</form>

<div class="card">
<h2>Payment</h2>
<p><strong>Cash App:</strong> $ErinASayer</p>
<p><strong>Venmo:</strong> @ErinASayer</p>
<p><strong>Apple Cash:</strong> (912) 327-0026</p>
<p><strong>Cash:</strong> Accepted</p>
</div>

<div class="card">
<a class="button" href="/feedback">Leave Poké Bowl Feedback</a>
</div>

</div>

<script>
const prices = {
{% for item in poke %}
"{{ item.name|replace(' ', '_')|replace('-', '_') }}": {{ item.price }},
{% endfor %}
{% for item in hibachi %}
"{{ item.name|replace(' ', '_')|replace('-', '_') }}": {{ item.price }}
{% if not loop.last %},{% endif %}
{% endfor %}
};

function updateTotal() {
    let total = 0;

    for (const [name, price] of Object.entries(prices)) {
        const select = document.querySelector('[name="qty_' + name + '"]');
        if (select) {
            total += Number(select.value) * price;
        }
    }

    document.getElementById("total").textContent = total.toFixed(2);
}

document.querySelectorAll("select").forEach(function(el) {
    el.addEventListener("change", updateTotal);
});

updateTotal();
</script>

</body>
</html>
""", poke=MENU["Poké Bowls"], hibachi=MENU["Hibachi Bowls"], phone=PHONE)


# --------------------------------------------------
# PLACE ORDER
# --------------------------------------------------

@app.route("/order", methods=["POST"])
def place_order():

    customer_name = request.form.get("customer_name", "").strip()
    phone = request.form.get("phone", "").strip()
    notes = request.form.get("notes", "").strip()
    payment_method = request.form.get("payment_method", "").strip()

    if not customer_name or not phone or not payment_method:
        return """
        <h2>Missing information</h2>
        <p>Please go back and enter your name, phone number, and payment method.</p>
        <a href="/">Go Back</a>
        """

    items = []

    all_items = []

    for category, menu_items in MENU.items():
        for item in menu_items:
            all_items.append((category, item))

    for category, item in all_items:
        field = "qty_" + item["name"].replace(" ", "_").replace("-", "_")

        try:
            quantity = int(request.form.get(field, 0))
        except:
            quantity = 0

        if quantity > 0:
            items.append({
                "category": category,
                "name": item["name"],
                "quantity": quantity,
                "price": item["price"],
                "total": item["price"] * quantity
            })

    if not items:
        return """
        <h2>No items selected</h2>
        <p>Please select at least one bowl.</p>
        <a href="/">Go Back</a>
        """

    grand_total = sum(item["total"] for item in items)

    conn = get_db()

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for item in items:
        conn.execute("""
            INSERT INTO orders
            (customer_name, phone, item, category, quantity, price,
             total, notes, payment_method, paid, completed, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, ?)
        """, (
            customer_name,
            phone,
            item["name"],
            item["category"],
            item["quantity"],
            item["price"],
            item["total"],
            notes,
            payment_method,
            now
        ))

    conn.commit()
    conn.close()

    item_lines = ""

    for item in items:
        item_lines += f"""
        <li>
        {item["quantity"]} × {item["name"]}
        — ${item["total"]:.2f}
        </li>
        """

    return render_template_string("""
<!doctype html>
<html>
<head>
<title>Order Received</title>
""" + BASE_STYLE + """
</head>

<body>

<header>
<h1>Order Received!</h1>
</header>

<div class="container">

<div class="card">

<div class="success">

<h2>Thank you, {{ name }}!</h2>

<p>Your order has been received.</p>

</div>

<h3>Your Order</h3>

<ul>
{{ items|safe }}
</ul>

<div class="total">
Total: ${{ "%.2f"|format(total) }}
</div>

<p><strong>Payment:</strong> {{ payment }}</p>

{% if payment == "Cash App" %}
<p>Send payment to <strong>$ErinASayer</strong>.</p>
{% elif payment == "Venmo" %}
<p>Send payment to <strong>@ErinASayer</strong>.</p>
{% elif payment == "Apple Cash" %}
<p>Send payment to <strong>(912) 327-0026</strong>.</p>
{% else %}
<p>Please have cash ready.</p>
{% endif %}

<p>
For delivery, text <strong>(912) 327-0026</strong>.
</p>

<a class="button" href="/">Place Another Order</a>

</div>

</div>

</body>
</html>
""", name=customer_name, items=item_lines,
       total=grand_total, payment=payment_method)


# --------------------------------------------------
# LOGIN
# --------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():

    error = ""

    if request.method == "POST":

        password = request.form.get("password", "")

        if password == DASHBOARD_PASSWORD:
            session["dashboard_logged_in"] = True
            return redirect(url_for("dashboard"))

        error = "Incorrect password."

    return render_template_string("""
<!doctype html>
<html>
<head>
<title>Dashboard Login</title>
""" + BASE_STYLE + """
</head>

<body>

<header>
<h1>Erin's Dashboard</h1>
</header>

<div class="container">

<div class="card">

<h2>Dashboard Login</h2>

{% if error %}
<div class="error">{{ error }}</div>
{% endif %}

<form method="POST">

<label>Password</label>
<input type="password" name="password" required>

<br><br>

<button type="submit">Log In</button>

</form>

</div>

</div>

</body>
</html>
""", error=error)


# --------------------------------------------------
# LOGOUT
# --------------------------------------------------

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# --------------------------------------------------
# DASHBOARD
# --------------------------------------------------

@app.route("/dashboard")
@dashboard_required
def dashboard():

    conn = get_db()

    active = conn.execute("""
        SELECT *
        FROM orders
        WHERE completed = 0
        ORDER BY id DESC
    """).fetchall()

    completed = conn.execute("""
        SELECT *
        FROM orders
        WHERE completed = 1
        ORDER BY id DESC
    """).fetchall()

    feedback = conn.execute("""
        SELECT *
        FROM feedback
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    return render_template_string("""
<!doctype html>
<html>
<head>
<title>Erin's Dashboard</title>
""" + BASE_STYLE + """
</head>

<body>

<header>
<h1>Erin's Order Dashboard</h1>

<div class="nav">
<a href="/">Customer Site</a>
<a href="/feedback">Feedback Form</a>
<a href="/export">Download Orders CSV</a>
<a href="/logout">Log Out</a>
</div>

</header>

<div class="container">

<div class="card">
<h2>Active Orders</h2>

{% if active %}

{% for order in active %}

<div class="order">

<h3>
Order #{{ order.id }} — {{ order.customer_name }}
</h3>

<p class="small">
{{ order.created_at }}
</p>

<p>
<strong>Phone:</strong>
<a href="tel:{{ order.phone }}">{{ order.phone }}</a>
</p>

<p>
<strong>Item:</strong>
{{ order.quantity }} × {{ order.item }}
</p>

<p>
<strong>Category:</strong>
{{ order.category }}
</p>

<p>
<strong>Total:</strong>
${{ "%.2f"|format(order.total) }}
</p>

<p>
<strong>Payment:</strong>
{{ order.payment_method }}
</p>

<p>
<strong>Paid:</strong>
{% if order.paid %}
Yes
{% else %}
No
{% endif %}
</p>

{% if order.notes %}
<p>
<strong>Notes:</strong>
{{ order.notes }}
</p>
{% endif %}

<form method="POST" action="/toggle-paid/{{ order.id }}" style="display:inline">
<button type="submit">
{% if order.paid %}
Mark Unpaid
{% else %}
Mark Paid
{% endif %}
</button>
</form>

<form method="POST" action="/complete/{{ order.id }}" style="display:inline">
<button type="submit">Mark Completed</button>
</form>

</div>

{% endfor %}

{% else %}

<p>No active orders right now.</p>

{% endif %}

</div>

<div class="card">

<h2>Completed Orders</h2>

{% if completed %}

{% for order in completed %}

<div class="order">

<strong>
Order #{{ order.id }} — {{ order.customer_name }}
</strong>

<p>
{{ order.quantity }} × {{ order.item }}
</p>

<p>
Total: ${{ "%.2f"|format(order.total) }}
</p>

<p class="small">
Completed: {{ order.created_at }}
</p>

</div>

{% endfor %}

{% else %}

<p>No completed orders yet.</p>

{% endif %}

</div>

<div class="card">

<h2>Poké Bowl Feedback</h2>

{% if feedback %}

{% for f in feedback %}

<div class="order">

<strong>{{ f.name or "Anonymous" }}</strong>

<p>
<strong>Rating:</strong>
{{ f.rating }}
</p>

<p>
<strong>Favorite:</strong>
{{ f.favorite }}
</p>

{% if f.comments %}
<p>
<strong>Comments:</strong>
{{ f.comments }}
</p>
{% endif %}

<p class="small">
{{ f.created_at }}
</p>

</div>

{% endfor %}

{% else %}

<p>No feedback yet.</p>

{% endif %}

</div>

</div>

</body>
</html>
""", active=active, completed=completed, feedback=feedback)


# --------------------------------------------------
# MARK PAID / UNPAID
# --------------------------------------------------

@app.route("/toggle-paid/<int:order_id>", methods=["POST"])
@dashboard_required
def toggle_paid(order_id):

    conn = get_db()

    order = conn.execute(
        "SELECT paid FROM orders WHERE id = ?",
        (order_id,)
    ).fetchone()

    if order:
        new_value = 0 if order["paid"] else 1

        conn.execute(
            "UPDATE orders SET paid = ? WHERE id = ?",
            (new_value, order_id)
        )

        conn.commit()

    conn.close()

    return redirect(url_for("dashboard"))


# --------------------------------------------------
# COMPLETE ORDER
# --------------------------------------------------

@app.route("/complete/<int:order_id>", methods=["POST"])
@dashboard_required
def complete_order(order_id):

    conn = get_db()

    conn.execute(
        "UPDATE orders SET completed = 1 WHERE id = ?",
        (order_id,)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("dashboard"))


# --------------------------------------------------
# CSV EXPORT
# --------------------------------------------------

@app.route("/export")
@dashboard_required
def export_orders():

    conn = get_db()

    orders = conn.execute("""
        SELECT *
        FROM orders
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    output = io.StringIO()

    writer = csv.writer(output)

    writer.writerow([
        "Order ID",
        "Customer Name",
        "Phone",
        "Item",
        "Category",
        "Quantity",
        "Price",
        "Total",
        "Notes",
        "Payment Method",
        "Paid",
        "Completed",
        "Created At"
    ])

    for order in orders:
        writer.writerow([
            order["id"],
            order["customer_name"],
            order["phone"],
            order["item"],
            order["category"],
            order["quantity"],
            order["price"],
            order["total"],
            order["notes"],
            order["payment_method"],
            "Yes" if order["paid"] else "No",
            "Yes" if order["completed"] else "No",
            order["created_at"]
        ])

    output.seek(0)

    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype="text/csv",
        as_attachment=True,
        download_name="erins-orders.csv"
    )


# --------------------------------------------------
# FEEDBACK
# --------------------------------------------------

@app.route("/feedback", methods=["GET", "POST"])
def feedback():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        rating = request.form.get("rating", "").strip()
        favorite = request.form.get("favorite", "").strip()
        comments = request.form.get("comments", "").strip()

        conn = get_db()

        conn.execute("""
            INSERT INTO feedback
            (name, rating, favorite, comments, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            name,
            rating,
            favorite,
            comments,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))

        conn.commit()
        conn.close()

        return render_template_string("""
        <!doctype html>
        <html>
        <head>
        <title>Thank You</title>
        """ + BASE_STYLE + """
        </head>

        <body>

        <header>
        <h1>Thank You!</h1>
        </header>

        <div class="container">

        <div class="card success">

        <h2>Thanks for your feedback!</h2>

        <p>Your response has been saved.</p>

        <a class="button" href="/">Back to Menu</a>

        </div>

        </div>

        </body>
        </html>
        """)

    return render_template_string("""
<!doctype html>
<html>
<head>
<title>Poké Bowl Feedback</title>
""" + BASE_STYLE + """
</head>

<body>

<header>
<h1>Poké Bowl Feedback</h1>
<p>Tell us what you think!</p>
</header>

<div class="container">

<div class="card">

<form method="POST">

<label>Your Name (optional)</label>
<input name="name">

<label>How would you rate your bowl?</label>

<select name="rating" required>
<option value="">Choose one</option>
<option>5 - Excellent</option>
<option>4 - Very Good</option>
<option>3 - Good</option>
<option>2 - Needs Improvement</option>
<option>1 - Poor</option>
</select>

<label>What was your favorite?</label>
<input name="favorite">

<label>Comments</label>
<textarea name="comments" rows="5"></textarea>

<br><br>

<button type="submit">Submit Feedback</button>

</form>

</div>

</div>

</body>
</html>
""")


# --------------------------------------------------
# HEALTH CHECK
# --------------------------------------------------

@app.route("/health")
def health():
    return jsonify({"status": "ok"})


# --------------------------------------------------
# RUN LOCALLY
# --------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
