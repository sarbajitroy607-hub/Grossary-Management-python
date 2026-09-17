"""
database.py — SQLite persistent storage for GroceryPro
Data is saved to  store_data.db  in the project folder.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "store_data.db")


def get_connection():
    """Return a connection with row_factory so rows behave like dicts."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """
    Create tables if they don't exist and seed default stock/prices
    only on the very first run (when the table is empty).
    """
    conn = get_connection()
    c = conn.cursor()

    # ── Products table ──────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS products (
            name    TEXT PRIMARY KEY,
            price   REAL NOT NULL,
            stock   INTEGER NOT NULL DEFAULT 0,
            category TEXT DEFAULT 'General',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ── Sales / receipt history ──────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id  TEXT NOT NULL,
            item_name   TEXT NOT NULL,
            qty         INTEGER NOT NULL,
            unit_price  REAL NOT NULL,
            total       REAL NOT NULL,
            sold_at     DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ── Seed default data only if products table is empty ───────────
    c.execute("SELECT COUNT(*) FROM products")
    if c.fetchone()[0] == 0:
        defaults = [
            ("rice",  50.0,  10, "Staples"),
            ("wheat", 40.0,  10, "Staples"),
            ("flour", 30.0,  10, "Staples"),
            ("oil",  100.0,  10, "Oils"),
            ("daal",  60.0,  10, "Staples"),
            ("soap",  20.0,  10, "Cleaning"),
            ("surf",  25.0,  10, "Cleaning"),
        ]
        c.executemany(
            "INSERT INTO products (name, price, stock, category) VALUES (?, ?, ?, ?)",
            defaults
        )

    conn.commit()
    conn.close()


# ── Product helpers ─────────────────────────────────────────────────

def get_all_products():
    """Return list of all products as dicts."""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM products ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_product(name):
    """Return a single product dict or None."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM products WHERE name = ?", (name,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_stock(name, new_qty):
    """Set stock to new_qty for a product. Returns True on success."""
    conn = get_connection()
    cur = conn.execute(
        "UPDATE products SET stock = ?, updated_at = CURRENT_TIMESTAMP WHERE name = ?",
        (new_qty, name)
    )
    conn.commit()
    conn.close()
    return cur.rowcount > 0


def add_product(name, price, qty, category="General"):
    """Insert or replace a product."""
    conn = get_connection()
    conn.execute(
        """INSERT INTO products (name, price, stock, category)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(name) DO UPDATE SET
               price    = excluded.price,
               stock    = excluded.stock,
               category = excluded.category,
               updated_at = CURRENT_TIMESTAMP""",
        (name, price, qty, category)
    )
    conn.commit()
    conn.close()


# ── Sales helpers ────────────────────────────────────────────────────

def record_sale(session_id, item_name, qty, unit_price):
    """Insert one line-item sale record."""
    conn = get_connection()
    conn.execute(
        "INSERT INTO sales (session_id, item_name, qty, unit_price, total) VALUES (?, ?, ?, ?, ?)",
        (session_id, item_name, qty, unit_price, qty * unit_price)
    )
    conn.commit()
    conn.close()


def get_sales_history(limit=50):
    """Return recent sales, newest first."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM sales ORDER BY sold_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
