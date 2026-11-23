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
SALES_FIELDS    = ["session_id", "item_name", "qty", "unit_price", "total", "sold_at", "payment_method", "tender_amount", "change_due"]

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

    # sales.csv — just create a header-only file if missing, or migrate header if needed
    if not os.path.exists(SALES_CSV):
        with open(SALES_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=SALES_FIELDS)
            writer.writeheader()
    else:
        # Check if header needs migration to include payment_method, tender_amount, change_due
        try:
            with open(SALES_CSV, "r", newline="", encoding="utf-8") as f:
                first_line = f.readline().strip()
            if "tender_amount" not in first_line or "payment_method" not in first_line:
                with open(SALES_CSV, "r", newline="", encoding="utf-8") as f:
                    reader = list(csv.DictReader(f))
                with open(SALES_CSV, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=SALES_FIELDS)
                    writer.writeheader()
                    for r in reader:
                        if "payment_method" not in r or not r["payment_method"]:
                            r["payment_method"] = "Cash"
                        if "tender_amount" not in r:
                            r["tender_amount"] = r.get("total", 0.0)
                        if "change_due" not in r:
                            r["change_due"] = 0.0
                        writer.writerow({k: r.get(k, "") for k in SALES_FIELDS})
        except Exception:
            pass


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

def record_sale(session_id, item_name, qty, unit_price, payment_method="Cash", tender_amount=0.0, change_due=0.0):
    """Append one sale line to sales.csv with tender reconciliation."""
    with open(SALES_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SALES_FIELDS)
        writer.writerow({
            "session_id":     session_id,
            "item_name":      item_name,
            "qty":            qty,
            "unit_price":     unit_price,
            "total":          round(qty * unit_price, 2),
            "sold_at":        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "payment_method": payment_method or "Cash",
            "tender_amount":  round(float(tender_amount or 0.0), 2),
            "change_due":     round(float(change_due or 0.0), 2),
        })


def get_sales_history(limit=50):
    """Return the last `limit` sales rows as list of dicts (newest first)."""
    rows = []
    if os.path.exists(SALES_CSV):
        with open(SALES_CSV, "r", newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                rows.append(dict(row))
    return list(reversed(rows))[:limit]


def get_z_report(target_date=None):
    """
    Generate an End-of-Day (EOD) Z-Report summary for the specified date (YYYY-MM-DD).
    Defaults to today's date if target_date is None.
    """
    if not target_date:
        target_date = datetime.now().strftime("%Y-%m-%d")

    sales = []
    if os.path.exists(SALES_CSV):
        with open(SALES_CSV, "r", newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                sold_at = row.get("sold_at", "")
                if sold_at.startswith(target_date):
                    sales.append(row)

    total_items_sold = sum(int(s.get("qty", 1)) for s in sales)
    net_sales = sum(float(s.get("total", 0.0)) for s in sales)
    tax_rate = 0.0825
    tax_collected = round(net_sales * tax_rate, 2)
    gross_total = round(net_sales + tax_collected, 2)

    # Unique transactions (by session_id)
    unique_sessions = set(s.get("session_id") for s in sales if s.get("session_id"))
    transaction_count = len(unique_sessions) if unique_sessions else (1 if sales else 0)

    # Breakdown by payment method
    by_payment = {"Cash": 0.0, "UPI": 0.0, "Card": 0.0}
    for s in sales:
        method = s.get("payment_method") or "Cash"
        if method not in by_payment:
            by_payment[method] = 0.0
        by_payment[method] += float(s.get("total", 0.0))

    # Top selling products
    product_counts = {}
    product_revenue = {}
    for s in sales:
        item = s.get("item_name", "Unknown")
        qty = int(s.get("qty", 1))
        tot = float(s.get("total", 0.0))
        product_counts[item] = product_counts.get(item, 0) + qty
        product_revenue[item] = product_revenue.get(item, 0.0) + tot

    top_products = []
    for item in sorted(product_counts, key=product_counts.get, reverse=True)[:5]:
        top_products.append({
            "name": item,
            "qty": product_counts[item],
            "revenue": round(product_revenue[item] * (1 + tax_rate), 2)
        })

    return {
        "date": target_date,
        "lane": "Lane 04",
        "cashier": "Lane 04 Terminal",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "transaction_count": transaction_count,
        "total_items_sold": total_items_sold,
        "net_sales": round(net_sales, 2),
        "tax_rate": "8.25%",
        "tax_collected": tax_collected,
        "gross_total": gross_total,
        "payment_breakdown": {
            "Cash": round(by_payment.get("Cash", 0.0) * (1 + tax_rate), 2),
            "UPI": round(by_payment.get("UPI", 0.0) * (1 + tax_rate), 2),
            "Card": round(by_payment.get("Card", 0.0) * (1 + tax_rate), 2),
        },
        "top_products": top_products
    }
