from flask import Flask, render_template, request, jsonify, session
import os

app = Flask(__name__)
app.secret_key = 'kiryana_store_secret_key_2024'

stock = {
    "rice": 10, "wheat": 10, "flour": 10, "oil": 10,
    "daal": 10, "soap": 10, "surf": 10,
}
prices = {
    "rice": 50.0, "wheat": 40.0, "flour": 30.0, "oil": 100.0,
    "daal": 60.0, "soap": 20.0, "surf": 25.0,
}
carts = {}

def get_cart():
    sid = session.get("sid")
    if not sid:
        import uuid
        sid = str(uuid.uuid4())
        session["sid"] = sid
    return carts.setdefault(sid, {})

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/user")
def user_page():
    return render_template("user.html")

@app.route("/admin")
def admin_page():
    return render_template("admin.html")

@app.route("/api/items")
def api_items():
    items = [{"name": n, "price": prices[n], "stock": q} for n, q in stock.items()]
    return jsonify(items)

@app.route("/api/cart")
def api_cart():
    cart = get_cart()
    items = [{"name": n, "qty": q, "price": prices.get(n, 0), "total": prices.get(n, 0)*q} for n, q in cart.items()]
    return jsonify({"items": items, "grand_total": sum(i["total"] for i in items)})

@app.route("/api/cart/add", methods=["POST"])
def api_cart_add():
    data = request.json
    item = data.get("item", "").lower().strip()
    try:
        qty = int(data.get("qty", 0))
    except:
        return jsonify({"success": False, "message": "Invalid quantity."}), 400
    if item not in stock:
        return jsonify({"success": False, "message": f"'{item}' is not available."}), 404
    if qty <= 0:
        return jsonify({"success": False, "message": "Quantity must be > 0."}), 400
    if qty > stock[item]:
        return jsonify({"success": False, "message": f"Only {stock[item]} units in stock."}), 400
    cart = get_cart()
    current = cart.get(item, 0)
    if current + qty > stock[item] + current:
        return jsonify({"success": False, "message": "Not enough stock."}), 400
    stock[item] -= qty
    cart[item] = current + qty
    return jsonify({"success": True, "message": f"Added {qty}x {item.capitalize()} to cart!"})

@app.route("/api/cart/remove", methods=["POST"])
def api_cart_remove():
    data = request.json
    item = data.get("item", "").lower().strip()
    try:
        qty = int(data.get("qty", 0))
    except:
        return jsonify({"success": False, "message": "Invalid quantity."}), 400
    cart = get_cart()
    if item not in cart:
        return jsonify({"success": False, "message": f"'{item}' not in cart."}), 404
    if qty <= 0 or qty > cart[item]:
        return jsonify({"success": False, "message": f"You only have {cart.get(item,0)} in cart."}), 400
    stock[item] += qty
    cart[item] -= qty
    if cart[item] == 0:
        del cart[item]
    return jsonify({"success": True, "message": f"Removed {qty}x {item.capitalize()} from cart."})

@app.route("/api/cart/clear", methods=["POST"])
def api_cart_clear():
    cart = get_cart()
    for item, qty in cart.items():
        if item in stock:
            stock[item] += qty
    cart.clear()
    return jsonify({"success": True})

@app.route("/api/checkout", methods=["POST"])
def api_checkout():
    cart = get_cart()
    if not cart:
        return jsonify({"success": False, "message": "Your cart is empty!"}), 400
    receipt = [{"name": n, "qty": q, "price": prices.get(n,0), "total": prices.get(n,0)*q} for n,q in cart.items()]
    grand_total = sum(i["total"] for i in receipt)
    cart.clear()
    return jsonify({"success": True, "receipt": receipt, "grand_total": grand_total})

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
    except:
        return jsonify({"success": False, "message": "Invalid quantity."}), 400
    if item not in stock:
        return jsonify({"success": False, "message": f"'{item}' does not exist."}), 404
    stock[item] = qty
    return jsonify({"success": True, "message": f"Stock for '{item.capitalize()}' updated to {qty}."})

@app.route("/api/admin/add_item", methods=["POST"])
def api_admin_add_item():
    if not session.get("admin"):
        return jsonify({"success": False, "message": "Unauthorized."}), 403
    data = request.json
    item = data.get("item", "").lower().strip()
    try:
        qty = int(data.get("qty", 0))
        price = float(data.get("price", 0))
    except:
        return jsonify({"success": False, "message": "Invalid quantity or price."}), 400
    if not item:
        return jsonify({"success": False, "message": "Item name required."}), 400
    stock[item] = qty
    prices[item] = price
    return jsonify({"success": True, "message": f"'{item.capitalize()}' added to store!"})

if __name__ == "__main__":
    app.run(debug=True, port=5000)
