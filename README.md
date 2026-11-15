# Erin's Poke Bowls — editable order site

This is a complete editable Flask + SQLite order site based on the supplied Erin's Poke Bowls page.

## Included
- Poke bowls and Hibachi bowls
- Quantity selection, no topping options
- Customer name, phone, notes
- Automatic order total
- Cash App, Venmo, Apple Cash, and cash payment instructions
- Delivery instruction to text (912) 327-0026
- Order persistence in SQLite
- Password-protected dashboard
- Mark paid/unpaid
- Move completed deliveries out of active orders
- Past orders
- CSV download
- Separate "Poke Bowl Test" feedback form and dashboard responses

## Dashboard
The initial dashboard password is the password you supplied for this test run. It is stored as a PBKDF2 hash in the app configuration rather than plaintext.

For production, change `DASHBOARD_PASSWORD_HASH` and `DASHBOARD_PASSWORD_SALT` in `.env`.

## Run locally
Python 3.11+ recommended:

```bash
python -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows:
# .venv\Scripts\activate

pip install -r requirements.txt
python app.py
```

Then open http://127.0.0.1:5000

The SQLite database is created automatically as `orders.db`.

## Edit later
The menu is defined in `app.py` under `MENU`. The site styling is in `static/styles.css`, and the customer/dashboard pages are in `templates/`.

The structure deliberately keeps menu data separate from presentation so prices, names, included ingredients, wording, and photos can be changed without rewriting the order logic.

## Deployment
This project can be deployed to a Python host such as Render, Railway, Fly.io, or a VPS. For production, use persistent storage for `orders.db` (or switch the database layer to Postgres) and set a strong dashboard password through environment variables.
