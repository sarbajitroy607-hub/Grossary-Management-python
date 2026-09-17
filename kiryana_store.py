import tkinter as tk
root = tk.Tk()
from tkinter import messagebox
# Lists to store cart items, quantities, and other related data
cart=[]
quantit=[]
new_stock=[]
newitem=[]
newq=[]
newp = []

# Dictionary to store items and their stock quantities

stock={
    "rice": 10,
    "wheat": 10, 
    "flour": 10,
    "oil": 10,
    "daal": 10,
    "soap": 10,
    "surf": 10,
}

# Dictionary to store item prices

prices={
    "rice": 50.0,
    "wheat": 40.0, 
    "flour": 30.0,
    "oil": 100.0,
    "daal": 60.0,
    "soap": 20.0,
    "surf": 25.0,
}   

# Function to display available grocery items

def items():
    root1 = tk.Tk()
    root1.title('Items')

    head = tk.Label(root1, text="Grocery Items", font=("times new roman", 30))
    head.pack(pady=(15))
    
    for item, qty in stock.items():
        item_info = f"  {item.capitalize()}:  price: {prices[item]}, stock: {qty}"
        head = tk.Label(root1, text=item_info, font=("arial", 15))
        head.pack(pady=(10), anchor='w')

# Function to view items in the cart

def veiw_cart():
    import tkinter as tk
    root6 = tk.Tk()
    root6.geometry('400x400')
    
    head=tk.Label(root6,text=('Your Cart'),font=("times new roman",25))
    head.pack(pady=(8))
    if not cart:
        empty=tk.Label(root6, text="Your cart is empty... :(", font=("arial", 15))
        empty.pack(pady=100)
    for i in range(len(cart)):
        head=tk.Label(root6,text=(f'Item: {cart[i]}    |    Quantity: {quantit[i]}'),font=("arial",20))
        head.pack(pady=(10), anchor='w')

# Function to add items to the cart

def add_items():
    def add():
        item = entry1.get().lower()
        quantity = entry2.get()
        try:
            qunt = int(quantity)
        except ValueError:
            messagebox.showerror('Error', 'Please enter a valid quantity')
            return

        if item in stock:
            if 0 <= qunt <= stock[item]:
                cart.append(item)
                quantit.append(qunt)
                stock[item] -= qunt
                messagebox.showinfo("Success", "Item added to your cart")
            else:
                messagebox.showerror("Error", "Not enough stock of this item")
        else:
            messagebox.showerror("Error", "This item is not available")
        root5.destroy()

    root5 = tk.Tk()
    root5.geometry('400x400')
    
    head = tk.Label(root5, text='Add Items', font=("times new roman", 25))
    head.pack(pady=(8))
    
    tk.Label(root5, text='Enter the name of item you want', font=("arial", 15)).pack(pady=3, anchor='w')
    entry1 = tk.Entry(root5, width=50, font='arial, 15')
    entry1.pack(padx=5, ipady='3', pady='10')
    
    tk.Label(root5, text='Enter the quantity of your item', font=("arial", 15)).pack(pady=3, anchor='w')
    entry2 = tk.Entry(root5, width=50, font='arial, 15')
    entry2.pack(padx=5, ipady='3', pady='10')
    
    button = tk.Button(root5, text="Add", width='15', height='2', font=('arial', 14), bg='grey', command=add)
    button.pack(pady='10')

# Function to remove items from the cart

def remove_item():
    def remove():
        item= entry1.get().lower()
        quantity=entry2.get().lower()
        try:
            qunt =int(quantity)
        except ValueError:
            messagebox.showerror('error','please enter a valid quantity')

        if item in cart:
            index = cart.index(item)
            if quantit[index] >= qunt:
                quantit[index] -= qunt
                stock[item] += qunt

                if quantit[index]==0:
                    cart.pop(index)
                messagebox.showinfo('successful','item removed from your cart')
            else:
                messagebox.showerror('error', 'not enough quantity of this titem to remove')
        else:
            messagebox.showerror('error','this item is not available in your cart')
        root7.destroy()
    
    
    import tkinter as tk
    root7 = tk.Tk()
    root7.geometry('400x400')
    
    head=tk.Label(root7,text=('Remove Items'),font=("times new roman",25))
    head.pack(pady=(8))
    
    head=tk.Label(root7,text=('Enter the name of item you want to remove'),font=("arial",15))
    head.pack(pady=(3),anchor='w')
    
    entry1 = tk.Entry(root7, width=50,font='arial, 15' )
    entry1.pack(padx=5,ipady='3',pady='10')
    
    head=tk.Label(root7,text=('Enter the quantity of your item to be removed'),font=("arial",15))
    head.pack(pady=(3),anchor='w')
    
    entry2 = tk.Entry(root7, width=50,font='arial, 15' )
    entry2.pack(padx=5,ipady='3',pady='10')
    
    button = tk.Button(root7, text="Remove",width='15',height='2',font=('arial',14),bg='grey',command=remove)
    button.pack(pady='10')

# Function to check out and finalize the purchase

def check_out():
    if not cart:
        messagebox.showinfo('Checkout', 'Your cart is empty.')
        return
    
    def check():
        messagebox.showinfo('Purchased', 'Thanks for Shopping :)')
        cart.clear()
        quantit.clear()
        root8.destroy()

    root8 = tk.Tk()
    head = tk.Label(root8, text="Check Out", font=("times new roman", 30))
    head.pack(pady=(15))

    total_cost = 0
    for i in range(len(cart)):
        item = cart[i]
        cost = prices[item] * quantit[i]
        total_cost += cost
        
        item_info = f'Item: {item} | Quantity: {quantit[i]} | Price: ${prices[item]} | Total: ${cost}'
        tk.Label(root8, text=item_info, font=("arial", 15)).pack(pady=(10), anchor='w')

    tk.Label(root8, text=f'Total Amount: ${total_cost}', font=("arial", 15)).pack(pady=3, anchor='w')
    button4 = tk.Button(root8, text="Check Out!!", width=15, height=2, font=('arial', 15), bg='grey', command=check)
    button4.pack(padx=10, pady=10)

# Function to display the user menu

def second():
    root.destroy()
    
    import tkinter as tk
    root2 = tk.Tk()
    root2.geometry("700x600")
    root2.title("Kiryana Store")
    
    head=tk.Label(root2,text=("User menu"),font=("times new roman",30))
    head.pack(pady=(15))
    
    button4= tk.Button(root2,text="Show Items",width=15,height=2,font=('arial',15),bg='grey',command=items)
    button4.pack(padx= 10, pady=10, anchor='w')
    
    button4= tk.Button(root2,text="Add Items",width=15,height=2,font=('arial',15),bg='grey',command=add_items)
    button4.pack(padx= 10, pady=10, anchor='w')
    
    button5= tk.Button(root2,text="Remove Item",width=15,height=2,font=('arial',15),bg='grey',command=remove_item)
    button5.pack(padx= 10, pady=10, anchor='w')
    
    button6= tk.Button(root2,text="View Cart",width=15,height=2,font=('arial',15),bg='grey',command=veiw_cart)
    button6.pack(padx= 10, pady=10, anchor='w')
    
    button7= tk.Button(root2,text="Check Out",width=15,height=2,font=('arial',15),bg='grey',command=check_out)
    button7.pack(padx= 10, pady=10, anchor='w')

# Function to start the program by accepting user name and password
def admin_login():
    root.destroy()
    import tkinter as tk
    root3 = tk.Tk()
    
    def login():
        email=admin.get()
        password= paas.get()
        if email== 'admin@gmail.com' and password == '123456':
            root3.destroy()
            
            import tkinter as tk
            root4 = tk.Tk()
            root4.geometry('500x600')
            root4.title('kiryana store')
            
            head=tk.Label(root4,text=("Welcome Admin"),font=("times new roman",30))
            head.pack(pady=(15))
            
            button4= tk.Button(root4,text="Show Items",width=15,height=2,font=('arial',15),bg='grey',command=items)
            button4.pack(padx= 10, pady=10, anchor='w')
    
            button4= tk.Button(root4,text="Change Stock",width=15,height=2,font=('arial',15),bg='grey',command=change_stock)
            button4.pack(padx= 10, pady=10, anchor='w')
    
            button5= tk.Button(root4,text="Add Item",width=15,height=2,font=('arial',15),bg='grey',command=ad_item)
            button5.pack(padx= 10, pady=10, anchor='w')
            
        else:
            messagebox.showerror('ohh!', 'worng ID or password')
    
    root3.geometry(("500x600"))
    root3.title("kiryana store") 
    root3.configure(background='lightgrey')

    lable = tk.Label(root3,bg='light grey', text=("Admin Login"), font=('times new roman', 30))
    lable.pack(padx=(20), pady=(20))

    label = tk.Label(root3, bg='light grey', text=("Enter ID"), font=('arial', 15))
    label.pack(padx=20, pady=15)

    admin = tk.Entry(root3,width=(30) ,font=('arial', 14))
    admin.pack(ipady=3)

    lab = tk.Label(root3, bg='light grey', text=("Enter Password"), font=('arial', 15))
    lab.pack(padx=20, pady=15)

    paas = tk.Entry(root3, width=(30), font=('arial', 14),show="*")
    paas.pack(ipady=3)

    button = tk.Button(root3, text='Login!',width=(10),font=('arial', 15),command=login)
    button.pack(pady=10)
    root.geometry("600x400")
# Function for admin to change the stock (quantity) of item in store
def change_stock():
    def change():
        item = entry1.get().lower()
        new_quantity = entry2.get()
    
        if item in stock:
            try:
                quan =int(new_quantity)
                messagebox.showinfo('succcess','stock updated')
                stock[item] = quan
            except ValueError:
                root9.destroy()
                messagebox.showerror('error','please enter a valid quantity')   
        else:
            messagebox.showerror('error','this item not not avalible in store')
            root9.destroy()        
    
    import tkinter as tk
    root9 = tk.Tk()
    root9.geometry('400x400')
    
    head=tk.Label(root9,text=('Add Stock'),font=("times new roman",25))
    head.pack(pady=(8))
    
    head=tk.Label(root9,text=('Enter the name of item to change stock'),font=("arial",15))
    head.pack(pady=(3),anchor='w')
    
    entry1 = tk.Entry(root9, width=50,font='arial, 15' )
    entry1.pack(padx=5,ipady='3',pady='10')
    
    head=tk.Label(root9,text=('Enter the new stock'),font=("arial",15))
    head.pack(pady=(3),anchor='w')
    
    entry2 = tk.Entry(root9, width=50,font='arial, 15' )
    entry2.pack(padx=5,ipady='3',pady='10')
    
    button = tk.Button(root9, text="Commit Changes!",width='15',height='2',font=('arial',14),bg='grey',command=change)
    button.pack(pady='10')

# Funtion for admin to add an item, set it's stock and it's price in store

def ad_item():
    def ad():
        item = entry1.get().lower()
        new_quantity = entry2.get()
        new_price = entry3.get()
        newitem.append(item)
        try:
            quan =int(new_quantity)
            newq.append(quan)
            stock[item] = quan
            money = float(new_price)
            newp.append(money)
            prices[item]= money
            messagebox.showinfo('sucsessful','item add to store')
        except ValueError:
            root10.destroy()
            messagebox.showerror('error','please enter a valid quantity or quantity')   
        
        root10.destroy()
    
    import tkinter as tk
    root10 = tk.Tk()
    root10.geometry('400x400')
    
    head=tk.Label(root10,text=('Add New Item'),font=("times new roman",25))
    head.pack(pady=(8))
    
    head=tk.Label(root10,text=('Enter the name of item'),font=("arial",15))
    head.pack(pady=(3),anchor='w')
    
    entry1 = tk.Entry(root10, width=50,font='arial, 15' )
    entry1.pack(padx=5,ipady='3',pady='10')
    
    head=tk.Label(root10,text=('Enter the stock'),font=("arial",15))
    head.pack(pady=(3),anchor='w')
    
    entry2 = tk.Entry(root10, width=50,font='arial, 15' )
    entry2.pack(padx=5,ipady='3',pady='10')
    
    head=tk.Label(root10,text=('Enter the price of item '),font=("arial",15))
    head.pack(pady=(3),anchor='w')
    
    entry3 = tk.Entry(root10, width=50,font='arial, 15' )
    entry3.pack(padx=5,ipady='3',pady='10')

    button = tk.Button(root10, text="Add Item!",width='15',height='2',font=('arial',14),bg='grey',command=ad)
    button.pack(pady='10')
# main window
root.title('kiryana store')

label2=tk.Label(root, text=("____Welcome To Kiryana store!____"), font=('times new roman',30 ))
label2.pack(pady=(15))

label3=tk.Label(root, text=("Continue as:-"), font=('arial',20))
label3.pack(pady=(40))

button2=tk.Button(root, bg="grey", text=("Admin"),width=(12), height='2',font=("arial", 19),command=admin_login)
button2.pack(pady=15)

button3=tk.Button(root, bg="grey",text=("User"),width=(12), height='2',font=("arial", 19),command=second)
button3.pack(pady=15)
    
root.mainloop()