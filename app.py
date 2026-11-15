import csv
import io
import os
import sqlite3
import hashlib
from datetime import datetime
from functools import wraps
import hmac

from flask import Flask, render_template_string, request, redirect, url_for, session, jsonify, Response
from werkzeug.middleware.proxy_fix import ProxyFix

BASE = os.path.dirname(os.path.abspath(__file__))

CSS = '@import url(\'https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&display=swap\');\n:root{--ink:#181816;--muted:#77746e;--line:#d8d6d0;--paper:#f7f6f2;--card:#fff;--accent:#d6f35f;--dark:#191919}\n*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font-family:Manrope,system-ui,sans-serif}.topbar{height:72px;border-bottom:1px solid var(--line);display:flex;align-items:center;justify-content:space-between;padding:0 30px;background:rgba(255,255,255,.7);position:sticky;top:0;z-index:4}.brand{font-size:14px;font-weight:800;letter-spacing:.08em;color:inherit;text-decoration:none}.dash-link{font-size:12px;color:var(--muted);text-decoration:none}.page{max-width:1120px;margin:auto;padding:50px 28px 80px}.hero{padding:20px 0 45px;border-bottom:1px solid var(--line)}.eyebrow{font:500 11px/1.2 "DM Mono",monospace;letter-spacing:.12em;color:var(--muted)}h1{font-size:clamp(40px,7vw,72px);line-height:.95;letter-spacing:-.055em;margin:14px 0}h2{letter-spacing:-.03em}p{color:#5e5c57;line-height:1.6}.delivery{font-size:13px;margin-top:26px}.delivery a{color:inherit;font-weight:800}.order-layout{display:grid;grid-template-columns:minmax(0,1.5fr) minmax(300px,.7fr);gap:38px;margin-top:35px}.menu-section{padding:0 0 32px;border-bottom:1px solid var(--line);margin-bottom:32px}.menu-section h2{font-size:15px;margin:0 0 5px}.menu-section p{font-size:13px;margin:0}.included{font-size:13px;background:#eeece5;padding:18px 20px;margin:18px 0;border-radius:2px}.included strong{font-size:10px;letter-spacing:.1em;text-transform:uppercase}.choices{display:grid;gap:10px}.choice{display:block;border:1px solid var(--line);padding:18px 20px;background:var(--card);cursor:pointer}.choice:has(input:checked){outline:2px solid var(--ink);outline-offset:-2px}.choice input{display:none}.choice-copy{display:flex;justify-content:space-between;gap:20px;font-size:15px}.choice-copy span{font-family:"DM Mono",monospace}.card{background:var(--card);border:1px solid var(--line);padding:24px}.summary{position:sticky;top:96px;height:max-content}.summary h2{font-size:28px;line-height:1.02}.summary-items{margin:30px 0}.summary-item{display:flex;justify-content:space-between;padding:14px 0;border-bottom:1px solid var(--line);font-size:13px}.muted{color:#92908a}.total{display:flex;justify-content:space-between;border-top:2px solid var(--ink);padding-top:18px;font-size:18px}.quantity-row{margin-top:24px;display:flex;justify-content:space-between;gap:12px;align-items:center;font-size:12px}.quantity-row input{width:74px;padding:12px;border:1px solid var(--line);font:inherit}.details{margin-bottom:18px}.details h2,.payment h2{font-size:20px;margin-top:0}.details label,.feedback-form label,.login label{display:block;font-size:11px;font-weight:800;letter-spacing:.05em;text-transform:uppercase;margin:18px 0}.details input,.details textarea,.feedback-form input,.feedback-form textarea,.feedback-form select,.login input{display:block;width:100%;margin-top:7px;border:1px solid var(--line);padding:14px;font:inherit;background:#fff;text-transform:none;letter-spacing:0}.payment{margin-bottom:18px}.pay-row{display:flex;justify-content:space-between;padding:11px 0;border-bottom:1px solid #eee;font-size:13px}.pay-row span{font-family:"DM Mono",monospace}.payment p{font-size:11px}.submit,.button,button{border:0;background:var(--dark);color:white;padding:15px 19px;font:700 12px Manrope,sans-serif;cursor:pointer;text-decoration:none;display:inline-block}.submit{width:100%}.bottom{text-align:center}.feedback-link{text-align:center;margin-top:45px;font-size:12px}.feedback-link a{color:inherit}.success{margin-top:20px;padding:15px;background:#e9f7bd;font-size:12px}.narrow{max-width:620px;margin:70px auto;padding:0 24px}.login{max-width:480px;margin:auto}.error{background:#ffe4e0;padding:12px;font-size:12px}.dashboard{max-width:1100px;margin:auto;padding:45px 28px 80px}.dash-head{display:flex;justify-content:space-between;gap:20px;align-items:end;border-bottom:1px solid var(--line);padding-bottom:24px;margin-bottom:35px}.dash-head h1{font-size:52px}.dash-actions{display:flex;gap:10px;align-items:center}.ghost{background:transparent;color:var(--ink);border:1px solid var(--line)}.dashboard section{margin:0 0 50px}.order-card,.feedback-card{background:white;border:1px solid var(--line);padding:22px;margin:12px 0}.order-top,.order-body,.order-actions,.compact{display:flex;justify-content:space-between;gap:20px}.order-top span,.compact span,.feedback-card span{display:block;color:var(--muted);font-size:11px;margin-top:5px}.status{font:600 10px "DM Mono",monospace;padding:7px 9px;height:max-content}.paid{background:#e9f7bd}.unpaid{background:#ffe7a8}.order-body{padding:20px 0}.order-body ul{margin:0;padding-left:18px;font-size:13px}.contact{font-size:12px;min-width:180px}.order-actions{justify-content:flex-end}.order-actions button{background:#fff;color:var(--ink);border:1px solid var(--line)}.feedback-card{font-size:13px}.feedback-card p{margin:8px 0}.feedback-form .submit{margin-top:10px}@media(max-width:820px){.order-layout{grid-template-columns:1fr}.summary{position:static}.dash-head,.order-body,.order-top{display:block}.dash-actions{margin-top:18px}.order-actions{margin-top:15px}.order-actions form{display:inline-block;margin-right:7px}.topbar{padding:0 18px}.page,.dashboard{padding-left:18px;padding-right:18px}}\n'
BASE_HTML = '<!doctype html>\n<html lang="en">\n<head>\n  <meta charset="utf-8">\n  <meta name="viewport" content="width=device-width,initial-scale=1">\n  <title>{{ page_title }}</title>\n  <link rel="stylesheet" href="{{ url_for(\'static\', filename=\'styles.css\') }}">\n</head>\n<body>\n  <header class="topbar">\n    <a class="brand" href="{{ url_for(\'home\') }}">ERIN’S POKE BOWLS</a>\n    <a class="dash-link" href="{{ url_for(\'dashboard_login\') }}">Order dashboard</a>\n  </header>\n  {{ body|safe }}\n</body>\n</html>\n'
PAGES = {'index.html': '\n<main class="page">\n  <section class="hero">\n    <div>\n      <div class="eyebrow">POKÉ BOWL PLATES</div>\n      <h1>Order your bowl.</h1>\n      <p>Choose your protein. Every bowl comes with all the fixings.</p>\n      <p class="delivery">Need delivery? <a href="tel:9123270026">Text Erin: 912-327-0026</a></p>\n    </div>\n  </section>\n\n  <form id="orderForm" class="order-layout">\n    <div class="menu-column">\n      {% for key, group in menu.items() %}\n      <section class="menu-section">\n        <div class="section-heading">\n          <div>\n            <h2>{{ group.title }}</h2>\n            <p>{{ group.subtitle }}</p>\n          </div>\n        </div>\n        <div class="included"><strong>Included in every bowl</strong><br>{{ group.included }}</div>\n        <div class="choices">\n          {% for item in group.items %}\n          <label class="choice">\n            <input type="radio" name="{{ key }}" value="{{ item.id }}" data-price="{{ item.price }}" data-name="{{ item.name }}">\n            <span class="choice-copy"><b>{{ item.name }}</b><span>${{ item.price }}</span></span>\n          </label>\n          {% endfor %}\n        </div>\n      </section>\n      {% endfor %}\n\n      <section class="details card">\n        <h2>Your details</h2>\n        <label>Name<input required id="name" placeholder="First and last name"></label>\n        <label>Phone number<input required id="phone" type="tel" placeholder="(555) 555-5555"></label>\n        <label>Order notes (optional)<textarea id="notes" rows="4"></textarea></label>\n      </section>\n\n      <section class="payment card">\n        <h2>Payment options</h2>\n        <div class="pay-row"><b>Cash App</b><span>$ErinASayer</span></div>\n        <div class="pay-row"><b>Venmo</b><span>@ErinASayer</span></div>\n        <div class="pay-row"><b>Apple Cash</b><span>(912) 327-0026</span></div>\n        <div class="pay-row"><b>Cash</b><span>Accepted</span></div>\n        <p>Payment is arranged directly with Erin; this form does not collect it.</p>\n      </section>\n\n      <button class="submit" type="submit">Place order</button>\n      <p class="delivery bottom">Text Erin for delivery: <a href="tel:9123270026">912-327-0026</a></p>\n    </div>\n\n    <aside class="summary card">\n      <div class="eyebrow">YOUR ORDER</div>\n      <h2>A little of everything<br>you love.</h2>\n      <div id="summaryItems" class="summary-items"><p class="muted">Choose a bowl to begin.</p></div>\n      <div class="total"><span>Total</span><strong id="total">$0.00</strong></div>\n      <div class="quantity-row">\n        <span>Quantity for selected bowl</span>\n        <input id="quantity" type="number" min="1" value="1">\n      </div>\n      <div id="success" class="success" hidden></div>\n    </aside>\n  </form>\n\n  <div class="feedback-link"><a href="{{ url_for(\'feedback\') }}">Poké Bowl Test feedback</a></div>\n</main>\n\n<script>\nconst state = { items: [] };\nconst radios = document.querySelectorAll(\'input[type=radio][data-price]\');\nconst qty = document.getElementById(\'quantity\');\nconst summary = document.getElementById(\'summaryItems\');\nconst totalEl = document.getElementById(\'total\');\n\nfunction selectedItems() {\n  const out = [];\n  document.querySelectorAll(\'input[type=radio]:checked\').forEach(r => {\n    out.push({id:r.value, name:r.dataset.name, price:Number(r.dataset.price), quantity:1});\n  });\n  return out;\n}\nfunction render() {\n  const items = selectedItems();\n  const q = Math.max(1, Number(qty.value || 1));\n  let total = 0;\n  summary.innerHTML = \'\';\n  if (!items.length) {\n    summary.innerHTML = \'<p class="muted">Choose a bowl to begin.</p>\';\n  } else {\n    items.forEach(x => {\n      x.quantity = q;\n      total += x.price * q;\n      const div = document.createElement(\'div\');\n      div.className = \'summary-item\';\n      div.innerHTML = `<span>${q} × ${x.name}</span><b>$${(x.price*q).toFixed(2)}</b>`;\n      summary.appendChild(div);\n    });\n  }\n  totalEl.textContent = `$${total.toFixed(2)}`;\n}\nradios.forEach(r => r.addEventListener(\'change\', render));\nqty.addEventListener(\'input\', render);\ndocument.getElementById(\'orderForm\').addEventListener(\'submit\', async (e) => {\n  e.preventDefault();\n  const items = selectedItems().map(x => ({...x, quantity: Math.max(1, Number(qty.value || 1))}));\n  if (!items.length) return alert(\'Choose a bowl first.\');\n  const body = {name:document.getElementById(\'name\').value, phone:document.getElementById(\'phone\').value, notes:document.getElementById(\'notes\').value, items};\n  const res = await fetch(\'/order\', {method:\'POST\', headers:{\'Content-Type\':\'application/json\'}, body:JSON.stringify(body)});\n  const data = await res.json();\n  if (!data.ok) return alert(data.error || \'Could not save the order.\');\n  const success = document.getElementById(\'success\');\n  success.hidden = false;\n  success.textContent = `Order #${data.order_id} saved. Total: $${Number(data.total).toFixed(2)}. Text Erin at 912-327-0026 for delivery.`;\n  window.scrollTo({top:0, behavior:\'smooth\'});\n});\nrender();\n</script>\n\n', 'login.html': '\n<main class="narrow">\n  <section class="card login">\n    <div class="eyebrow">ORDER DASHBOARD</div>\n    <h1>Sign in.</h1>\n    {% if error %}<div class="error">{{ error }}</div>{% endif %}\n    <form method="post">\n      <label>Password<input type="password" name="password" required autofocus></label>\n      <button class="submit" type="submit">Open dashboard</button>\n    </form>\n  </section>\n</main>\n\n', 'dashboard.html': '\n<main class="dashboard">\n  <div class="dash-head">\n    <div><div class="eyebrow">ERIN’S POKE BOWLS</div><h1>Order dashboard</h1></div>\n    <div class="dash-actions"><a class="button" href="{{ url_for(\'orders_csv\') }}">Download CSV</a><form method="post" action="{{ url_for(\'dashboard_logout\') }}"><button class="ghost">Log out</button></form></div>\n  </div>\n\n  <section>\n    <h2>Active orders</h2>\n    {% if not active %}<p class="muted">No active orders.</p>{% endif %}\n    {% for o in active %}\n    <article class="order-card">\n      <div class="order-top"><div><b>#{{ o.id }} · {{ o.customer_name }}</b><span>{{ o.created_at }}</span></div><div class="status {{ \'paid\' if o.paid else \'unpaid\' }}">{{ \'PAID\' if o.paid else \'UNPAID\' }}</div></div>\n      <div class="order-body">\n        <div><ul>{% for i in o.items %}<li>{{ i.quantity }} × {{ i.name }} — ${{ \'%.2f\'|format(i.line_total) }}</li>{% endfor %}</ul><p><b>Total:</b> ${{ \'%.2f\'|format(o.total) }}</p></div>\n        <div class="contact"><b>{{ o.phone }}</b>{% if o.notes %}<p><b>Notes:</b> {{ o.notes }}</p>{% endif %}</div>\n      </div>\n      <div class="order-actions">\n        <form method="post" action="{{ url_for(\'toggle_paid\', order_id=o.id) }}"><button>{{ \'Mark unpaid\' if o.paid else \'Mark paid\' }}</button></form>\n        <form method="post" action="{{ url_for(\'complete_order\', order_id=o.id) }}"><button>Move to completed</button></form>\n      </div>\n    </article>\n    {% endfor %}\n  </section>\n\n  <section>\n    <h2>Past orders</h2>\n    {% if not past %}<p class="muted">No completed orders yet.</p>{% endif %}\n    {% for o in past %}\n    <article class="order-card compact"><div><b>#{{ o.id }} · {{ o.customer_name }}</b><span>{{ o.created_at }}</span></div><div><span class="status {{ \'paid\' if o.paid else \'unpaid\' }}">{{ \'PAID\' if o.paid else \'UNPAID\' }}</span> · ${{ \'%.2f\'|format(o.total) }}</div></article>\n    {% endfor %}\n  </section>\n\n  <section>\n    <h2>Poké Bowl Test feedback</h2>\n    {% if not feedback %}<p class="muted">No feedback yet.</p>{% endif %}\n    {% for f in feedback %}\n    <article class="feedback-card"><b>{{ f.name or \'Anonymous\' }}</b><span>{{ f.created_at }}</span><p>Rating: {{ f.rating or \'—\' }}</p><p>Favorite: {{ f.favorite or \'—\' }}</p><p>{{ f.comments or \'—\' }}</p></article>\n    {% endfor %}\n  </section>\n</main>\n\n', 'feedback.html': '\n<main class="narrow">\n  <section class="card">\n    <div class="eyebrow">POKÉ BOWL TEST</div>\n    <h1>Tell us what you think.</h1>\n    <form method="post" class="feedback-form">\n      <label>Name (optional)<input name="name"></label>\n      <label>How would you rate it?\n        <select name="rating"><option value="">Choose one</option><option>5 — Excellent</option><option>4 — Good</option><option>3 — Okay</option><option>2 — Needs work</option><option>1 — Not for me</option></select>\n      </label>\n      <label>What was your favorite? <input name="favorite"></label>\n      <label>Comments<textarea name="comments" rows="5"></textarea></label>\n      <button class="submit" type="submit">Send feedback</button>\n    </form>\n  </section>\n</main>\n\n', 'feedback_thanks.html': '\n<main class="narrow"><section class="card"><div class="eyebrow">THANK YOU</div><h1>Feedback received.</h1><p>Your response has been saved to the dashboard.</p><a class="button" href="{{ url_for(\'home\') }}">Back to ordering</a></section></main>\n\n'}
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
    return hmac.compare_digest(actual, expected)


def login_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not session.get("dashboard"):
            return redirect(url_for("dashboard_login"))
        return fn(*args, **kwargs)
    return wrapped


@app.route("/")
def home():
    return render_template_string(BASE_HTML, page_title="Erin’s Poke Bowls | Order Online", body=render_template_string(PAGES["index.html"], menu=MENU, css=CSS))


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
        return render_template_string(BASE_HTML, page_title="Feedback received", body=render_template_string(PAGES["feedback_thanks.html"]), css=CSS)
    return render_template_string(BASE_HTML, page_title="Poké Bowl Test Feedback", body=render_template_string(PAGES["feedback.html"]), css=CSS)


@app.route("/dashboard/login", methods=["GET", "POST"])
def dashboard_login():
    error = None
    if request.method == "POST":
        if password_ok(request.form.get("password", "")):
            session["dashboard"] = True
            return redirect(url_for("dashboard"))
        error = "Incorrect password."
    return render_template_string(BASE_HTML, page_title="Dashboard Login", body=render_template_string(PAGES["login.html"], error=error), css=CSS)


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
    return render_template_string(BASE_HTML, page_title="Order Dashboard", body=render_template_string(PAGES["dashboard.html"], active=hydrate(active), past=hydrate(past), feedback=feedback_rows), css=CSS)


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
