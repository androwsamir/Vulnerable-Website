from flask import Flask, request, render_template, abort, flash, redirect, url_for, session, jsonify, render_template_string
import db
import utils
from werkzeug.utils import secure_filename
import json
import os
import requests
import validators

app = Flask(__name__)
app.secret_key = "123456" 
connection = db.connect_to_database()

@app.route('/')
def home():
    specific_books = request.args.get('specific_books')
    user_input = request.args.get('user_input')

    if specific_books:
        try:
            print('==============================')
            print(specific_books)
            print('==============================')
            specific_books = json.loads(specific_books)
        except json.JSONDecodeError:
            specific_books = []
    else:
        specific_books = []
    
    all_books = specific_books if specific_books else db.get_all_books(connection)
    card_items = []
    if 'user_id' in session:
        card_id = session['card_id']
        card_books_id = db.get_books_in_card(connection, card_id)
        
        for book_id in card_books_id:
            card_items.append(db.get_book_by_id(connection, book_id))

    if user_input:
        user_input = render_template_string(user_input)

    return render_template('home.html', books=all_books, card_items=card_items, user_input=user_input)
    
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
    
        user = db.check_user_existing(connection, username, utils.hash_password(password))

        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']

            if user['picture']:
                session['user_picture'] = user['picture']
            session['card_id'] = db.get_user_card(connection, session['user_id'])
            return redirect(url_for('home'))
        else:
            admin = db.check_admin_existing(connection, username, utils.hash_password(password))
            if admin:
                session['admin_id'] = admin['id']
                session['admin_username'] = admin['username']
                return redirect(url_for('home'))
            flash("Invalid username or password", "danger")
            return render_template('login.html')
    return render_template('login.html')

@app.route('/admin')
def admin_page():
    users = db.get_all_users(connection)

    all_books = db.get_all_books(connection)

    comments = db.get_all_comments(connection)
    print(comments)

    return render_template('admin_profile.html', users=users, books=all_books, comments=comments)

@app.route('/delete-book', methods=['POST'])
def delete_book():
    
    book_id = request.form.get('book_id')
    db.delete_book(connection, book_id)

    return redirect(url_for('admin_page'))

@app.route('/add-book', methods=['POST'])
def add_book():
    # if 'admin_id' in session:
    book_name = request.form['name']
    book_description = request.form['description']
    book_image = request.files['image']
    book_price = request.form['price']
    book_stock = request.form['stock']

    print(book_image)

    if book_image:
        filename = secure_filename(book_image.filename)
        image_path = os.path.join('booksPictures/', filename)
        book_image.save('./static/images/'+image_path)
    else:
        image_path = None

    db.add_book(connection, book_name, book_description, image_path, book_price, book_stock)

    return redirect(url_for('admin_page'))

@app.route('/delete-user', methods=['POST'])
def delete_user():
    user_id = request.form.get('user_id')
    db.delete_user(connection, user_id)

    return redirect(url_for('admin_page'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm-password']

        if not utils.is_strong_password(password):
            flash('password_error|Sorry, You Entered a Weak Password. Please Choose a Stronger One.', 'danger')
            return redirect(url_for('register'))

        if password != confirm_password:
            flash('confirm_password_error|Passwords do not match.', 'danger')
            return redirect(url_for('register'))

        user = db.check_user_existing(connection, username, password)
        email_exist = db.get_user_by_email(connection, email)
        if user:
            flash('username_error|Username already exists. Please choose a different username.', 'danger')
            return redirect(url_for('register'))
        else:
            if email_exist:
                flash('email_error|email already exists. Please choose a different email.', 'danger')
                return redirect(url_for('register'))
            hashed_password = utils.hash_password(password)
            db.add_user(connection, username, email, hashed_password)
            return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/profile/<id>')
def user_profile(id):
    if 'user_id' in session:
        user_data = db.get_user_by_id(connection, id)
        card_id = session['card_id']
        card_books_id = db.get_books_in_card(connection, card_id)
        card_items = []
        book_dict = {}
        for book_id in card_books_id:
            book_dict = db.get_book_by_id(connection, book_id)
            quantity = db.get_quantity_of_books(connection, card_id, book_id)
            book_dict['quantity'] = quantity
            book_dict['status'] = db.is_book_sold(connection, card_id, book_id)
            book_dict['price'] = db.get_price_of_book(connection, book_id)
            card_items.append(book_dict)

        total_price = sum(item['quantity'] * item['price'] for item in card_items if item['status'])  

        return render_template('profile.html', user=user_data, card_items=card_items, total_price=total_price)
    return redirect(url_for('home'))

@app.route('/buy-book/<int:book_id>', methods=['POST'])
def buy_book(book_id):
    user_id = session['user_id']
    card_id = session['card_id']
    request_data = request.get_json()
    quantity_purchased = request_data.get('quantity', 1)

    if db.check_balance(connection, user_id, card_id, book_id) and db.check_quantity(connection, book_id, quantity_purchased):

        print('=============================')
        db.buy_book(connection, card_id, book_id, quantity_purchased)
        db.check_balancwe_and_update(connection, user_id, card_id)

        # After successful purchase, update the status and total price
        total_price = db.calculate_total_price(connection, card_id)
        return jsonify({"success": True, "total_price": total_price}), 200
    else:
        if not db.check_balance(connection, user_id, card_id, book_id):
            return jsonify({"error": "Sorry, You don't have enough money."}), 400
        elif not db.check_quantity(connection, book_id, quantity_purchased):
            return jsonify({"error": "Sorry, This quantity is out of stock."}), 400

@app.route('/increase-balance')
def increase_balance():
    card_id = session['card_id']
    db.increase_balance(connection, card_id)
    return 'Done'

@app.route('/update_quantity/<book_id>', methods=['POST'])
def update_quantity(book_id):
    if 'user_id' in session:
        card_id = session['card_id']
        db.add_book_to_user_card(connection, card_id, book_id)
        return '', 204  # No Content response
    return '', 401  # Unauthorized response

@app.route('/delete_from_cart/<book_id>', methods=['DELETE'])
def delete_from_cart(book_id):
    # Logic to delete the item from the user's cart
    # Assuming you have a function `remove_from_cart(user_id, book_id)`
    if 'user_id' in session:
        card_id = session['card_id']
        db.delete_book_from_user_card(connection, card_id, book_id)

        # Recalculate total price after deletion
        total_price = db.calculate_total_price(connection, card_id)
        return jsonify({"success": True, "total_price": total_price}), 200
    return jsonify({"error": "Unauthorized request"}), 401

@app.route('/update-profile', methods=['GET', 'POST'])
def update_profile():
    if request.method == 'POST':
        user_id = session['user_id']
        username = request.form['username']
        email = request.form['email']
        change_password = request.form.get('change_password')
        if change_password:
            password = request.form['password']
            confirm_password = request.form['confirm_password']

            if password != confirm_password:
                flash('password_error|confirm password not like password', 'danger')
                return redirect(url_for('user_profile', id=user_id))
            
        picture = request.files['profile_picture']
        if change_password and not picture:
            user_data = {
                'id': user_id,
                'username': username,
                'email': email,
                'password': password,
                'picture': ''
            }

        if picture and not change_password:
            filename = picture.filename
            picture.save('./static/images/'+filename)
            password = db.get_user_password(connection, user_id)

            if not validators.allowed_file(picture):
                flash("picture_error|Invalid File is Uploaded", "danger")
                return redirect(url_for('user_profile', id=user_id))

            user_data = {
                'id': user_id,
                'username': username,
                'email': email,
                'password': password,
                'picture': filename if filename else None
            }
            session['user_picture'] = filename

        if picture and change_password:
            filename = picture.filename
            picture.save('./static/images/'+filename)
            password = db.get_user_password(connection, user_id)

            if not validators.allowed_file(picture):
                flash("picture_error|Invalid File is Uploaded", "danger")
                return redirect(url_for('user_profile', id=user_id))

            user_data = {
                'id': user_id,
                'username': username,
                'email': email,
                'password': password,
                'picture': filename if filename else None
            }
            session['user_picture'] = filename

        db.update_user(connection, user_data)

        # return redirect(url_for('home'))

    return redirect(url_for('user_profile', id=user_id))

@app.route('/add-to-cart/<id>')
def add_to_cart(id):
    book_id = id
    user_id = session['user_id']

    if not db.add_book_to_user_card(connection, user_id, book_id):
        flash('Sorry, Out of the stock', 'danger')

    return redirect(url_for('bookPage', id=book_id))

@app.route('/logout')
def logout():
    if 'user_id' in session:
        session.pop('username', None)
        session.pop('user_id', None)
        session.pop('card_id', None)
        session.pop('user_picture', None)
    elif 'admin_id' in session:
        session.pop('admin_id', None)
        session.pop('admin_username', None)
    return redirect(url_for('home'))

@app.route('/add-comment/<book_id>', methods=['POST'])
def add_comment(book_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    comment_text = request.form.get('comment_text')

    db.add_comment(connection, book_id, user_id, comment_text)

    return redirect(url_for('bookPage', id=book_id))

@app.route('/admin/edit_comment/<int:comment_id>', methods=['POST'])
def edit_comment(comment_id):
    new_text = request.form['new_text']
    db.edit_comment(connection, comment_id, new_text)  # This is a placeholder for your actual DB function
    return redirect(url_for('admin_page'))

@app.route('/admin/delete_comment/<int:comment_id>', methods=['POST'])
def delete_comment(comment_id):
    db.delete_comment(connection, comment_id)  # This is a placeholder for your actual DB function
    return redirect(url_for('admin_page'))

@app.route('/book-details/<id>')
def bookPage(id):

    is_logged_in = 'user_id' in session
    card_items = []
    if 'user_id' in session:
        card_id = session['card_id']
        card_books_id = db.get_books_in_card(connection, card_id)
        
        for book_id in card_books_id:
            card_items.append(db.get_book_by_id(connection, book_id))

    book = db.get_book_by_id(connection, id)
    comments = db.get_comments_for_book(connection, id)
    comments_users = [db.get_user_by_id(connection, comment['user_id']) for comment in comments]

    # Zip comments and users
    comments_with_users = list(zip(comments, comments_users))

    if book is None:
        abort(404)  # Book not found

    return render_template('book_details.html', book=book, is_logged_in=is_logged_in, card_items=card_items, comments_with_users=comments_with_users)

@app.route('/show-stock', methods=['POST'])
def show_stock():

    data = request.get_json()
    stock_request_url = data.get('stockAPI')

    try:
        response = requests.get(stock_request_url)
        if response.ok:
            stock_response = response.text

            return jsonify({'success': True, 'stock': stock_response})
        else:
            return jsonify({'success': False, 'message': 'Failed to fetch stock information'}), 500
    except requests.RequestException as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/stock/<book_id>', methods=['GET'])
def get_stock(book_id):
    
    book = db.get_book_by_id(connection, book_id)

    if book is None:
        abort(404)  

    return str(book['stock'])

@app.route('/search')
def search_for_book():
    query = request.args.get('query')
    specific_books = db.get_books_by_name(connection, query) if query else None
    specific_books_json = json.dumps(specific_books)
    return redirect(url_for('home', specific_books=specific_books_json, user_input=query))

@app.route('/about-us')
def about_us():
    return render_template('about_us.html')

@app.route('/contact-us')
def contact_us():
    return render_template('contact_us.html')

@app.route('/submit-contact')
def submit_contact():
    return 'Done'

if __name__ =='__main__':
    db.init_db(connection)
    db.init_admins_table(connection)
    db.init_books_table(connection)
    db.init_cards_table(connection)
    db.init_comments_table(connection)
    db.init_cards_books_table(connection)
    app.run(host='0.0.0.0', debug=True, port=8888)