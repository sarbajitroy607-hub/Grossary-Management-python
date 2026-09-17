from flask import Flask, render_template, request, jsonify, session
import os
import uuid

from database import (
    init_db, get_all_products, get_product,
    update_stock, add_product, record_sale, get_sales_history
)

app = Flask(__name__)
app.secret_key = 'kiryana_store_secret_key_2024'

# In-memory carts only (per session, not worth persisting)
carts = {}

# ── Initialise database on startup ──────────────────────────────────
init_db()


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

@app.route("/admin")
def admin_page():
    return render_template("admin.html")


# ── Public API ───────────────────────────────────────────────────────
@app.route("/api/items")
def api_items():
    products = get_all_products()
    items = [{"name": p["name"], "price": p["price"], "stock": p["stock"]} for p in products]
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

    receipt = []
    for name, qty in cart.items():
        prod = get_product(name)
        price = prod["price"] if prod else 0
        total = price * qty
        receipt.append({"name": name, "qty": qty, "price": price, "total": total})
        # Persist each sale line to the database
        record_sale(sid, name, qty, price)

    grand_total = sum(i["total"] for i in receipt)
    cart.clear()
    return jsonify({"success": True, "receipt": receipt, "grand_total": grand_total})


# ── Admin API ────────────────────────────────────────────────────────
@app.route("/api/admin/login", methods=["POST"])
def api_admin_login():
    data = request.json
    if data.get("email") == "admin@gmail.com" and data.get("password") == "123456":
        session["admin"] = True
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "Invalid credentials."}), 401


@app.route("/api/admin/logout", methods=["POST"])
def api_admin_logout():
    session.pop("admin", None)
    return jsonify({"success": True})


@app.route("/api/admin/stock", methods=["POST"])
def api_admin_stock():
    if not session.get("admin"):
        return jsonify({"success": False, "message": "Unauthorized."}), 403
    data = request.json
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
def api_admin_add_item():
    if not session.get("admin"):
        return jsonify({"success": False, "message": "Unauthorized."}), 403
    data = request.json
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
def api_admin_sales():
    """Bonus endpoint: recent sales history."""
    if not session.get("admin"):
        return jsonify({"success": False, "message": "Unauthorized."}), 403
    return jsonify(get_sales_history())


if __name__ == "__main__":
    app.run(debug=True, port=5000)
