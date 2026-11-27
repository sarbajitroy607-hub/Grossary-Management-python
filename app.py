from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from functools import wraps
from datetime import timedelta
import os
import uuid

from database import (
    init_db, get_all_products, get_product,
    update_stock, add_product, record_sale, get_sales_history, get_z_report,
    close_db_session, register_customer, authenticate_customer,
    get_customer_by_id, get_customer_by_email, get_customer_orders,
    authenticate_staff, create_staff_user, change_staff_password,
    get_staff_user_by_id, get_all_staff_users
)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'kiryana_store_secret_key_2024')
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.permanent_session_lifetime = timedelta(hours=8)

# Cleanup SQLAlchemy scoped session on application context teardown
@app.teardown_appcontext
def shutdown_session(exception=None):
    close_db_session()

# In-memory carts only (per session, not worth persisting)
carts = {}

# ── Initialise database on startup ──────────────────────────────────
init_db()


# ── Role-Based Access Control (RBAC) Decorators ─────────────────────
def admin_required(view_func):
    """Ensure user has authenticated administrator session."""
    @wraps(view_func)
    def decorated_function(*args, **kwargs):
        if not session.get("admin"):
            if request.path.startswith("/api/"):
                return jsonify({"success": False, "message": "Unauthorized: Administrator privileges required."}), 403
            return redirect(url_for("index", role="admin", error="Admin session required"))
        return view_func(*args, **kwargs)
    return decorated_function


def cashier_required(view_func):
    """Ensure user has authenticated cashier or admin session."""
    @wraps(view_func)
    def decorated_function(*args, **kwargs):
        if not (session.get("cashier") or session.get("admin")):
            if request.path.startswith("/api/"):
                return jsonify({"success": False, "message": "Unauthorized: Cashier or Admin access required."}), 403
            return redirect(url_for("index", role="cashier", error="Cashier session required"))
        return view_func(*args, **kwargs)
    return decorated_function


def get_cart():
    sid = session.get("sid")
    if not sid:
        sid = str(uuid.uuid4())
        session["sid"] = sid
    return carts.setdefault(sid, {}), sid


# ── Pages ────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/user")
def user_page():
    return render_template("user.html")

@app.route("/cashier")
@cashier_required
def cashier_page():
    return render_template("cashier.html")

@app.route("/admin")
@admin_required
def admin_page():
    return render_template("admin.html")


# ── Public API ───────────────────────────────────────────────────────
@app.route("/api/items")
def api_items():
    products = get_all_products()
    items = []
    for i, p in enumerate(products, 1):
        name = p["name"]
        items.append({
            "name": name,
            "price": p["price"],
            "stock": p["stock"],
            "category": p.get("category", "General"),
            "sku": f"GP-{name[:3].upper()}",
            "barcode": f"890{i:05d}"
        })
    return jsonify(items)


@app.route("/api/cart")
def api_cart():
    cart, _ = get_cart()
    items = []
    for name, qty in cart.items():
        prod = get_product(name)
        price = prod["price"] if prod else 0
        items.append({"name": name, "qty": qty, "price": price, "total": price * qty})
    return jsonify({"items": items, "grand_total": sum(i["total"] for i in items)})


@app.route("/api/cart/add", methods=["POST"])
def api_cart_add():
    data = request.json
    item = data.get("item", "").lower().strip()
    try:
        qty = int(data.get("qty", 0))
    except Exception:
        return jsonify({"success": False, "message": "Invalid quantity."}), 400

    prod = get_product(item)
    if not prod:
        return jsonify({"success": False, "message": f"'{item}' is not available."}), 404
    if qty <= 0:
        return jsonify({"success": False, "message": "Quantity must be > 0."}), 400
    if qty > prod["stock"]:
        return jsonify({"success": False, "message": f"Only {prod['stock']} units in stock."}), 400

    cart, _ = get_cart()
    current = cart.get(item, 0)
    new_stock = prod["stock"] - qty
    update_stock(item, new_stock)
    cart[item] = current + qty
    return jsonify({"success": True, "message": f"Added {qty}x {item.capitalize()} to cart!"})


@app.route("/api/cart/remove", methods=["POST"])
def api_cart_remove():
    data = request.json
    item = data.get("item", "").lower().strip()
    try:
        qty = int(data.get("qty", 0))
    except Exception:
        return jsonify({"success": False, "message": "Invalid quantity."}), 400

    cart, _ = get_cart()
    if item not in cart:
        return jsonify({"success": False, "message": f"'{item}' not in cart."}), 404
    if qty <= 0 or qty > cart[item]:
        return jsonify({"success": False, "message": f"You only have {cart.get(item,0)} in cart."}), 400

    prod = get_product(item)
    if prod:
        update_stock(item, prod["stock"] + qty)
    cart[item] -= qty
    if cart[item] == 0:
        del cart[item]
    return jsonify({"success": True, "message": f"Removed {qty}x {item.capitalize()} from cart."})


@app.route("/api/cart/clear", methods=["POST"])
def api_cart_clear():
    cart, _ = get_cart()
    for name, qty in cart.items():
        prod = get_product(name)
        if prod:
            update_stock(name, prod["stock"] + qty)
    cart.clear()
    return jsonify({"success": True})


@app.route("/api/checkout", methods=["POST"])
def api_checkout():
    cart, sid = get_cart()
    if not cart:
        return jsonify({"success": False, "message": "Your cart is empty!"}), 400

    data = request.json or {}
    payment_method = str(data.get("payment_method", "Cash")).strip()
    if payment_method not in ["Cash", "UPI", "Card"]:
        payment_method = "Cash"
    try:
        tender_amount = float(data.get("tender_amount", 0.0) or 0.0)
    except Exception:
        tender_amount = 0.0

    receipt = []
    for name, qty in cart.items():
        prod = get_product(name)
        price = prod["price"] if prod else 0
        total = price * qty
        receipt.append({"name": name, "qty": qty, "price": price, "total": total})

    grand_total = sum(i["total"] for i in receipt)
    tax = round(grand_total * 0.0825, 2)
    final_due = round(grand_total + tax, 2)
    actual_tender = tender_amount if (payment_method == "Cash" and tender_amount > 0) else final_due
    change_due = max(0.0, round(actual_tender - final_due, 2)) if payment_method == "Cash" else 0.0

    cust_id = session.get("customer_id")
    cust_name = session.get("customer_name")
    cust_email = session.get("customer_email")

    # Persist each sale line to the database
    for item in receipt:
        record_sale(
            sid, item["name"], item["qty"], item["price"],
            payment_method=payment_method,
            tender_amount=actual_tender,
            change_due=change_due,
            customer_id=cust_id,
            customer_name=cust_name
        )

    cart.clear()
    return jsonify({
        "success": True,
        "receipt": receipt,
        "grand_total": grand_total,
        "tax": tax,
        "final_due": final_due,
        "payment_method": payment_method,
        "tender_amount": tender_amount,
        "change_due": change_due,
        "customer": {
            "id": cust_id,
            "name": cust_name,
            "email": cust_email
        } if cust_id else None
    })


@app.route("/api/cashier/z_report")
@cashier_required
def api_cashier_z_report():
    target_date = request.args.get("date")
    report = get_z_report(target_date)
    return jsonify({"success": True, "report": report})


# ── Staff (Admin & Cashier) Auth API ─────────────────────────────────
@app.route("/api/admin/login", methods=["POST"])
def api_admin_login():
    data = request.json or {}
    identifier = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", "")).strip()

    if not identifier or not password:
        return jsonify({"success": False, "message": "Email/Username and password required."}), 400

    staff = authenticate_staff(identifier, password)
    if staff:
        # Prevent session fixation
        sid = session.get("sid")
        session.clear()
        if sid:
            session["sid"] = sid
        session["user_id"] = staff["id"]
        session["user_name"] = staff["name"]
        session["user_email"] = staff["email"]
        session["role"] = staff["role"]

        if staff["role"] == "admin":
            session["admin"] = True
            session["cashier"] = True
            return jsonify({"success": True, "role": "admin", "user": staff})
        elif staff["role"] == "cashier":
            session["cashier"] = True
            return jsonify({"success": True, "role": "cashier", "user": staff})

    return jsonify({"success": False, "message": "Invalid credentials. For Admin use admin@gmail.com / 123456; For Cashier use cashier@store.io / 123456"}), 401


@app.route("/api/admin/logout", methods=["POST"])
def api_admin_logout():
    session.pop("admin", None)
    session.pop("cashier", None)
    session.pop("role", None)
    session.pop("user_id", None)
    session.pop("user_name", None)
    session.pop("user_email", None)
    return jsonify({"success": True, "message": "Logged out successfully."})


@app.route("/api/admin/change_password", methods=["POST"])
@cashier_required
def api_admin_change_password():
    data = request.json or {}
    old_password = str(data.get("old_password", "")).strip()
    new_password = str(data.get("new_password", "")).strip()
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"success": False, "message": "Staff session required."}), 401
    result = change_staff_password(user_id, old_password, new_password)
    status_code = 200 if result.get("success") else 400
    return jsonify(result), status_code


@app.route("/api/admin/staff", methods=["GET", "POST"])
@admin_required
def api_admin_staff():
    if request.method == "POST":
        data = request.json or {}
        username = data.get("username", "")
        email = data.get("email", "")
        password = data.get("password", "")
        role = data.get("role", "cashier")
        name = data.get("name", "")
        result = create_staff_user(username, email, password, role, name)
        status_code = 201 if result.get("success") else 400
        return jsonify(result), status_code
    else:
        staff_list = get_all_staff_users()
        return jsonify({"success": True, "staff": staff_list})


@app.route("/api/admin/stock", methods=["POST"])
@admin_required
def api_admin_stock():
    data = request.json or {}
    item = data.get("item", "").lower().strip()
    try:
        qty = int(data.get("qty", 0))
    except Exception:
        return jsonify({"success": False, "message": "Invalid quantity."}), 400

    if not get_product(item):
        return jsonify({"success": False, "message": f"'{item}' does not exist."}), 404
    update_stock(item, qty)
    return jsonify({"success": True, "message": f"Stock for '{item.capitalize()}' updated to {qty}."})


@app.route("/api/admin/add_item", methods=["POST"])
@admin_required
def api_admin_add_item():
    data = request.json or {}
    item = data.get("item", "").lower().strip()
    try:
        qty   = int(data.get("qty", 0))
        price = float(data.get("price", 0))
    except Exception:
        return jsonify({"success": False, "message": "Invalid quantity or price."}), 400
    if not item:
        return jsonify({"success": False, "message": "Item name required."}), 400

    add_product(item, price, qty)
    return jsonify({"success": True, "message": f"'{item.capitalize()}' added to store!"})


@app.route("/api/admin/sales")
@admin_required
def api_admin_sales():
    """Bonus endpoint: recent sales history."""
    return jsonify(get_sales_history())


# ── Customer Auth API ────────────────────────────────────────────────
@app.route("/api/customer/register", methods=["POST"])
def api_customer_register():
    data = request.json or {}
    name = data.get("name", "")
    email = data.get("email", "")
    password = data.get("password", "")
    phone = data.get("phone", "")
    address = data.get("address", "")

    result = register_customer(name, email, password, phone, address)
    if not result.get("success"):
        return jsonify(result), 400

    customer = result["customer"]
    session["customer_id"] = customer["id"]
    session["customer_name"] = customer["name"]
    session["customer_email"] = customer["email"]
    session["role"] = "customer"

    return jsonify({
        "success": True,
        "message": "Registration successful! You are now logged in.",
        "customer": customer
    })


@app.route("/api/customer/login", methods=["POST"])
def api_customer_login():
    data = request.json or {}
    email = data.get("email", "")
    password = data.get("password", "")

    customer = authenticate_customer(email, password)
    if not customer:
        return jsonify({"success": False, "message": "Invalid email or password."}), 401

    session["customer_id"] = customer["id"]
    session["customer_name"] = customer["name"]
    session["customer_email"] = customer["email"]
    session["role"] = "customer"

    return jsonify({
        "success": True,
        "message": f"Welcome back, {customer['name']}!",
        "customer": customer
    })


@app.route("/api/customer/logout", methods=["POST"])
def api_customer_logout():
    session.pop("customer_id", None)
    session.pop("customer_name", None)
    session.pop("customer_email", None)
    if session.get("role") == "customer":
        session.pop("role", None)
    return jsonify({"success": True, "message": "Logged out successfully."})


@app.route("/api/customer/me")
def api_customer_me():
    customer_id = session.get("customer_id")
    if not customer_id:
        return jsonify({"logged_in": False})

    customer = get_customer_by_id(customer_id)
    if not customer:
        session.pop("customer_id", None)
        session.pop("customer_name", None)
        session.pop("customer_email", None)
        return jsonify({"logged_in": False})

    return jsonify({
        "logged_in": True,
        "customer": customer
    })


@app.route("/api/customer/orders")
def api_customer_orders():
    customer_id = session.get("customer_id")
    if not customer_id:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    orders = get_customer_orders(customer_id=customer_id)
    return jsonify({"success": True, "orders": orders})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
