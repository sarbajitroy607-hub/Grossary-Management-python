"""
database.py — CSV-based persistent storage for GroceryPro
----------------------------------------------------------
Two CSV files inside the  data/  folder:
  data/products.csv  —  all grocery items (name, price, stock, category)
  data/sales.csv     —  every checkout line-item (session, item, qty, price, total, date)
"""

import csv
import os
from datetime import datetime

# ── File paths ───────────────────────────────────────────────────────
BASE_DIR      = os.path.dirname(__file__)
DATA_DIR      = os.path.join(BASE_DIR, "data")
PRODUCTS_CSV  = os.path.join(DATA_DIR, "products.csv")
SALES_CSV     = os.path.join(DATA_DIR, "sales.csv")

PRODUCTS_FIELDS = ["name", "price", "stock", "category"]
SALES_FIELDS    = ["session_id", "item_name", "qty", "unit_price", "total", "sold_at"]

# Default stock loaded when products.csv doesn't exist yet
DEFAULT_PRODUCTS = [
    {"name": "rice",  "price": 50.0,  "stock": 10, "category": "Staples"},
    {"name": "wheat", "price": 40.0,  "stock": 10, "category": "Staples"},
    {"name": "flour", "price": 30.0,  "stock": 10, "category": "Staples"},
    {"name": "oil",   "price": 100.0, "stock": 10, "category": "Oils"},
    {"name": "daal",  "price": 60.0,  "stock": 10, "category": "Staples"},
    {"name": "soap",  "price": 20.0,  "stock": 10, "category": "Cleaning"},
    {"name": "surf",  "price": 25.0,  "stock": 10, "category": "Cleaning"},
]


# ── Init ─────────────────────────────────────────────────────────────

def init_db():
    """Create the data/ folder and CSV files if they don't exist."""
    os.makedirs(DATA_DIR, exist_ok=True)

    # products.csv — seed defaults only on first run
    if not os.path.exists(PRODUCTS_CSV):
        _write_products(DEFAULT_PRODUCTS)

    # sales.csv — just create a header-only file if missing
    if not os.path.exists(SALES_CSV):
        with open(SALES_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=SALES_FIELDS)
            writer.writeheader()


# ── Internal helpers ─────────────────────────────────────────────────

def _read_products():
    """Read products.csv and return list of dicts (typed correctly)."""
    products = []
    with open(PRODUCTS_CSV, "r", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            products.append({
                "name":     row["name"],
                "price":    float(row["price"]),
                "stock":    int(row["stock"]),
                "category": row.get("category", "General"),
            })
    return products


def _write_products(products):
    """Overwrite products.csv with the given list of dicts."""
    with open(PRODUCTS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=PRODUCTS_FIELDS)
        writer.writeheader()
        writer.writerows(products)


# ── Product API ───────────────────────────────────────────────────────

def get_all_products():
    """Return list of all product dicts."""
    return _read_products()


def get_product(name):
    """Return one product dict by name, or None."""
    for p in _read_products():
        if p["name"] == name:
            return p
    return None


def update_stock(name, new_qty):
    """Set the stock of a product and save to CSV. Returns True on success."""
    products = _read_products()
    found = False
    for p in products:
        if p["name"] == name:
            p["stock"] = new_qty
            found = True
            break
    if found:
        _write_products(products)
    return found


def add_product(name, price, qty, category="General"):
    """Add a new product or update an existing one, then save to CSV."""
    products = _read_products()
    for p in products:
        if p["name"] == name:          # update existing
            p["price"]    = price
            p["stock"]    = qty
            p["category"] = category
            _write_products(products)
            return
    # new product
    products.append({"name": name, "price": price, "stock": qty, "category": category})
    _write_products(products)


# ── Sales API ─────────────────────────────────────────────────────────

def record_sale(session_id, item_name, qty, unit_price):
    """Append one sale line to sales.csv."""
    with open(SALES_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SALES_FIELDS)
        writer.writerow({
            "session_id": session_id,
            "item_name":  item_name,
            "qty":        qty,
            "unit_price": unit_price,
            "total":      round(qty * unit_price, 2),
            "sold_at":    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })


def get_sales_history(limit=50):
    """Return the last `limit` sales rows as list of dicts (newest first)."""
    rows = []
    with open(SALES_CSV, "r", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append(dict(row))
    return list(reversed(rows))[:limit]
