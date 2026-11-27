"""
test_system.py — Comprehensive automated test suite for SQLite & SQLAlchemy integration.
"""

import os
import sys
import unittest
from datetime import datetime

# Add project directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import database
from app import app


class TestDatabaseAndAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Initialise DB (which triggers table creation and CSV migration)
        database.init_db()

    def setUp(self):
        self.client = app.test_client()

    def test_01_db_file_exists(self):
        """Verify that SQLite store.db was created in data/"""
        self.assertTrue(os.path.exists(database.DB_PATH), "store.db should exist")

    def test_02_products_migrated_or_seeded(self):
        """Verify that products exist in the SQLite database"""
        products = database.get_all_products()
        self.assertGreater(len(products), 0, "Products table should not be empty")
        # 'rice' should be present
        rice = database.get_product("rice")
        self.assertIsNotNone(rice, "Product 'rice' should exist")
        self.assertIn("price", rice)
        self.assertIn("stock", rice)
        self.assertIn("category", rice)

    def test_03_product_crud(self):
        """Test adding, retrieving, and updating stock via SQLAlchemy"""
        test_item_name = "organic_honey"
        # Add product
        database.add_product(test_item_name, 250.0, 15, "Organic")
        prod = database.get_product(test_item_name)
        self.assertIsNotNone(prod)
        self.assertEqual(prod["name"], test_item_name)
        self.assertEqual(prod["price"], 250.0)
        self.assertEqual(prod["stock"], 15)
        self.assertEqual(prod["category"], "Organic")

        # Update stock
        success = database.update_stock(test_item_name, 30)
        self.assertTrue(success)
        updated = database.get_product(test_item_name)
        self.assertEqual(updated["stock"], 30)

        # Update existing via add_product
        database.add_product(test_item_name, 260.0, 40, "Premium Organic")
        re_updated = database.get_product(test_item_name)
        self.assertEqual(re_updated["price"], 260.0)
        self.assertEqual(re_updated["stock"], 40)
        self.assertEqual(re_updated["category"], "Premium Organic")

    def test_04_sales_and_z_report(self):
        """Test recording sales and generating Z-reports"""
        session_id = "test-session-xyz"
        database.record_sale(
            session_id=session_id,
            item_name="rice",
            qty=2,
            unit_price=50.0,
            payment_method="UPI",
            tender_amount=100.0,
            change_due=0.0
        )

        history = database.get_sales_history(limit=10)
        self.assertGreater(len(history), 0)
        latest = history[0]
        self.assertEqual(latest["session_id"], session_id)
        self.assertEqual(latest["item_name"], "rice")
        self.assertEqual(latest["qty"], 2)
        self.assertEqual(latest["payment_method"], "UPI")

        today_str = datetime.now().strftime("%Y-%m-%d")
        report = database.get_z_report(today_str)
        self.assertIn("date", report)
        self.assertIn("net_sales", report)
        self.assertIn("gross_total", report)
        self.assertIn("payment_breakdown", report)
        self.assertIn("top_products", report)
        self.assertGreaterEqual(report["total_items_sold"], 2)

    def test_05_flask_api_items(self):
        """Test GET /api/items endpoint"""
        res = self.client.get("/api/items")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)
        first = data[0]
        self.assertIn("sku", first)
        self.assertIn("barcode", first)
        self.assertIn("name", first)

    def test_06_flask_cart_and_checkout_flow(self):
        """Test full add to cart, view cart, and checkout flow"""
        # Ensure we have stock for 'rice'
        database.update_stock("rice", 20)

        # Add to cart
        add_res = self.client.post("/api/cart/add", json={"item": "rice", "qty": 2})
        self.assertEqual(add_res.status_code, 200)
        self.assertTrue(add_res.get_json()["success"])

        # Check cart
        cart_res = self.client.get("/api/cart")
        self.assertEqual(cart_res.status_code, 200)
        cart_data = cart_res.get_json()
        self.assertEqual(len(cart_data["items"]), 1)
        self.assertEqual(cart_data["items"][0]["name"], "rice")
        self.assertEqual(cart_data["items"][0]["qty"], 2)

        # Checkout
        checkout_res = self.client.post("/api/checkout", json={
            "payment_method": "Cash",
            "tender_amount": 150.0
        })
        self.assertEqual(checkout_res.status_code, 200)
        checkout_data = checkout_res.get_json()
        self.assertTrue(checkout_data["success"])
        self.assertGreater(checkout_data["grand_total"], 0)
        self.assertGreater(checkout_data["change_due"], 0)

    def test_07_flask_admin_endpoints(self):
        """Test Admin login, adding item, updating stock, and checking sales"""
        # Unauthorized check
        unauth_res = self.client.post("/api/admin/stock", json={"item": "rice", "qty": 10})
        self.assertEqual(unauth_res.status_code, 403)

        # Admin login
        login_res = self.client.post("/api/admin/login", json={
            "email": "admin@gmail.com",
            "password": "123456"
        })
        self.assertEqual(login_res.status_code, 200)
        self.assertTrue(login_res.get_json()["success"])

        # Admin update stock
        stock_res = self.client.post("/api/admin/stock", json={"item": "rice", "qty": 50})
        self.assertEqual(stock_res.status_code, 200)
        self.assertTrue(stock_res.get_json()["success"])

        # Admin add new item
        new_item_res = self.client.post("/api/admin/add_item", json={
            "item": "green_tea",
            "price": 140.0,
            "qty": 25
        })
        self.assertEqual(new_item_res.status_code, 200)
        self.assertTrue(new_item_res.get_json()["success"])

        # Admin sales
        sales_res = self.client.get("/api/admin/sales")
        self.assertEqual(sales_res.status_code, 200)
        self.assertIsInstance(sales_res.get_json(), list)

    def test_08_customer_registration_and_validation(self):
        """Test customer registration, duplicate email handling, and password validation"""
        unique_email = f"alice_{datetime.now().strftime('%Y%m%d%H%M%S%f')}@gmail.com"

        # Invalid: missing name
        res = self.client.post("/api/customer/register", json={
            "name": "",
            "email": unique_email,
            "password": "password123"
        })
        self.assertEqual(res.status_code, 400)
        self.assertFalse(res.get_json()["success"])

        # Invalid: bad email
        res = self.client.post("/api/customer/register", json={
            "name": "Alex Smith",
            "email": "notanemail",
            "password": "password123"
        })
        self.assertEqual(res.status_code, 400)

        # Invalid: short password
        res = self.client.post("/api/customer/register", json={
            "name": "Alex Smith",
            "email": unique_email,
            "password": "12"
        })
        self.assertEqual(res.status_code, 400)

        # Valid registration
        res = self.client.post("/api/customer/register", json={
            "name": "Alice Wonder",
            "email": unique_email,
            "password": "alicepass123",
            "phone": "9876501234",
            "address": "42 Wonderland Ave"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["customer"]["name"], "Alice Wonder")
        self.assertEqual(data["customer"]["email"], unique_email)

        # Duplicate email registration should fail
        dup_res = self.client.post("/api/customer/register", json={
            "name": "Alice Duplicate",
            "email": unique_email,
            "password": "anotherpass"
        })
        self.assertEqual(dup_res.status_code, 400)
        self.assertFalse(dup_res.get_json()["success"])

    def test_09_customer_login_session_checkout_flow(self):
        """Test customer login, session retrieval (/api/customer/me), checkout association, and logout"""
        # Register a unique customer for login test
        unique_login_email = f"bob_{datetime.now().strftime('%Y%m%d%H%M%S%f')}@gmail.com"
        reg_res = self.client.post("/api/customer/register", json={
            "name": "Bob Builder",
            "email": unique_login_email,
            "password": "bobpassword123"
        })
        self.assertEqual(reg_res.status_code, 200)

        # Logout from registration auto-login to test explicit login
        self.client.post("/api/customer/logout")

        # Wrong password
        bad_res = self.client.post("/api/customer/login", json={
            "email": unique_login_email,
            "password": "wrongpassword"
        })
        self.assertEqual(bad_res.status_code, 401)
        self.assertFalse(bad_res.get_json()["success"])

        # Correct login
        login_res = self.client.post("/api/customer/login", json={
            "email": unique_login_email,
            "password": "bobpassword123"
        })
        self.assertEqual(login_res.status_code, 200)
        login_data = login_res.get_json()
        self.assertTrue(login_data["success"])
        self.assertEqual(login_data["customer"]["name"], "Bob Builder")

        # Check /api/customer/me
        me_res = self.client.get("/api/customer/me")
        self.assertEqual(me_res.status_code, 200)
        me_data = me_res.get_json()
        self.assertTrue(me_data["logged_in"])
        self.assertEqual(me_data["customer"]["email"], unique_login_email)

        # Make a purchase while logged in
        database.update_stock("rice", 20)
        self.client.post("/api/cart/add", json={"item": "rice", "qty": 1})
        checkout_res = self.client.post("/api/checkout", json={"payment_method": "Card"})
        self.assertEqual(checkout_res.status_code, 200)
        c_data = checkout_res.get_json()
        self.assertTrue(c_data["success"])
        self.assertIsNotNone(c_data.get("customer"))
        self.assertEqual(c_data["customer"]["name"], "Bob Builder")

        # Customer order history
        orders_res = self.client.get("/api/customer/orders")
        self.assertEqual(orders_res.status_code, 200)
        orders = orders_res.get_json()["orders"]
        self.assertGreater(len(orders), 0)
        self.assertEqual(orders[0]["customer_name"], "Bob Builder")

        # Logout
        logout_res = self.client.post("/api/customer/logout")
        self.assertEqual(logout_res.status_code, 200)
        self.assertTrue(logout_res.get_json()["success"])

        # Verify /api/customer/me shows logged out
        me_after_res = self.client.get("/api/customer/me")
        self.assertEqual(me_after_res.status_code, 200)
        self.assertFalse(me_after_res.get_json()["logged_in"])

    def test_10_staff_authentication_and_hashing(self):
        """Test staff password hashing and secure login authentication."""
        # Check staff users exist in DB with hashed passwords
        staff_users = database.get_all_staff_users()
        self.assertGreaterEqual(len(staff_users), 2)
        admin_user = next((u for u in staff_users if u["email"] == "admin@gmail.com"), None)
        self.assertIsNotNone(admin_user)
        self.assertEqual(admin_user["role"], "admin")

        # Database direct check: passwords are not stored in plaintext
        with database.get_db() as db:
            raw_admin = db.query(database.StaffUser).filter_by(email="admin@gmail.com").first()
            self.assertNotEqual(raw_admin.password_hash, "123456")
            self.assertTrue(raw_admin.password_hash.startswith("scrypt:") or raw_admin.password_hash.startswith("pbkdf2:"))

        # Authenticate with username
        auth_admin_uname = database.authenticate_staff("admin", "123456")
        self.assertIsNotNone(auth_admin_uname)
        self.assertEqual(auth_admin_uname["role"], "admin")

        # Authenticate with email
        auth_admin_email = database.authenticate_staff("admin@gmail.com", "123456")
        self.assertIsNotNone(auth_admin_email)

        # Authenticate cashier
        auth_cashier = database.authenticate_staff("cashier@store.io", "123456")
        self.assertIsNotNone(auth_cashier)
        self.assertEqual(auth_cashier["role"], "cashier")

        # Authentication failure with wrong password
        fail_auth = database.authenticate_staff("admin@gmail.com", "wrongpassword")
        self.assertIsNone(fail_auth)

        # Authentication failure with unknown user
        fail_user = database.authenticate_staff("unknown@store.io", "123456")
        self.assertIsNone(fail_user)

    def test_11_role_based_access_control(self):
        """Test RBAC route guards and API permissions for Admin and Cashier."""
        # 1. Unauthenticated checks
        # Page guards redirect to index (302)
        res_admin_page = self.client.get("/admin")
        self.assertEqual(res_admin_page.status_code, 302)
        self.assertIn("error=", res_admin_page.location)

        res_cashier_page = self.client.get("/cashier")
        self.assertEqual(res_cashier_page.status_code, 302)
        self.assertIn("error=", res_cashier_page.location)

        # API guards reject with 403
        res_z_report = self.client.get("/api/cashier/z_report")
        self.assertEqual(res_z_report.status_code, 403)

        res_admin_stock = self.client.post("/api/admin/stock", json={"item": "rice", "qty": 10})
        self.assertEqual(res_admin_stock.status_code, 403)

        res_admin_staff = self.client.get("/api/admin/staff")
        self.assertEqual(res_admin_staff.status_code, 403)

        # 2. Cashier Login Session
        cashier_login = self.client.post("/api/admin/login", json={
            "email": "cashier@store.io",
            "password": "123456"
        })
        self.assertEqual(cashier_login.status_code, 200)
        cashier_data = cashier_login.get_json()
        self.assertTrue(cashier_data["success"])
        self.assertEqual(cashier_data["role"], "cashier")

        # Cashier CAN access cashier page and z_report
        res_cashier_auth = self.client.get("/cashier")
        self.assertEqual(res_cashier_auth.status_code, 200)

        res_z_auth = self.client.get("/api/cashier/z_report")
        self.assertEqual(res_z_auth.status_code, 200)

        # Cashier CANNOT access admin page or admin APIs
        res_admin_from_cashier = self.client.get("/admin")
        self.assertEqual(res_admin_from_cashier.status_code, 302)

        res_stock_from_cashier = self.client.post("/api/admin/stock", json={"item": "rice", "qty": 10})
        self.assertEqual(res_stock_from_cashier.status_code, 403)

        res_staff_from_cashier = self.client.get("/api/admin/staff")
        self.assertEqual(res_staff_from_cashier.status_code, 403)

        # Cashier logout
        self.client.post("/api/admin/logout")

        # 3. Admin Login Session
        admin_login = self.client.post("/api/admin/login", json={
            "email": "admin@gmail.com",
            "password": "123456"
        })
        self.assertEqual(admin_login.status_code, 200)
        self.assertEqual(admin_login.get_json()["role"], "admin")

        # Admin CAN access admin page and cashier page
        self.assertEqual(self.client.get("/admin").status_code, 200)
        self.assertEqual(self.client.get("/cashier").status_code, 200)

        # Admin CAN access admin APIs and cashier z_report
        self.assertEqual(self.client.get("/api/cashier/z_report").status_code, 200)
        self.assertEqual(self.client.get("/api/admin/staff").status_code, 200)

        # Admin creates new staff user
        unique_uname = f"cashier_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        create_staff_res = self.client.post("/api/admin/staff", json={
            "username": unique_uname,
            "email": f"{unique_uname}@store.io",
            "password": "newpassword123",
            "role": "cashier",
            "name": "Jane Cashier"
        })
        self.assertEqual(create_staff_res.status_code, 201)
        self.assertTrue(create_staff_res.get_json()["success"])

        # Change staff password
        pw_change_res = self.client.post("/api/admin/change_password", json={
            "old_password": "123456",
            "new_password": "updatedadminpass123"
        })
        self.assertEqual(pw_change_res.status_code, 200)
        self.assertTrue(pw_change_res.get_json()["success"])

        # Restore original password for idempotency
        self.client.post("/api/admin/change_password", json={
            "old_password": "updatedadminpass123",
            "new_password": "123456"
        })

    def test_12_persistent_shopping_cart(self):
        """Test persistent shopping carts in SQLite, cross-session persistence, and login merge."""
        # Ensure sufficient stock
        database.update_stock("rice", 25)
        database.update_stock("flour", 25)

        # 1. Guest client adds items to cart
        guest_client = app.test_client()
        add1 = guest_client.post("/api/cart/add", json={"item": "rice", "qty": 3})
        self.assertEqual(add1.status_code, 200)
        add2 = guest_client.post("/api/cart/add", json={"item": "flour", "qty": 2})
        self.assertEqual(add2.status_code, 200)

        # Check in DB that CartItem records exist
        with database.get_db() as db:
            cart_rows = db.query(database.CartItem).all()
            self.assertGreaterEqual(len(cart_rows), 2)
            rice_row = db.query(database.CartItem).filter_by(item_name="rice").first()
            self.assertIsNotNone(rice_row)
            self.assertGreaterEqual(rice_row.qty, 3)

        # 2. Register a new customer in this same guest session -> carts should merge into customer_id
        cart_cust_email = f"cartuser_{datetime.now().strftime('%Y%m%d%H%M%S%f')}@store.io"
        reg_res = guest_client.post("/api/customer/register", json={
            "name": "Cart Customer",
            "email": cart_cust_email,
            "password": "cartpassword123"
        })
        self.assertEqual(reg_res.status_code, 200)
        cust_id = reg_res.get_json()["customer"]["id"]

        # Verify that CartItems now belong to cust_id in SQLite
        with database.get_db() as db:
            cust_items = db.query(database.CartItem).filter_by(customer_id=cust_id).all()
            self.assertEqual(len(cust_items), 2)
            names = [it.item_name for it in cust_items]
            self.assertIn("rice", names)
            self.assertIn("flour", names)

        # 3. Simulate another browser / fresh session client logging into this customer account
        second_client = app.test_client()
        login_res = second_client.post("/api/customer/login", json={
            "email": cart_cust_email,
            "password": "cartpassword123"
        })
        self.assertEqual(login_res.status_code, 200)

        # Second client gets cart -> persistent cart from SQLite is returned!
        cart_view = second_client.get("/api/cart")
        self.assertEqual(cart_view.status_code, 200)
        cart_data = cart_view.get_json()
        item_names = [i["name"] for i in cart_data["items"]]
        self.assertIn("rice", item_names)
        self.assertIn("flour", item_names)

        # 4. Remove 1 item
        rem_res = second_client.post("/api/cart/remove", json={"item": "rice", "qty": 1})
        self.assertEqual(rem_res.status_code, 200)

        # 5. Checkout
        checkout_res = second_client.post("/api/checkout", json={"payment_method": "Cash", "tender_amount": 500.0})
        self.assertEqual(checkout_res.status_code, 200)

        # Verify SQLite cart is now cleared for this customer
        with database.get_db() as db:
            remaining = db.query(database.CartItem).filter_by(customer_id=cust_id).all()
            self.assertEqual(len(remaining), 0)

    def test_13_complete_product_crud(self):
        """Test full Product CRUD: Create, Read (all/single), Update (price/stock/rename), Delete."""
        test_prod_name = f"test_item_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"

        # 1. CREATE
        # Unauthorized check
        unauth_create = self.client.post("/api/admin/product/create", json={
            "name": test_prod_name, "price": 85.0, "stock": 20, "category": "Dairy"
        })
        self.assertEqual(unauth_create.status_code, 403)

        # Authenticate as Admin
        self.client.post("/api/admin/login", json={"email": "admin@gmail.com", "password": "123456"})

        # Valid Create
        create_res = self.client.post("/api/admin/product/create", json={
            "name": test_prod_name,
            "price": 85.0,
            "stock": 20,
            "category": "Dairy"
        })
        self.assertEqual(create_res.status_code, 201)
        self.assertTrue(create_res.get_json()["success"])

        # Duplicate Create rejection
        dup_res = self.client.post("/api/admin/product/create", json={
            "name": test_prod_name, "price": 90.0, "stock": 10
        })
        self.assertEqual(dup_res.status_code, 400)
        self.assertFalse(dup_res.get_json()["success"])

        # Invalid Price Create rejection
        bad_price = self.client.post("/api/admin/product/create", json={
            "name": f"{test_prod_name}_bad", "price": -10.0, "stock": 5
        })
        self.assertEqual(bad_price.status_code, 400)

        # 2. READ
        # Read single product
        get_res = self.client.get(f"/api/items/{test_prod_name}")
        self.assertEqual(get_res.status_code, 200)
        prod_data = get_res.get_json()["product"]
        self.assertEqual(prod_data["name"], test_prod_name)
        self.assertEqual(prod_data["price"], 85.0)
        self.assertEqual(prod_data["stock"], 20)
        self.assertEqual(prod_data["category"], "Dairy")

        # Read non-existent product returns 404
        get_404 = self.client.get("/api/items/non_existent_item_xyz_999")
        self.assertEqual(get_404.status_code, 404)

        # 3. UPDATE
        # Update price, stock, category
        update_res = self.client.put(f"/api/admin/product/{test_prod_name}", json={
            "price": 95.0,
            "stock": 35,
            "category": "Beverages"
        })
        self.assertEqual(update_res.status_code, 200)
        self.assertTrue(update_res.get_json()["success"])

        # Verify update persisted
        updated_get = self.client.get(f"/api/items/{test_prod_name}").get_json()["product"]
        self.assertEqual(updated_get["price"], 95.0)
        self.assertEqual(updated_get["stock"], 35)
        self.assertEqual(updated_get["category"], "Beverages")

        # Rename product
        renamed_name = f"{test_prod_name}_renamed"
        rename_res = self.client.put(f"/api/admin/product/{test_prod_name}", json={
            "new_name": renamed_name
        })
        self.assertEqual(rename_res.status_code, 200)

        # Old name returns 404, new name returns 200
        self.assertEqual(self.client.get(f"/api/items/{test_prod_name}").status_code, 404)
        self.assertEqual(self.client.get(f"/api/items/{renamed_name}").status_code, 200)

        # 4. DELETE
        del_res = self.client.delete(f"/api/admin/product/{renamed_name}")
        self.assertEqual(del_res.status_code, 200)
        self.assertTrue(del_res.get_json()["success"])

        # Verify deleted
        self.assertEqual(self.client.get(f"/api/items/{renamed_name}").status_code, 404)

        # Subsequent delete returns 404
        del_again = self.client.delete(f"/api/admin/product/{renamed_name}")
        self.assertEqual(del_again.status_code, 404)

    def test_14_transaction_safe_inventory_and_atomic_checkout(self):
        """Test ACID atomic stock reservations, rollback safety, and atomic checkout."""
        item = f"atomic_item_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        database.add_product(item, 50.0, 10, "Staples")

        # Isolated test client
        client = app.test_client()

        # 1. Atomic reserve: add 4 items
        res1 = client.post("/api/cart/add", json={"item": item, "qty": 4})
        self.assertEqual(res1.status_code, 200)
        prod = database.get_product(item)
        self.assertEqual(prod["stock"], 6)

        # 2. Oversell attempt: try to add 7 when only 6 remain
        res2 = client.post("/api/cart/add", json={"item": item, "qty": 7})
        self.assertEqual(res2.status_code, 400)
        self.assertIn("Only 6 units in stock", res2.get_json()["message"])
        # Verify stock remained at 6 and was NOT corrupted
        prod = database.get_product(item)
        self.assertEqual(prod["stock"], 6)

        # 3. Partial remove: remove 2 items from cart
        res3 = client.post("/api/cart/remove", json={"item": item, "qty": 2})
        self.assertEqual(res3.status_code, 200)
        # Stock restored from 6 to 8
        prod = database.get_product(item)
        self.assertEqual(prod["stock"], 8)

        # 4. Atomic Checkout
        checkout_res = client.post("/api/checkout", json={
            "payment_method": "Cash",
            "tender_amount": 200.0
        })
        self.assertEqual(checkout_res.status_code, 200)
        data = checkout_res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["grand_total"], 100.0) # 2 units @ 50.0
        self.assertGreater(data["change_due"], 0)

        # Cart should now be empty
        cart_res = client.get("/api/cart")
        self.assertEqual(len(cart_res.get_json()["items"]), 0)

        # Final stock in DB remains 8 (10 initial - 2 purchased)
        final_prod = database.get_product(item)
        self.assertEqual(final_prod["stock"], 8)


if __name__ == "__main__":
    unittest.main()
