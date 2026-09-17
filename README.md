youtube channel : (https://www.youtube.com/@syntax_cypher)
# Kiryana Store Management System

This project is a simple **Grocery Store Management System** built with Python's `tkinter` library. It simulates an online grocery store where users can view items, add items to a cart, remove items, and check out. The system also includes basic user authentication and administrative features for stock management.

## Features

1. **User Login**: 
   - Basic login system to authenticate users with a username and password (placeholder).
   
2. **Main Menu**:
   - After logging in, users can:
     - View available grocery items, including their price and stock.
     - Add items to their cart.
     - Remove items from their cart.
     - View the current items in their cart.
     - Proceed to checkout.

3. **Stock Management**:
   - The system manages inventory for each grocery item, ensuring the stock is updated when items are added or removed from the cart.

4. **Error Handling**:
   - Ensures that the user enters valid quantities.
   - Provides feedback when trying to add an unavailable item or when there’s insufficient stock.

5. **Checkout**:
   - Calculates the total cost of the items in the cart.
   - Clears the cart upon successful checkout.

## How to Run

1. Ensure you have **Python** installed on your system. If not, download and install it from the [official Python website](https://www.python.org/downloads/).

2. Install the `tkinter` library if you don't already have it installed. You can typically install it with:

    ```bash
    sudo apt-get install python3-tk   # On Ubuntu/Debian
    ```

    On other systems, `tkinter` should come pre-installed with Python.

3. Clone or download this repository.

4. Open the terminal/command prompt in the project directory and run the following command to start the program:

    ```bash
    python grocery_store.py
    ```

5. The login window will appear. Enter any username and password to proceed to the main menu.

## Files

- `grocery_store.py`: Main Python script that runs the application and handles the graphical user interface.
- `README.md`: This file, providing an overview of the project.

## Dependencies

- `tkinter`: Python library for creating graphical user interfaces (included with Python).
  
## Future Enhancements

- Implement a real user authentication system with a database for storing user data.
- Improve the admin functionality to allow for more detailed item management.
- Add more detailed purchase history and receipt generation.
- Enhance the design and usability of the graphical user interface.

## License

This project is open-source and can be modified or distributed as per your needs.

---

Enjoy using this basic grocery store system for learning purposes!
