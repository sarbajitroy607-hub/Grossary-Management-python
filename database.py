"""
database.py — SQLite & SQLAlchemy persistent storage for GroceryPro
-------------------------------------------------------------------
Replaces legacy CSV storage with an ACID-compliant SQLite relational
database managed via SQLAlchemy ORM. Includes automatic backward-compatible
migration for existing CSV records.
"""

import csv
import os
from contextlib import contextmanager
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    String,
    create_engine,
    desc,
    func,
    text,
)
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker
from werkzeug.security import check_password_hash, generate_password_hash

# ── Paths & Configuration ───────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "store.db")
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DB_PATH}")

PRODUCTS_CSV = os.path.join(DATA_DIR, "products.csv")
SALES_CSV = os.path.join(DATA_DIR, "sales.csv")

# Default stock seeded when no existing data or CSV is found
DEFAULT_PRODUCTS = [
    {"name": "rice", "price": 50.0, "stock": 10, "category": "Staples"},
    {"name": "wheat", "price": 40.0, "stock": 10, "category": "Staples"},
    {"name": "flour", "price": 30.0, "stock": 10, "category": "Staples"},
    {"name": "oil", "price": 100.0, "stock": 10, "category": "Oils"},
    {"name": "daal", "price": 60.0, "stock": 10, "category": "Staples"},
    {"name": "soap", "price": 20.0, "stock": 10, "category": "Cleaning"},
    {"name": "surf", "price": 25.0, "stock": 10, "category": "Cleaning"},
]

# ── SQLAlchemy Setup ─────────────────────────────────────────────────
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    echo=False,
)

SessionLocal = scoped_session(
    sessionmaker(autocommit=False, autoflush=False, bind=engine)
)

Base = declarative_base()


# ── Models ───────────────────────────────────────────────────────────
class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=True)
    address = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone or "",
            "address": self.address or "",
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else "",
        }


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    price = Column(Float, nullable=False)
    stock = Column(Integer, nullable=False, default=0)
    category = Column(String(100), nullable=False, default="General")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "name": self.name,
            "price": float(self.price),
            "stock": int(self.stock),
            "category": self.category or "General",
        }


class Sale(Base):
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(100), index=True, nullable=True)
    customer_id = Column(Integer, index=True, nullable=True)
    customer_name = Column(String(100), nullable=True)
    item_name = Column(String(100), nullable=False)
    qty = Column(Integer, nullable=False, default=1)
    unit_price = Column(Float, nullable=False)
    total = Column(Float, nullable=False)
    sold_at = Column(String(30), nullable=False, index=True)
    payment_method = Column(String(50), nullable=False, default="Cash")
    tender_amount = Column(Float, nullable=False, default=0.0)
    change_due = Column(Float, nullable=False, default=0.0)

    def to_dict(self):
        return {
            "session_id": self.session_id,
            "customer_id": self.customer_id,
            "customer_name": self.customer_name,
            "item_name": self.item_name,
            "qty": self.qty,
            "unit_price": self.unit_price,
            "total": self.total,
            "sold_at": self.sold_at,
            "payment_method": self.payment_method,
            "tender_amount": self.tender_amount,
            "change_due": self.change_due,
        }


# ── Database Session Context Manager ─────────────────────────────────
@contextmanager
def get_db():
    """Transactional database session scope context manager."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def close_db_session():
    """Removes current thread's scoped session."""
    SessionLocal.remove()


# ── Initialization & Migration ───────────────────────────────────────
def init_db():
    """
    Ensure the data/ folder exists, create all SQLite tables,
    and seamlessly migrate existing data from CSV files if present.
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    Base.metadata.create_all(bind=engine)

    # Safely migrate existing tables if columns are missing
    try:
        with engine.connect() as conn:
            res = conn.execute(text("PRAGMA table_info(sales);")).fetchall()
            cols = [r[1] for r in res]
            if "customer_id" not in cols:
                conn.execute(text("ALTER TABLE sales ADD COLUMN customer_id INTEGER;"))
            if "customer_name" not in cols:
                conn.execute(text("ALTER TABLE sales ADD COLUMN customer_name VARCHAR(100);"))
            conn.commit()
    except Exception:
        pass

    with get_db() as db:
        # Check products table
        product_count = db.query(Product).count()
        if product_count == 0:
            migrated = False
            if os.path.exists(PRODUCTS_CSV):
                try:
                    with open(PRODUCTS_CSV, "r", newline="", encoding="utf-8") as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            name = (row.get("name") or "").strip().lower()
                            if not name:
                                continue
                            price = float(row.get("price", 0.0))
                            stock = int(row.get("stock", 0))
                            category = (row.get("category") or "General").strip()
                            db.add(Product(name=name, price=price, stock=stock, category=category))
                    db.flush()
                    migrated = True
                except Exception as e:
                    print(f"Warning: Failed migrating products from CSV: {e}")

            if not migrated or db.query(Product).count() == 0:
                for item in DEFAULT_PRODUCTS:
                    db.add(Product(
                        name=item["name"],
                        price=float(item["price"]),
                        stock=int(item["stock"]),
                        category=item.get("category", "General")
                    ))

        # Check sales table
        sales_count = db.query(Sale).count()
        if sales_count == 0 and os.path.exists(SALES_CSV):
            try:
                with open(SALES_CSV, "r", newline="", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        item_name = (row.get("item_name") or "").strip().lower()
                        if not item_name:
                            continue
                        session_id = row.get("session_id", "")
                        qty = int(row.get("qty", 1))
                        unit_price = float(row.get("unit_price", 0.0))
                        total = float(row.get("total", qty * unit_price))
                        sold_at = row.get("sold_at") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        payment_method = row.get("payment_method") or "Cash"
                        tender_amount = float(row.get("tender_amount") or total)
                        change_due = float(row.get("change_due") or 0.0)

                        db.add(Sale(
                            session_id=session_id,
                            item_name=item_name,
                            qty=qty,
                            unit_price=unit_price,
                            total=total,
                            sold_at=sold_at,
                            payment_method=payment_method,
                            tender_amount=tender_amount,
                            change_due=change_due
                        ))
            except Exception as e:
                print(f"Warning: Failed migrating sales from CSV: {e}")

        # Seed demo customer if empty
        if db.query(Customer).count() == 0:
            demo_cust = Customer(
                name="Demo Shopper",
                email="customer@gmail.com",
                password_hash=generate_password_hash("customer123"),
                phone="9876543210",
                address="123 Market Street"
            )
            db.add(demo_cust)


# ── Product API ───────────────────────────────────────────────────────
def get_all_products():
    """Return list of all product dicts sorted by ID."""
    with get_db() as db:
        products = db.query(Product).order_by(Product.id.asc()).all()
        return [p.to_dict() for p in products]


def get_product(name):
    """Return one product dict by name, or None."""
    if not name:
        return None
    clean_name = str(name).lower().strip()
    with get_db() as db:
        p = db.query(Product).filter(Product.name == clean_name).first()
        return p.to_dict() if p else None


def update_stock(name, new_qty):
    """Set the stock of a product. Returns True on success, False if not found."""
    if not name:
        return False
    clean_name = str(name).lower().strip()
    with get_db() as db:
        p = db.query(Product).filter(Product.name == clean_name).first()
        if p:
            p.stock = int(new_qty)
            p.updated_at = datetime.now(timezone.utc)
            return True
        return False


def add_product(name, price, qty, category="General"):
    """Add a new product or update an existing one."""
    if not name:
        return
    clean_name = str(name).lower().strip()
    clean_cat = (category or "General").strip()
    with get_db() as db:
        p = db.query(Product).filter(Product.name == clean_name).first()
        if p:
            p.price = float(price)
            p.stock = int(qty)
            p.category = clean_cat
            p.updated_at = datetime.now(timezone.utc)
        else:
            new_p = Product(
                name=clean_name,
                price=float(price),
                stock=int(qty),
                category=clean_cat
            )
            db.add(new_p)


# ── Sales API ─────────────────────────────────────────────────────────
def record_sale(
    session_id,
    item_name,
    qty,
    unit_price,
    payment_method="Cash",
    tender_amount=0.0,
    change_due=0.0,
    customer_id=None,
    customer_name=None,
):
    """Insert one sale record with tender reconciliation into SQLite."""
    sold_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    qty_int = int(qty)
    price_val = float(unit_price)
    total_val = round(qty_int * price_val, 2)
    clean_item = str(item_name).lower().strip()

    with get_db() as db:
        sale = Sale(
            session_id=session_id,
            customer_id=int(customer_id) if customer_id else None,
            customer_name=str(customer_name).strip() if customer_name else None,
            item_name=clean_item,
            qty=qty_int,
            unit_price=price_val,
            total=total_val,
            sold_at=sold_at,
            payment_method=payment_method or "Cash",
            tender_amount=round(float(tender_amount or 0.0), 2),
            change_due=round(float(change_due or 0.0), 2),
        )
        db.add(sale)


def get_sales_history(limit=50):
    """Return the last `limit` sales rows as list of dicts (newest first)."""
    with get_db() as db:
        sales = db.query(Sale).order_by(desc(Sale.id)).limit(limit).all()
        return [s.to_dict() for s in sales]


def get_z_report(target_date=None):
    """
    Generate an End-of-Day (EOD) Z-Report summary for the specified date (YYYY-MM-DD).
    Defaults to today's date if target_date is None.
    """
    if not target_date:
        target_date = datetime.now().strftime("%Y-%m-%d")

    with get_db() as db:
        sales_models = db.query(Sale).filter(Sale.sold_at.like(f"{target_date}%")).all()
        sales = [s.to_dict() for s in sales_models]

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


# ── Customer Authentication & Management API ──────────────────────────
def register_customer(name, email, password, phone="", address=""):
    """Register a new customer with a securely hashed password."""
    name_clean = str(name or "").strip()
    email_clean = str(email or "").strip().lower()
    pass_clean = str(password or "").strip()

    if not name_clean:
        return {"success": False, "message": "Customer name is required."}
    if not email_clean or "@" not in email_clean or "." not in email_clean:
        return {"success": False, "message": "A valid email address is required."}
    if len(pass_clean) < 4:
        return {"success": False, "message": "Password must be at least 4 characters long."}

    with get_db() as db:
        existing = db.query(Customer).filter(Customer.email == email_clean).first()
        if existing:
            return {"success": False, "message": f"An account with email '{email_clean}' already exists."}

        new_customer = Customer(
            name=name_clean,
            email=email_clean,
            password_hash=generate_password_hash(pass_clean),
            phone=str(phone or "").strip(),
            address=str(address or "").strip()
        )
        db.add(new_customer)
        db.flush()
        return {"success": True, "customer": new_customer.to_dict(), "message": "Account created successfully!"}


def authenticate_customer(email, password):
    """Verify customer credentials. Returns customer dict on success, None on failure."""
    email_clean = str(email or "").strip().lower()
    pass_clean = str(password or "").strip()
    if not email_clean or not pass_clean:
        return None

    with get_db() as db:
        cust = db.query(Customer).filter(Customer.email == email_clean).first()
        if cust and check_password_hash(cust.password_hash, pass_clean):
            return cust.to_dict()
    return None


def get_customer_by_id(customer_id):
    """Retrieve customer by ID."""
    if not customer_id:
        return None
    with get_db() as db:
        cust = db.query(Customer).filter(Customer.id == int(customer_id)).first()
        return cust.to_dict() if cust else None


def get_customer_by_email(email):
    """Retrieve customer by email."""
    if not email:
        return None
    email_clean = str(email).strip().lower()
    with get_db() as db:
        cust = db.query(Customer).filter(Customer.email == email_clean).first()
        return cust.to_dict() if cust else None


def get_customer_orders(customer_id=None, customer_name=None, limit=50):
    """Retrieve orders placed by a specific customer."""
    with get_db() as db:
        query = db.query(Sale)
        if customer_id:
            query = query.filter(Sale.customer_id == int(customer_id))
        elif customer_name:
            query = query.filter(Sale.customer_name == str(customer_name).strip())
        sales = query.order_by(desc(Sale.id)).limit(limit).all()
        return [s.to_dict() for s in sales]

