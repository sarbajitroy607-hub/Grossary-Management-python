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
class StaffUser(Base):
    __tablename__ = "staff_users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(120), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="cashier")  # "admin" or "cashier"
    name = Column(String(100), nullable=False)
    is_active = Column(Integer, nullable=False, default=1)
    last_login = Column(String(30), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "name": self.name,
            "is_active": bool(self.is_active),
            "last_login": self.last_login or "",
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else "",
        }


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


class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(100), index=True, nullable=True)
    customer_id = Column(Integer, index=True, nullable=True)
    item_name = Column(String(100), nullable=False)
    qty = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "customer_id": self.customer_id,
            "item_name": self.item_name,
            "qty": self.qty,
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

        # Seed default Admin and Cashier accounts if empty
        if db.query(StaffUser).count() == 0:
            admin_user = StaffUser(
                username="admin",
                email="admin@gmail.com",
                password_hash=generate_password_hash("123456"),
                role="admin",
                name="Store Administrator",
                is_active=1
            )
            cashier_user = StaffUser(
                username="cashier",
                email="cashier@store.io",
                password_hash=generate_password_hash("123456"),
                role="cashier",
                name="Lane 04 Cashier",
                is_active=1
            )
            db.add(admin_user)
            db.add(cashier_user)


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


def create_product(name, price, stock, category="General"):
    """
    Explicitly create a new product.
    Returns error if the product name already exists or inputs are invalid.
    """
    clean_name = str(name or "").lower().strip()
    if not clean_name:
        return {"success": False, "message": "Product name is required."}
    try:
        price_val = float(price)
        stock_val = int(stock)
    except (ValueError, TypeError):
        return {"success": False, "message": "Valid price and stock quantity are required."}

    if price_val <= 0:
        return {"success": False, "message": "Price must be greater than zero."}
    if stock_val < 0:
        return {"success": False, "message": "Stock cannot be negative."}

    clean_cat = str(category or "General").strip() or "General"

    with get_db() as db:
        existing = db.query(Product).filter(Product.name == clean_name).first()
        if existing:
            return {"success": False, "message": f"Product '{clean_name.capitalize()}' already exists."}

        prod = Product(
            name=clean_name,
            price=price_val,
            stock=stock_val,
            category=clean_cat
        )
        db.add(prod)
        db.flush()
        return {"success": True, "product": prod.to_dict(), "message": f"'{clean_name.capitalize()}' created successfully!"}


def update_product(name, new_name=None, price=None, stock=None, category=None):
    """
    Update details (name, price, stock, category) of an existing product.
    """
    clean_name = str(name or "").lower().strip()
    if not clean_name:
        return {"success": False, "message": "Product name is required."}

    with get_db() as db:
        prod = db.query(Product).filter(Product.name == clean_name).first()
        if not prod:
            return {"success": False, "message": f"Product '{clean_name.capitalize()}' not found."}

        # Rename check if new_name provided
        if new_name is not None:
            clean_new_name = str(new_name).lower().strip()
            if clean_new_name and clean_new_name != clean_name:
                conflict = db.query(Product).filter(Product.name == clean_new_name).first()
                if conflict:
                    return {"success": False, "message": f"A product named '{clean_new_name.capitalize()}' already exists."}
                prod.name = clean_new_name
                # Update any associated cart items
                db.query(CartItem).filter(CartItem.item_name == clean_name).update(
                    {CartItem.item_name: clean_new_name}, synchronize_session=False
                )

        if price is not None:
            try:
                p_val = float(price)
                if p_val <= 0:
                    return {"success": False, "message": "Price must be greater than zero."}
                prod.price = p_val
            except (ValueError, TypeError):
                return {"success": False, "message": "Invalid price value."}

        if stock is not None:
            try:
                s_val = int(stock)
                if s_val < 0:
                    return {"success": False, "message": "Stock cannot be negative."}
                prod.stock = s_val
            except (ValueError, TypeError):
                return {"success": False, "message": "Invalid stock value."}

        if category is not None:
            prod.category = str(category).strip() or "General"

        prod.updated_at = datetime.now(timezone.utc)
        return {"success": True, "product": prod.to_dict(), "message": "Product updated successfully."}


def delete_product(name):
    """
    Delete a product and its active cart reservations.
    """
    clean_name = str(name or "").lower().strip()
    if not clean_name:
        return {"success": False, "message": "Product name is required."}

    with get_db() as db:
        prod = db.query(Product).filter(Product.name == clean_name).first()
        if not prod:
            return {"success": False, "message": f"Product '{clean_name.capitalize()}' not found."}

        # Clean up any active cart items for this product
        db.query(CartItem).filter(CartItem.item_name == clean_name).delete(synchronize_session=False)

        db.delete(prod)
        return {"success": True, "message": f"Product '{clean_name.capitalize()}' deleted successfully."}


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


# ── Staff (Admin & Cashier) Authentication API ───────────────────────
def authenticate_staff(identifier, password):
    """
    Authenticate an Admin or Cashier staff member using either their email or username.
    Verifies passwords securely against salted cryptographic hashes.
    """
    id_clean = str(identifier or "").strip().lower()
    pass_clean = str(password or "").strip()
    if not id_clean or not pass_clean:
        return None

    with get_db() as db:
        staff = db.query(StaffUser).filter(
            ((StaffUser.email == id_clean) | (StaffUser.username == id_clean)),
            StaffUser.is_active == 1
        ).first()

        if staff and check_password_hash(staff.password_hash, pass_clean):
            staff.last_login = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            return staff.to_dict()
    return None


def create_staff_user(username, email, password, role="cashier", name=""):
    """Create a new staff user (Admin or Cashier)."""
    uname_clean = str(username or "").strip().lower()
    email_clean = str(email or "").strip().lower()
    pass_clean = str(password or "").strip()
    role_clean = str(role or "cashier").strip().lower()

    if role_clean not in ["admin", "cashier"]:
        return {"success": False, "message": "Role must be 'admin' or 'cashier'."}
    if not uname_clean or len(uname_clean) < 3:
        return {"success": False, "message": "Username must be at least 3 characters."}
    if not email_clean or "@" not in email_clean:
        return {"success": False, "message": "A valid email is required."}
    if len(pass_clean) < 6:
        return {"success": False, "message": "Password must be at least 6 characters."}

    with get_db() as db:
        existing = db.query(StaffUser).filter(
            (StaffUser.username == uname_clean) | (StaffUser.email == email_clean)
        ).first()
        if existing:
            return {"success": False, "message": "A user with this username or email already exists."}

        new_staff = StaffUser(
            username=uname_clean,
            email=email_clean,
            password_hash=generate_password_hash(pass_clean),
            role=role_clean,
            name=name.strip() or uname_clean.capitalize(),
            is_active=1
        )
        db.add(new_staff)
        db.flush()
        return {"success": True, "user": new_staff.to_dict(), "message": f"{role_clean.capitalize()} created successfully!"}


def change_staff_password(user_id, old_password, new_password):
    """Securely change staff user password."""
    if not user_id or not old_password or not new_password:
        return {"success": False, "message": "All password fields are required."}
    if len(str(new_password).strip()) < 6:
        return {"success": False, "message": "New password must be at least 6 characters."}

    with get_db() as db:
        staff = db.query(StaffUser).filter(StaffUser.id == int(user_id)).first()
        if not staff or not check_password_hash(staff.password_hash, str(old_password).strip()):
            return {"success": False, "message": "Current password incorrect."}

        staff.password_hash = generate_password_hash(str(new_password).strip())
        return {"success": True, "message": "Password updated successfully."}


def get_staff_user_by_id(user_id):
    """Retrieve staff user by ID."""
    if not user_id:
        return None
    with get_db() as db:
        staff = db.query(StaffUser).filter(StaffUser.id == int(user_id)).first()
        return staff.to_dict() if staff else None


def get_all_staff_users():
    """List all staff users."""
    with get_db() as db:
        users = db.query(StaffUser).order_by(StaffUser.id.asc()).all()
        return [u.to_dict() for u in users]


# ── Persistent Shopping Cart Operations ─────────────────────────────
def get_cart_db(session_id=None, customer_id=None):
    """
    Retrieve shopping cart contents as a {item_name: qty} dictionary.
    Prioritizes customer_id when logged in; falls back to session_id for guest users.
    """
    with get_db() as db:
        items = []
        if customer_id:
            items = db.query(CartItem).filter(CartItem.customer_id == int(customer_id)).all()
            if not items and session_id:
                items = db.query(CartItem).filter(
                    CartItem.session_id == str(session_id),
                    CartItem.customer_id.is_(None)
                ).all()
        elif session_id:
            items = db.query(CartItem).filter(
                CartItem.session_id == str(session_id),
                CartItem.customer_id.is_(None)
            ).all()

        cart = {}
        for it in items:
            cart[it.item_name] = cart.get(it.item_name, 0) + it.qty
        return cart


def add_to_cart_db(session_id, item_name, qty, customer_id=None):
    """Add or increment item quantity in persistent cart."""
    item_clean = str(item_name).lower().strip()
    qty = int(qty)
    if qty <= 0:
        return False

    with get_db() as db:
        query = db.query(CartItem).filter(CartItem.item_name == item_clean)
        if customer_id:
            cart_row = query.filter(CartItem.customer_id == int(customer_id)).first()
        else:
            cart_row = query.filter(
                CartItem.session_id == str(session_id),
                CartItem.customer_id.is_(None)
            ).first()

        if cart_row:
            cart_row.qty += qty
            cart_row.updated_at = datetime.now(timezone.utc)
        else:
            cart_row = CartItem(
                session_id=str(session_id) if session_id else None,
                customer_id=int(customer_id) if customer_id else None,
                item_name=item_clean,
                qty=qty,
            )
            db.add(cart_row)
        return True


def remove_from_cart_db(session_id, item_name, qty, customer_id=None):
    """Remove or decrement item quantity in persistent cart."""
    item_clean = str(item_name).lower().strip()
    qty = int(qty)
    if qty <= 0:
        return False

    with get_db() as db:
        query = db.query(CartItem).filter(CartItem.item_name == item_clean)
        if customer_id:
            cart_row = query.filter(CartItem.customer_id == int(customer_id)).first()
        else:
            cart_row = query.filter(
                CartItem.session_id == str(session_id),
                CartItem.customer_id.is_(None)
            ).first()

        if not cart_row:
            return False

        if qty >= cart_row.qty:
            db.delete(cart_row)
        else:
            cart_row.qty -= qty
            cart_row.updated_at = datetime.now(timezone.utc)
        return True


def clear_cart_db(session_id=None, customer_id=None):
    """Clear all items in persistent cart for session or customer."""
    with get_db() as db:
        query = db.query(CartItem)
        if customer_id:
            query.filter(CartItem.customer_id == int(customer_id)).delete(synchronize_session=False)
        if session_id:
            query.filter(
                CartItem.session_id == str(session_id),
                CartItem.customer_id.is_(None)
            ).delete(synchronize_session=False)
        return True


def merge_cart_on_login(session_id, customer_id):
    """Merge guest cart items into customer's persistent cart upon login or registration."""
    if not session_id or not customer_id:
        return
    with get_db() as db:
        guest_items = db.query(CartItem).filter(
            CartItem.session_id == str(session_id),
            CartItem.customer_id.is_(None)
        ).all()
        if not guest_items:
            return

        for g_item in guest_items:
            cust_item = db.query(CartItem).filter(
                CartItem.customer_id == int(customer_id),
                CartItem.item_name == g_item.item_name
            ).first()
            if cust_item:
                cust_item.qty += g_item.qty
                cust_item.updated_at = datetime.now(timezone.utc)
                db.delete(g_item)
            else:
                g_item.customer_id = int(customer_id)
                g_item.updated_at = datetime.now(timezone.utc)


# ── Transaction-Safe Inventory & Cart Operations ────────────────────
def reserve_stock_and_add_to_cart(session_id, item_name, qty, customer_id=None):
    """
    Atomically verifies inventory stock, decrements it, and adds to cart
    within a SINGLE database transaction.
    If stock is insufficient or any error occurs, rolls back cleanly.
    """
    clean_name = str(item_name or "").lower().strip()
    try:
        qty_int = int(qty)
    except (ValueError, TypeError):
        return {"success": False, "message": "Invalid quantity.", "status": 400}

    if qty_int <= 0:
        return {"success": False, "message": "Quantity must be > 0.", "status": 400}

    with get_db() as db:
        prod = db.query(Product).filter(Product.name == clean_name).with_for_update().first()
        if not prod:
            return {"success": False, "message": f"'{clean_name.capitalize()}' is not available.", "status": 404}
        if qty_int > prod.stock:
            return {"success": False, "message": f"Only {prod.stock} units in stock.", "status": 400}

        # Atomically deduct stock
        prod.stock -= qty_int
        prod.updated_at = datetime.now(timezone.utc)

        # Atomically update or insert cart item
        query = db.query(CartItem).filter(CartItem.item_name == clean_name)
        if customer_id:
            cart_row = query.filter(CartItem.customer_id == int(customer_id)).first()
        else:
            cart_row = query.filter(
                CartItem.session_id == str(session_id),
                CartItem.customer_id.is_(None)
            ).first()

        if cart_row:
            cart_row.qty += qty_int
            cart_row.updated_at = datetime.now(timezone.utc)
        else:
            cart_row = CartItem(
                session_id=str(session_id) if session_id else None,
                customer_id=int(customer_id) if customer_id else None,
                item_name=clean_name,
                qty=qty_int,
            )
            db.add(cart_row)

        return {
            "success": True,
            "message": f"Added {qty_int}x {clean_name.capitalize()} to cart!",
            "remaining_stock": prod.stock,
            "status": 200
        }


def release_stock_and_remove_from_cart(session_id, item_name, qty, customer_id=None):
    """
    Atomically increments inventory stock and removes/decrements from cart
    within a SINGLE database transaction.
    """
    clean_name = str(item_name or "").lower().strip()
    try:
        qty_int = int(qty)
    except (ValueError, TypeError):
        return {"success": False, "message": "Invalid quantity.", "status": 400}

    with get_db() as db:
        query = db.query(CartItem).filter(CartItem.item_name == clean_name)
        if customer_id:
            cart_row = query.filter(CartItem.customer_id == int(customer_id)).first()
        else:
            cart_row = query.filter(
                CartItem.session_id == str(session_id),
                CartItem.customer_id.is_(None)
            ).first()

        if not cart_row:
            return {"success": False, "message": f"'{clean_name.capitalize()}' not in cart.", "status": 404}
        if qty_int <= 0 or qty_int > cart_row.qty:
            return {"success": False, "message": f"You only have {cart_row.qty} in cart.", "status": 400}

        # Restock product
        prod = db.query(Product).filter(Product.name == clean_name).with_for_update().first()
        if prod:
            prod.stock += qty_int
            prod.updated_at = datetime.now(timezone.utc)

        # Update cart
        if qty_int >= cart_row.qty:
            db.delete(cart_row)
        else:
            cart_row.qty -= qty_int
            cart_row.updated_at = datetime.now(timezone.utc)

        return {
            "success": True,
            "message": f"Removed {qty_int}x {clean_name.capitalize()} from cart.",
            "status": 200
        }


def release_stock_and_clear_cart(session_id=None, customer_id=None):
    """
    Atomically restores all inventory quantities and clears the cart
    within a SINGLE database transaction.
    """
    with get_db() as db:
        query = db.query(CartItem)
        if customer_id:
            items = query.filter(CartItem.customer_id == int(customer_id)).all()
        elif session_id:
            items = query.filter(
                CartItem.session_id == str(session_id),
                CartItem.customer_id.is_(None)
            ).all()
        else:
            items = []

        for it in items:
            prod = db.query(Product).filter(Product.name == it.item_name).with_for_update().first()
            if prod:
                prod.stock += it.qty
                prod.updated_at = datetime.now(timezone.utc)
            db.delete(it)

        return {"success": True, "message": "Cart cleared and stock restored."}


def atomic_checkout(session_id, payment_method="Cash", tender_amount=0.0, customer_id=None, customer_name=None, customer_email=None):
    """
    Executes checkout as a single atomic ACID transaction:
    1. Validates and reads all cart items
    2. Builds receipt and verifies final amounts
    3. Persists each sale line into the `sales` table
    4. Clears active cart lines
    All within a SINGLE transaction. Any failure triggers full rollback.
    """
    with get_db() as db:
        query = db.query(CartItem)
        if customer_id:
            cart_rows = query.filter(CartItem.customer_id == int(customer_id)).all()
            if not cart_rows and session_id:
                cart_rows = db.query(CartItem).filter(
                    CartItem.session_id == str(session_id),
                    CartItem.customer_id.is_(None)
                ).all()
        elif session_id:
            cart_rows = query.filter(
                CartItem.session_id == str(session_id),
                CartItem.customer_id.is_(None)
            ).all()
        else:
            cart_rows = []

        if not cart_rows:
            return {"success": False, "message": "Your cart is empty!", "status": 400}

        # Consolidate cart items
        receipt = []
        for it in cart_rows:
            prod = db.query(Product).filter(Product.name == it.item_name).first()
            unit_price = float(prod.price) if prod else 0.0
            line_total = round(it.qty * unit_price, 2)
            receipt.append({
                "name": it.item_name,
                "qty": it.qty,
                "price": unit_price,
                "total": line_total
            })

        grand_total = sum(i["total"] for i in receipt)
        tax = round(grand_total * 0.0825, 2)
        final_due = round(grand_total + tax, 2)
        try:
            tender_val = float(tender_amount or 0.0)
        except (ValueError, TypeError):
            tender_val = 0.0

        clean_payment = str(payment_method or "Cash").strip()
        if clean_payment not in ["Cash", "UPI", "Card"]:
            clean_payment = "Cash"

        actual_tender = tender_val if (clean_payment == "Cash" and tender_val > 0) else final_due
        change_due = max(0.0, round(actual_tender - final_due, 2)) if clean_payment == "Cash" else 0.0
        sold_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Persist sale lines
        for item in receipt:
            sale = Sale(
                session_id=str(session_id) if session_id else "",
                customer_id=int(customer_id) if customer_id else None,
                customer_name=str(customer_name) if customer_name else None,
                item_name=item["name"],
                qty=item["qty"],
                unit_price=item["price"],
                total=item["total"],
                sold_at=sold_at,
                payment_method=clean_payment,
                tender_amount=actual_tender,
                change_due=change_due
            )
            db.add(sale)

        # Clear cart rows
        for it in cart_rows:
            db.delete(it)

        return {
            "success": True,
            "receipt": receipt,
            "grand_total": grand_total,
            "tax": tax,
            "final_due": final_due,
            "payment_method": clean_payment,
            "tender_amount": actual_tender,
            "change_due": change_due,
            "customer": {
                "id": customer_id,
                "name": customer_name,
                "email": customer_email
            } if customer_id else None,
            "status": 200
        }



