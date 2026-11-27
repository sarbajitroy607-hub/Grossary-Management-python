# GroceryPro — Grocery Store Management & POS System

A modern, full-featured **Grocery Store Management & Point of Sale (POS)** web application built with **Python**, **Flask**, **SQLAlchemy**, and **SQLite**. The system provides separate portals for online customers, in-store cashiers, and store managers/administrators with role-based access control, cryptographic password hashing, real-time inventory management, and automated sales reporting.

---

## 🚀 Key Features

### 1. 🗄️ SQLite Database with SQLAlchemy ORM & Transaction-Safe Inventory
- **ACID-Compliant Persistence**: Replaced flat CSV files with an SQLite relational database (`data/store.db`) managed via SQLAlchemy ORM.
- **Transaction-Safe Inventory Updates**: Stock validation, reservation, decrementing, and restoration are executed within isolated atomic database transactions (`with_for_update` row locking / single-transaction commits). Prevents race conditions, overselling, and inventory leakage.
- **Atomic Checkout**: Receipt calculation, sale line item persistence, and active cart cleanup run as a single atomic transaction. Any error triggers an immediate, full rollback.
- **Automatic Migration**: Automatically scans and migrates existing CSV catalog items and sales history on startup without data loss.
- **Connection Management**: Scoped session lifecycle with automatic cleanup handlers on teardown.

### 2. 🔐 Secure Authentication & Role-Based Access Control (RBAC)
- **Cryptographic Password Hashing**: Passwords for customers and staff (Admins and Cashiers) are hashed using salted cryptographic hashing (Werkzeug `generate_password_hash` / `check_password_hash`).
- **Route & API Guards**:
  - `@admin_required`: Restricts inventory restocking, new product creation, staff management, and sales audits to verified administrators.
  - `@cashier_required`: Protects POS transaction terminals and end-of-day Z-Report generation.
  - Unauthenticated access to protected pages automatically redirects to the login portal with informative alerts.
  - Protected API endpoints reject unauthorized calls with `403 Forbidden`.
- **Session Security**: Session cookies configured with `HttpOnly` and `SameSite=Lax` flags, 8-hour lifetime, and session fixation prevention upon login.

### 3. 🛒 Customer Shopping Portal & Persistent Carts (`/user`)
- **Persistent Shopping Carts in SQLite**: Cart items are stored in the `cart_items` table in SQLite rather than volatile server memory. Carts survive server restarts, crashes, and browser reloads.
- **Guest-to-Customer Cart Merge**: Unauthenticated shoppers who add items to their cart retain those items seamlessly when registering or logging in.
- **Cross-Session Retrieval**: Logged-in customers can access their saved shopping cart across different sessions or devices.
- **Customer Registration & Login**: Customers can self-register with their name, email, password, phone, and delivery address.
- **Live Catalog & Cart**: Browse products by category with real-time stock indicators, add/remove quantities, and view live totals.
- **Customer Profiles & Order History**: View previous receipts and order history directly linked to customer accounts.

### 4. 🧾 Cashier Point of Sale (POS) (`/cashier`)
- **Fast Checkout Flow**: Quick product addition, barcode/SKU lookup, and touch keypad.
- **Multiple Payment Tender**: Supports Cash, UPI, and Card. Cash transactions include real-time change calculation.
- **Z-Report Daily Totals**: Generates daily financial summaries showing gross total, tax, net sales, payment method breakdowns, and top-selling items.

### 5. 📊 Admin Dashboard & Full Product CRUD (`/admin`)
- **Full Product CRUD Lifecycle**:
  - **Create**: Add new products with name, price, stock, and category (`POST /api/admin/product/create`, `POST /api/admin/add_item`).
  - **Read**: Fetch catalog listings (`GET /api/items`) or inspect individual products (`GET /api/items/<item_name>`).
  - **Update**: Edit product prices, stock quantities, categories, or rename products with real-time cart synchronization (`PUT /api/admin/product/<item_name>`).
  - **Delete**: Permanently remove items and clean up corresponding active cart reservations (`DELETE /api/admin/product/<item_name>`).
- **Stock Management**: Live stock level tracking, instant inventory adjustment, and low-stock warnings.
- **Staff Administration**: Create new cashier or admin accounts and update passwords.
- **Sales Analytics**: Full transaction log showing date, session, payment method, customer details, and line totals.

---

## 📁 Project Structure

```text
Grossary-Management-python-main/
├── app.py                  # Core Flask web application & API routing
├── database.py             # SQLAlchemy models, SQLite configuration & CRUD functions
├── requirements.txt        # Python package dependencies
├── test_system.py          # Comprehensive 14-test automated suite
├── data/
│   ├── store.db            # SQLite database file (auto-generated)
│   ├── products.csv        # Legacy/migration product catalog
│   └── sales.csv           # Legacy/migration sales log
├── templates/
│   ├── index.html          # Portal gateway & staff login page
│   ├── user.html           # Customer storefront & shopping portal
│   ├── cashier.html        # Cashier POS terminal & Z-Report
│   └── admin.html          # Admin dashboard & inventory controls
└── static/
    ├── css/                # Responsive styling for POS & portals
    └── js/                 # Client-side cart, receipt & API integrations
```

---

## 🛠️ Installation & Setup

### 1. Prerequisites
- **Python 3.10+** installed on your system.

### 2. Install Dependencies
Navigate to the project directory and install the required packages:

```bash
pip install -r requirements.txt
```

*(Dependencies: `Flask>=3.0.0`, `SQLAlchemy>=2.0.0`)*

### 3. Run the Application
Start the Flask development server:

```bash
python app.py
```

The application will start at **`http://localhost:5000`**.

---

## 🌐 Portals & Default Credentials

| Portal | URL | Access Level | Default Credentials |
| :--- | :--- | :--- | :--- |
| **Main Portal Gateway** | `http://localhost:5000/` | Public | Select Staff Login or Customer Store |
| **Customer Store** | `http://localhost:5000/user` | Public / Customer | Self-register or log in with customer account |
| **Cashier POS** | `http://localhost:5000/cashier` | Cashier / Admin | **ID/Email:** `cashier@store.io`<br>**PIN/Password:** `123456` |
| **Admin Dashboard** | `http://localhost:5000/admin` | Admin Only | **ID/Email:** `admin@gmail.com`<br>**PIN/Password:** `123456` |

*Note: Default accounts are seeded automatically into SQLite on first startup with cryptographic password hashes.*

---

## 🧪 Automated Testing

A full automated test suite is provided to verify all core features:

```bash
python test_system.py
```

### Test Coverage (14 Comprehensive Tests)
1. `test_01_db_file_exists`: Verifies SQLite database file creation.
2. `test_02_products_migrated_or_seeded`: Verifies product seeding & CSV migration.
3. `test_03_product_crud`: Tests adding, updating, and querying products via SQLAlchemy.
4. `test_04_sales_and_z_report`: Validates sale persistence and Z-Report calculations.
5. `test_05_flask_api_items`: Checks public catalog API with SKU/barcode formatting.
6. `test_06_flask_cart_and_checkout_flow`: Validates cart lifecycle and tender calculation.
7. `test_07_flask_admin_endpoints`: Tests admin inventory management and stock updates.
8. `test_08_customer_registration_and_validation`: Tests registration, validation, and email uniqueness.
9. `test_09_customer_login_session_checkout_flow`: Tests customer auth, order history, and logout.
10. `test_10_staff_authentication_and_hashing`: Tests password hashing and staff login verification.
11. `test_11_role_based_access_control`: Verifies RBAC guards, unauthenticated redirects, and API 403 blocks.
12. `test_12_persistent_shopping_cart`: Verifies SQLite persistent cart storage, guest-to-customer login merge, and cross-session restoration.
13. `test_13_complete_product_crud`: Full CRUD lifecycle testing (Create with validation, Read single/all, Update price/stock/rename, Delete with cart cleanup, RBAC enforcement).
14. `test_14_transaction_safe_inventory_and_atomic_checkout`: Verifies ACID atomic stock reservations, overselling prevention, rollback safety, and atomic checkout.

---

## 📄 License
This project is open-source and available for educational and commercial store management use.
