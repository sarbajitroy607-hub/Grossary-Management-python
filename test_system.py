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


if __name__ == "__main__":
    unittest.main()
