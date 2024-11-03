import utils

def connect_to_database(name='database.db'):
    import sqlite3
    return sqlite3.connect(name, check_same_thread=False)

# Function to initialize the database
def init_db(connection):
    cursor = connection.cursor()

    # Create users table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            picture TEXT
        )
    ''')

    connection.commit()

def init_admins_table(connection):
    cursor = connection.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')

    # Add the admin account if it doesn't exist
    cursor.execute('SELECT * FROM admins WHERE username=?', ('admin',))
    existing_admin = cursor.fetchone()
    if not existing_admin:
        admin_password = 'admin1'  # Replace 'admin_password' with the desired password
        admin_password = utils.hash_password(admin_password)
        cursor.execute('INSERT INTO admins (username, password) VALUES (?, ?)', ('admin', admin_password))

    connection.commit()

def init_books_table(connection):

    cursor = connection.cursor()

    # Create books table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            description TEXT NOT NULL,
            image TEXT NOT NULL,
            price REAL NOT NULL,
            stock REAL NOT NULL
        )
    ''')
    
    # Add books if they don't exist
    books_data = [
        ('A Hands-on Introduction To Hacking', 'Practical insights and techniques for beginners to start exploring the world of ethical hacking and cybersecurity.', 'booksPictures/AHands-onIntroductionToHacking.png', 1599.99, 5),
        ('Attacking Network Protocols', 'In-depth guide to understanding and exploiting vulnerabilities in network protocols for cybersecurity professionals.', 'booksPictures/AttackingNetworkProtocols.png', 1299.99, 1000),
        ('Black Hat Python', 'Using Python to craft and implement offensive security tools and techniques for penetration testing and cybersecurity.', 'booksPictures/BlackHatPython.png', 199.99, 1000),
        ('Linux Command Line and Shell Scripting', 'A comprehensive guide to mastering the Linux command line and automating tasks with shell scripting.', 'booksPictures/LinuxCommandLineAndShellScripting.png', 679.99, 1000),
        ('Mastering Modern Web Penteration Testing', 'A comprehensive guide that equips readers with advanced techniques and tools for identifying and exploiting vulnerabilities in web applications.', 'booksPictures/MasteringModernWebPentesting.png', 149.99, 1000),
        ('Real World Bug Hunting', 'A practical guide to discovering and exploiting security vulnerabilities in real-world software applications.', 'booksPictures/RealWorldBugHunting.png', 1179.99, 1000),
        ('The Art of Exploitation', 'A comprehensive guide to understanding and utilizing security vulnerabilities through hands-on exploitation techniques and practical examples.', 'booksPictures/TheArtOfExploitation.png', 549.99, 1000),
        ('Web Security for Developers', 'A comprehensive guide for building secure web applications, focusing on practical techniques to protect against common vulnerabilities and threats.', 'booksPictures/WebSecurityForDevelopers.png', 1579.99, 1000),
        
    ]

    for book_data in books_data:
        name = book_data[0]
        cursor.execute('SELECT * FROM books WHERE name=?', (name,))
        existing_book = cursor.fetchone()
        if not existing_book:
            cursor.execute('INSERT INTO books (name, description, image, price, stock) VALUES (?, ?, ?, ?, ?)', book_data)

    connection.commit()

def init_comments_table(connection):
    cursor = connection.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (book_id) REFERENCES books (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    connection.commit()

def init_cards_table(connection):
    cursor = connection.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            balance REAL DEFAULT 1000.0,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    connection.commit()

def init_cards_books_table(connection):
    cursor = connection.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS card_books (
            card_id INTEGER NOT NULL,
            book_id INTEGER NOT NULL,
            quantity INTEGER DEFAULT 1,
            status TEXT NOT NULL DEFAULT 'Not Sold',
            PRIMARY KEY (card_id, book_id),
            FOREIGN KEY (card_id) REFERENCES cards (id) ON DELETE CASCADE,
            FOREIGN KEY (book_id) REFERENCES books (id) ON DELETE CASCADE
        )
    ''')

    connection.commit()

def check_quantity(connection, book_id, quantity_purchased):
    cursor = connection.cursor()
    # Check current stock for the book
    cursor.execute("SELECT stock FROM books WHERE id=?", (book_id,))
    result = cursor.fetchone()
    if result:
        stock = result[0]
        if stock >= quantity_purchased:
            return True
    return False
    

def check_balance(connection, user_id, card_id, book_id):
    cursor = connection.cursor()

    # Check current balance for the user's card
    cursor.execute("SELECT balance FROM cards WHERE id=? AND user_id=?", (card_id, user_id))
    result1 = cursor.fetchone()

    cursor.execute("SELECT quantity FROM card_books WHERE card_id=? AND book_id=?", (card_id, book_id,))
    result2 = cursor.fetchone()

    cursor.execute("SELECT price FROM books WHERE id=?", (book_id,))
    result3=cursor.fetchone()

    if result1 and result2 and result3:
        balance = result1[0]
        quantity = result2[0]
        book_cost = result3[0]
        total_cost = calculate_total_price(connection, card_id)

        if balance >= (total_cost+(quantity*book_cost)):
            return True
    
    return False

def check_balance_and_update(connection, user_id, card_id):
    cursor = connection.cursor()

    # Check current balance for the user's card
    cursor.execute("SELECT balance FROM cards WHERE id=? AND user_id=?", (card_id, user_id))
    result1 = cursor.fetchone()

    if result1:
        balance = result1[0]
        total_cost = calculate_total_price(connection, card_id)

        # Check if the user has enough balance
        if balance >= total_cost:
            # Update the user's balance
            new_balance = balance - total_cost
            cursor.execute("UPDATE cards SET balance=? WHERE id=? AND user_id=?", (new_balance, card_id, user_id))
            connection.commit()
            return True

    return False

def calculate_total_price(connection, card_id):
    cursor = connection.cursor()
    
    # Query to get the quantity and price of each book in the cart that is not sold
    cursor.execute('''
        SELECT cb.quantity, b.price 
        FROM card_books cb
        JOIN books b ON cb.book_id = b.id
        WHERE cb.card_id = ? AND cb.status = 'Sold'
    ''', (card_id,))
    
    items = cursor.fetchall()
    
    # Calculate the total price
    total_price = sum(quantity * price for quantity, price in items)
    
    return total_price

def increase_balance(connection, card_id):
    cursor = connection.cursor()
    cursor.execute('''
            UPDATE cards
            SET balance = balance + 2000
            WHERE id = ?
        ''', (card_id,))
    # Commit the changes
    connection.commit()

def buy_book(connection, card_id, book_id, quantity_purchased):
    cursor = connection.cursor()
    # Check current stock for the book
    cursor.execute("SELECT stock FROM books WHERE id=?", (book_id,))
    result = cursor.fetchone()
    if result:
        stock = result[0]
        if stock >= quantity_purchased:
            # Update stock and mark items in card as sold
            new_stock = stock - quantity_purchased
            cursor.execute("UPDATE books SET stock=? WHERE id=?", (new_stock, book_id))

            cursor.execute("UPDATE card_books SET status='Sold' WHERE card_id=? AND book_id=?", (card_id, book_id))
            
            cursor.execute("UPDATE card_books SET quantity=? WHERE card_id=? AND book_id=?", (quantity_purchased, card_id, book_id))
            connection.commit()
            return True
        else:
            return False
    return False

def is_book_sold(connection, card_id, book_id):
    cursor = connection.cursor()
    
    # Query the status of the book in the card_books table
    cursor.execute("SELECT status FROM card_books WHERE card_id=? AND book_id=?", (card_id, book_id))
    result = cursor.fetchone()
    
    if result:
        status = result[0]
        return status == 'Sold'
    
    return False

def add_user(connection, username, email, password):
    cursor = connection.cursor()

    # Insert the new user into the users table
    cursor.execute('INSERT INTO users (username, email, password) VALUES (?, ?, ?)', (username, email, password))

    # Retrieve the id of the newly inserted user
    user_id = cursor.lastrowid

    # Insert a new card for the new user
    cursor.execute('INSERT INTO cards (user_id) VALUES (?)', (user_id,))

    # Commit the transaction
    connection.commit()

def add_book_to_user_card(connection, card_id, book_id, quantity=1):
    cursor = connection.cursor()
    
    if card_id:
        # Check if the book is already in the user's card
        cursor.execute('SELECT quantity FROM card_books WHERE card_id = ? AND book_id = ?', (card_id, book_id))
        result = cursor.fetchone()
        
        # Get the current stock of the book
        cursor.execute('SELECT stock FROM books WHERE id = ?', (book_id,))
        stock = cursor.fetchone()[0]
        
        if result:
            # If the book is already in the card, update the quantity
            current_quantity = result[0]
            new_quantity = current_quantity + quantity
            
            if new_quantity <= stock:
                cursor.execute('UPDATE card_books SET quantity = ? WHERE card_id = ? AND book_id = ?', (new_quantity, card_id, book_id))
                connection.commit()
                return True
            else:
                # Not enough stock
                return False
        else:
            # Add the book to the card with the specified quantity
            if quantity <= stock:
                cursor.execute('INSERT INTO card_books (card_id, book_id, quantity) VALUES (?, ?, ?)', (card_id, book_id, quantity))
                connection.commit()
                return True
            else:
                # Not enough stock
                return False
    else:
        # The user doesn't have a card
        return False

def add_comment(connection, book_id, user_id, text):
    cursor = connection.cursor()

    # SQL query to insert a new comment into the comments table
    cursor.execute('''
        INSERT INTO comments (book_id, user_id, text)
        VALUES (?, ?, ?)
    ''', (book_id, user_id, text))

    # Commit the transaction to save the comment in the database
    connection.commit()

    print("Comment added successfully.")

def get_comments_for_book(connection, book_id):
    cursor = connection.cursor()
    
    # Execute the query to get comments for the specific book_id
    cursor.execute('''
        SELECT id, book_id, user_id, text, timestamp
        FROM comments
        WHERE book_id = ?
    ''', (book_id,))
    
    # Fetch all results
    rows = cursor.fetchall()
    
    # Convert the results into a list of dictionaries
    comments = []
    for row in rows:
        comments.append({
            'id': row[0],
            'book_id': row[1],
            'user_id': row[2],
            'text': row[3],
            'timestamp': row[4]
        })
    
    return comments

def get_all_comments(connection):
    cursor = connection.cursor()

    cursor.execute('''
        SELECT c.id, c.book_id, c.user_id, c.text, c.timestamp, u.username
        FROM comments c
        JOIN users u ON c.user_id = u.id
        ORDER BY c.timestamp DESC
    ''')

    comments = cursor.fetchall()

    all_comments = []
    for comment in comments:
        # Create a dictionary for each comment and append it to the list
        comment_dict = {
            'id': comment[0],
            'book_id': comment[1],
            'user_id': comment[2],
            'text': comment[3],
            'timestamp': comment[4],
            'username': comment[5]  # Include the username of the commenter
        }
        all_comments.append(comment_dict)

    return all_comments

def delete_comment(connection, comment_id):
    cursor = connection.cursor()

    # Delete the specified comment
    cursor.execute('''
        DELETE FROM comments
        WHERE id = ?
    ''', (comment_id,))

    # Shift the IDs of the remaining comments
    cursor.execute('''
        UPDATE comments
        SET id = id - 1
        WHERE id > ?
    ''', (comment_id,))

    connection.commit()

    # If the ID is an AUTOINCREMENT field, you may also want to reset the AUTOINCREMENT counter.
    cursor.execute('VACUUM')  # This will rebuild the database to reset the AUTOINCREMENT counter

    connection.commit()

def edit_comment(connection, comment_id, new_text):
    cursor = connection.cursor()

    cursor.execute('''
        UPDATE comments
        SET text = ?, timestamp = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (new_text, comment_id))

    connection.commit()

def delete_book_from_user_card(connection, card_id, book_id):
    cursor = connection.cursor()

    cursor.execute('DELETE FROM card_books WHERE card_id = ? AND book_id = ?', (card_id, book_id))

    connection.commit()

def get_user_password(connection, user_id):
    cursor = connection.cursor()
    cursor.execute('SELECT password FROM users WHERE id = ?', (user_id,))
    password = cursor.fetchone()
    if password:
        return password[0]
    return None

def update_user(connection, user):
    cursor = connection.cursor()

    cursor.execute('UPDATE users SET username=?, email=?, password=?, picture=? WHERE id=?', (user['username'], user['email'], user['password'], user['picture'], user['id']))

    connection.commit()

def get_user_card(connection, user_id):
    cursor = connection.cursor()
    cursor.execute('SELECT id FROM cards WHERE user_id = ?', (user_id,))
    card = cursor.fetchone()
    if card:
        return card[0]
    return None

def get_books_in_card(connection, card_id):
    cursor = connection.cursor()
    cursor.execute('SELECT book_id FROM card_books WHERE card_id = ?', (card_id,))
    books = cursor.fetchall()
    return [book[0] for book in books]

def get_quantity_of_books(connection, card_id, book_id):
    cursor = connection.cursor()

    # Check if the book is in the user's card
    cursor.execute('SELECT quantity FROM card_books WHERE card_id = ? AND book_id = ?', (card_id, book_id))
    result = cursor.fetchone()
    
    if result:
        return result[0]
    return None

def get_price_of_book(connection, book_id):
    cursor = connection.cursor()

    # Check if the book is in the user's card
    cursor.execute('SELECT price FROM books WHERE id = ?', (book_id,))
    result = cursor.fetchone()
    
    if result:
        return result[0]
    return None

def check_admin_existing(connection, username, password):
    cursor = connection.cursor()

    query = f"SELECT * FROM admins WHERE username = '{username}' AND password = '{password}'"

    cursor.execute(query)
    admin = cursor.fetchone()

    if admin:
        # Return the user as a dictionary
        return {'id': admin[0], 'username': admin[1], 'password': admin[2]}
    else:
        return None

def get_all_users(connection):
    cursor = connection.cursor()
    
    # Execute the query to get all users
    cursor.execute('SELECT * FROM users')
    users = cursor.fetchall()

    user_list = []
    for user in users:
        user_dict = {
            'id': user[0],
            'username': user[1],
            'email': user[2],
            'password': user[3],
            'picture': user[4]
        }
        user_list.append(user_dict)
    
    return user_list if user_list else []

def delete_user(connection, user_id):
    cursor = connection.cursor()
    
    # Execute the query to delete the user
    cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
    
    # Commit the changes to the database
    connection.commit()
    
    # Check if the user was deleted
    if cursor.rowcount > 0:
        return True  # User deleted successfully
    else:
        return False  # User not found

def add_book(connection, name, description, image, price, stock):
    cursor = connection.cursor()
    
    # Check if the book already exists
    cursor.execute('SELECT * FROM books WHERE name = ?', (name,))
    existing_book = cursor.fetchone()
    
    if not existing_book:
        # Insert the new book into the books table
        cursor.execute('INSERT INTO books (name, description, image, price, stock) VALUES (?, ?, ?, ?, ?)', (name, description, image, price, stock))
        connection.commit()
        return True  # Book added successfully
    else:
        return False  # Book already exists

def delete_book(connection, book_id):
    cursor = connection.cursor()
    
    # Execute the query to delete the book
    cursor.execute('DELETE FROM books WHERE id = ?', (book_id,))
    
    # Shift the IDs of the remaining books
    cursor.execute('''
        UPDATE books
        SET id = id - 1
        WHERE id > ?
    ''', (book_id,))


    # Commit the changes to the database
    connection.commit()

    cursor.execute('VACUUM')

    connection.commit()
    
    # Check if the book was deleted
    if cursor.rowcount > 0:
        return True  # Book deleted successfully
    else:
        return False  # Book not found

def get_user_by_id(connection, id):
    cursor = connection.cursor()

    cursor.execute('SELECT * FROM users WHERE id=?', (id,))
    user = cursor.fetchone()

    if user:
        # Return the user as a dictionary
        return {'id': user[0], 'username': user[1], 'email': user[2], 'password': user[3], 'picture': user[4]}
    else:
        return None

# Function to get a user by username
def check_user_existing(connection, username, password):
    cursor = connection.cursor()

    query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"

    cursor.execute(query)
    user = cursor.fetchone()

    if user:
        # Return the user as a dictionary
        return {'id': user[0], 'username': user[1], 'email': user[2], 'password': user[3], 'picture': user[4]}
    else:
        return None
    
def get_user_by_email(connection, email):
    cursor = connection.cursor()

    cursor.execute('SELECT * FROM users WHERE email=?', (email,))
    user = cursor.fetchone()

    if user:
        # Return the user as a dictionary
        return {'id': user[0], 'username': user[1], 'email': user[2], 'password': user[3], 'picture': user[4]}
    else:
        return None

def get_book_by_id(connection, book_id):
    cursor = connection.cursor()

    cursor.execute('SELECT * FROM books WHERE id=?', (book_id,))
    book = cursor.fetchone()

    if book:
        # Create a dictionary for the book and return it
        book_dict = {
            'id': book[0],
            'name': book[1],
            'description': book[2],
            'image': book[3],
            'price': book[4],
            'stock': book[5]  # Add stock to the dictionary
        }
        return book_dict
    else:
        return None

def get_books_by_name(connection, book_name):
    cursor = connection.cursor()
    query = f"SELECT * FROM books WHERE LOWER(name) LIKE '%{book_name.lower()}%'"
    cursor.execute(query)
    books = cursor.fetchall()
    book_list = []
    for book in books:
        book_dict = {
            'id': book[0],
            'name': book[1],
            'description': book[2],
            'image': book[3],
            'price': book[4]
        }
        book_list.append(book_dict)
    return book_list if book_list else None

def get_all_books(connection):
    cursor = connection.cursor()

    cursor.execute('SELECT * FROM books')
    books = cursor.fetchall()

    all_books = []
    for book in books:
        # Create a dictionary for each book and append it to the list
        book_dict = {
            'id': book[0],
            'name': book[1],
            'description': book[2],
            'image': book[3],
            'price': book[4],
            'stock': book[5]  # Add stock to the dictionary
        }
        all_books.append(book_dict)

    return all_books


