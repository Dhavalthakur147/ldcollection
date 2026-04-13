import os
import re
from datetime import datetime
from contextlib import contextmanager
from functools import wraps
from pathlib import Path

import mysql.connector
from mysql.connector import pooling
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'ldcollection-secret-key-2024')

# MySQL Database Configuration
MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
MYSQL_USER = os.getenv('MYSQL_USER', 'root')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
MYSQL_DB = os.getenv('MYSQL_DB', 'ldcollection')
MYSQL_PORT = int(os.getenv('MYSQL_PORT', '3306'))
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')
PRODUCT_UPLOAD_DIR = Path(app.root_path) / 'static' / 'uploads' / 'products'
PROFILE_UPLOAD_DIR = Path(app.root_path) / 'static' / 'uploads' / 'profiles'
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}

_db_pool = pooling.MySQLConnectionPool(
    pool_name='ldcollection_pool',
    pool_size=5,
    host=MYSQL_HOST,
    user=MYSQL_USER,
    password=MYSQL_PASSWORD,
    database=MYSQL_DB,
    port=MYSQL_PORT,
    autocommit=False,
)


@contextmanager
def db_cursor(commit=False):
    conn = _db_pool.get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        yield cursor, conn
        if commit:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def fetch_one(query, params=None):
    with db_cursor() as (cursor, _):
        cursor.execute(query, params or ())
        return cursor.fetchone()


def fetch_all(query, params=None):
    with db_cursor() as (cursor, _):
        cursor.execute(query, params or ())
        return cursor.fetchall()


def execute(query, params=None):
    with db_cursor(commit=True) as (cursor, _):
        cursor.execute(query, params or ())


def execute_returning_id(query, params=None):
    with db_cursor(commit=True) as (cursor, _):
        cursor.execute(query, params or ())
        return cursor.lastrowid


@app.template_filter('inr')
def format_inr(value):
    try:
        amount = float(value)
    except (TypeError, ValueError):
        amount = 0.0

    is_negative = amount < 0
    amount = abs(amount)
    whole, fraction = f'{amount:.2f}'.split('.')

    if len(whole) > 3:
        last_three = whole[-3:]
        remaining = whole[:-3]
        groups = []
        while len(remaining) > 2:
            groups.insert(0, remaining[-2:])
            remaining = remaining[:-2]
        if remaining:
            groups.insert(0, remaining)
        whole = ','.join(groups + [last_three])

    prefix = '-Rs. ' if is_negative else 'Rs. '
    return f'{prefix}{whole}.{fraction}'


def allowed_image_file(filename):
    if not filename or '.' not in filename:
        return False
    extension = filename.rsplit('.', 1)[1].lower()
    return extension in ALLOWED_IMAGE_EXTENSIONS


def save_product_image(uploaded_file):
    if not uploaded_file or not uploaded_file.filename:
        return None
    if not allowed_image_file(uploaded_file.filename):
        raise ValueError('Invalid image format. Use png, jpg, jpeg, webp, or gif.')

    PRODUCT_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = secure_filename(uploaded_file.filename)
    timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S%f')
    final_name = f'{timestamp}_{safe_name}'
    destination = PRODUCT_UPLOAD_DIR / final_name
    uploaded_file.save(destination)
    return f'/static/uploads/products/{final_name}'


def save_profile_image(uploaded_file):
    if not uploaded_file or not uploaded_file.filename:
        return None
    if not allowed_image_file(uploaded_file.filename):
        raise ValueError('Invalid image format. Use png, jpg, jpeg, webp, or gif.')

    PROFILE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = secure_filename(uploaded_file.filename)
    timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S%f')
    final_name = f'{timestamp}_{safe_name}'
    destination = PROFILE_UPLOAD_DIR / final_name
    uploaded_file.save(destination)
    return f'/static/uploads/profiles/{final_name}'


def make_slug(value):
    base = (value or '').strip().lower()
    slug = re.sub(r'[^a-z0-9]+', '-', base).strip('-')
    return slug or 'category'

# ===================== ADMIN AUTH =====================


def is_admin_logged_in():
    return bool(session.get('is_admin'))


def admin_required(view_func):
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if not is_admin_logged_in():
            flash('Please log in as admin to continue.', 'error')
            return redirect(url_for('admin_login'))
        return view_func(*args, **kwargs)

    return wrapped_view


# ===================== USER AUTH =====================


def is_user_logged_in():
    return bool(session.get('is_user'))


def user_required(view_func):
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if not is_user_logged_in():
            flash('Please log in to continue.', 'error')
            return redirect(url_for('user_login'))
        return view_func(*args, **kwargs)

    return wrapped_view


# ===================== CART HELPERS =====================


def get_cart():
    return session.get('cart', {})


def save_cart(cart):
    session['cart'] = cart
    session.modified = True


def cart_item_count(cart):
    return sum(cart.values()) if cart else 0


def fetch_products_for_cart(cart):
    if not cart:
        return []
    product_ids = [int(pid) for pid in cart.keys()]
    placeholders = ','.join(['%s'] * len(product_ids))
    query = f'SELECT * FROM product WHERE id IN ({placeholders})'
    products = fetch_all(query, product_ids)
    product_map = {product['id']: product for product in products}

    items = []
    for product_id_str, quantity in cart.items():
        product_id = int(product_id_str)
        product = product_map.get(product_id)
        if product:
            items.append({
                'product': product,
                'quantity': quantity,
            })
    return items


def cart_total(cart_items):
    return sum(item['quantity'] * item['product']['price'] for item in cart_items)


# ===================== DATA SEED =====================


def ensure_tables():
    with db_cursor(commit=True) as (cursor, _):
        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS product (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                price DECIMAL(10, 2) NOT NULL,
                category VARCHAR(100),
                stock INT NOT NULL DEFAULT 0,
                image_url VARCHAR(500),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            '''
        )
        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS `order` (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NULL,
                order_number VARCHAR(50) NOT NULL,
                customer_name VARCHAR(255) NOT NULL,
                customer_email VARCHAR(255) NOT NULL,
                customer_phone VARCHAR(50),
                shipping_address TEXT,
                total_amount DECIMAL(10, 2) NOT NULL,
                status VARCHAR(50) NOT NULL DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            '''
        )
        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS order_item (
                id INT AUTO_INCREMENT PRIMARY KEY,
                order_id INT NOT NULL,
                product_id INT NOT NULL,
                quantity INT NOT NULL,
                price DECIMAL(10, 2) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT fk_order_item_order
                    FOREIGN KEY (order_id) REFERENCES `order`(id)
                    ON DELETE CASCADE,
                CONSTRAINT fk_order_item_product
                    FOREIGN KEY (product_id) REFERENCES product(id)
                    ON DELETE RESTRICT
            )
            '''
        )
        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS admin_user (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(100) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            '''
        )
        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS customer_user (
                id INT AUTO_INCREMENT PRIMARY KEY,
                full_name VARCHAR(255) NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                profile_image VARCHAR(500),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            '''
        )
        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS category (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(120) UNIQUE NOT NULL,
                slug VARCHAR(140) UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            '''
        )
        cursor.execute(
            '''
            SELECT COUNT(*) AS total
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = %s
              AND TABLE_NAME = 'order'
              AND COLUMN_NAME = 'user_id'
            ''',
            (MYSQL_DB,),
        )
        has_user_id = cursor.fetchone()
        if not has_user_id or has_user_id['total'] == 0:
            cursor.execute('ALTER TABLE `order` ADD COLUMN user_id INT NULL')
        cursor.execute(
            '''
            SELECT COUNT(*) AS total
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = %s
              AND TABLE_NAME = 'customer_user'
              AND COLUMN_NAME = 'profile_image'
            ''',
            (MYSQL_DB,),
        )
        has_profile_image = cursor.fetchone()
        if not has_profile_image or has_profile_image['total'] == 0:
            cursor.execute('ALTER TABLE customer_user ADD COLUMN profile_image VARCHAR(500)')


def ensure_sample_products():
    count_row = fetch_one('SELECT COUNT(*) AS total FROM product')
    if count_row and count_row['total'] > 0:
        return

    sample_products = [
        ('Elegant Black Dress', 'A sophisticated black dress perfect for any occasion', 49.99, 'Dresses', 20, 'https://via.placeholder.com/300x400?text=Black+Dress'),
        ('Classic White Shirt', 'Timeless white shirt for everyday wear', 29.99, 'Shirts', 30, 'https://via.placeholder.com/300x400?text=White+Shirt'),
        ('Blue Denim Jeans', 'Comfortable and stylish denim jeans', 59.99, 'Jeans', 25, 'https://via.placeholder.com/300x400?text=Jeans'),
        ('Summer Floral Dress', 'Colorful floral dress for summer', 45.99, 'Dresses', 15, 'https://via.placeholder.com/300x400?text=Floral+Dress'),
        ('Red Sweater', 'Cozy red sweater for cooler days', 39.99, 'Sweaters', 18, 'https://via.placeholder.com/300x400?text=Red+Sweater'),
        ('Black Leather Jacket', 'Classic black leather jacket', 129.99, 'Jackets', 10, 'https://via.placeholder.com/300x400?text=Jacket'),
        ('Grey Cargo Pants', 'Practical cargo pants with multiple pockets', 54.99, 'Pants', 22, 'https://via.placeholder.com/300x400?text=Cargo+Pants'),
        ('Pink Hoodie', 'Comfortable pink hoodie', 44.99, 'Hoodies', 20, 'https://via.placeholder.com/300x400?text=Pink+Hoodie'),
    ]

    with db_cursor(commit=True) as (cursor, _):
        cursor.executemany(
            'INSERT INTO product (name, description, price, category, stock, image_url) VALUES (%s, %s, %s, %s, %s, %s)',
            sample_products,
        )


def ensure_sample_categories():
    category_rows = fetch_all(
        '''
        SELECT DISTINCT category
        FROM product
        WHERE category IS NOT NULL AND category != ''
        '''
    )
    for row in category_rows:
        name = row['category'].strip()
        if not name:
            continue
        try:
            execute(
                'INSERT INTO category (name, slug) VALUES (%s, %s)',
                (name, make_slug(name)),
            )
        except mysql.connector.Error:
            continue


def fetch_categories():
    return fetch_all('SELECT id, name, slug, created_at FROM category ORDER BY name ASC')


def ensure_admin_user():
    existing_admin = fetch_one('SELECT id FROM admin_user WHERE username = %s', (ADMIN_USERNAME,))
    if existing_admin:
        return

    password_hash = generate_password_hash(ADMIN_PASSWORD)
    execute(
        'INSERT INTO admin_user (username, password_hash) VALUES (%s, %s)',
        (ADMIN_USERNAME, password_hash),
    )


# ===================== CONTEXT =====================


@app.context_processor
def inject_cart_count():
    cart = get_cart()
    return {
        'cart_count': cart_item_count(cart),
        'admin_logged_in': is_admin_logged_in(),
        'admin_username': session.get('admin_username'),
        'user_logged_in': is_user_logged_in(),
        'user_name': session.get('user_name'),
        'user_profile_image': session.get('user_profile_image'),
    }


# ===================== ROUTES =====================


@app.route('/')
def index():
    products = fetch_all('SELECT * FROM product ORDER BY created_at DESC, id DESC LIMIT 6')
    return render_template('index.html', products=products)


@app.route('/products')
def products():
    products_list = fetch_all('SELECT * FROM product')
    return render_template('products.html', products=products_list)


@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = fetch_one('SELECT * FROM product WHERE id = %s', (product_id,))
    if not product:
        return redirect(url_for('products'))

    related_products = fetch_all(
        'SELECT * FROM product WHERE category = %s AND id != %s LIMIT 4',
        (product['category'], product_id),
    )
    return render_template('product_detail.html', product=product, related_products=related_products)


@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    product = fetch_one('SELECT * FROM product WHERE id = %s', (product_id,))
    if not product:
        flash('Product not found!', 'error')
        return redirect(url_for('products'))

    quantity = max(1, int(request.form.get('quantity', 1)))
    if product['stock'] <= 0:
        flash('This product is out of stock.', 'error')
        return redirect(url_for('product_detail', product_id=product_id))

    cart = get_cart()
    current_qty = cart.get(str(product_id), 0)
    cart[str(product_id)] = min(product['stock'], current_qty + quantity)
    save_cart(cart)

    flash(f"{product['name']} added to cart!", 'success')
    return redirect(url_for('view_cart'))


@app.route('/cart')
def view_cart():
    cart = get_cart()
    items = fetch_products_for_cart(cart)
    total = cart_total(items)
    return render_template('cart.html', items=items, total=total)


@app.route('/remove_from_cart/<int:product_id>', methods=['POST'])
def remove_from_cart(product_id):
    cart = get_cart()
    cart.pop(str(product_id), None)
    save_cart(cart)
    flash('Item removed from cart!', 'success')
    return redirect(url_for('view_cart'))


@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    cart = get_cart()
    items = fetch_products_for_cart(cart)
    if not items:
        flash('Your cart is empty!', 'error')
        return redirect(url_for('view_cart'))

    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        address = request.form.get('address')
        city = request.form.get('city')
        state = request.form.get('state')
        zipcode = request.form.get('zipcode')

        if not name or not email or not address:
            flash('Name, email, and address are required.', 'error')
            return redirect(url_for('checkout'))

        shipping_address = f"{address}, {city}, {state} {zipcode}".strip()
        total_amount = cart_total(items)
        order_number = f"LD{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        current_user_id = session.get('user_id') if is_user_logged_in() else None

        with db_cursor(commit=True) as (cursor, _):
            cursor.execute(
                '''
                INSERT INTO `order` (user_id, order_number, customer_name, customer_email, customer_phone, shipping_address, total_amount, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ''',
                (current_user_id, order_number, name, email, phone, shipping_address, total_amount, 'pending'),
            )
            order_id = cursor.lastrowid

            for item in items:
                product_id = item['product']['id']
                quantity = item['quantity']

                cursor.execute('SELECT stock FROM product WHERE id = %s', (product_id,))
                stock_row = cursor.fetchone()
                if not stock_row or stock_row['stock'] < quantity:
                    raise ValueError('Insufficient stock for one or more items.')

                cursor.execute(
                    'INSERT INTO order_item (order_id, product_id, quantity, price) VALUES (%s, %s, %s, %s)',
                    (order_id, product_id, quantity, item['product']['price']),
                )
                cursor.execute(
                    'UPDATE product SET stock = stock - %s WHERE id = %s',
                    (quantity, product_id),
                )

        save_cart({})
        flash('Order placed successfully!', 'success')
        return redirect(url_for('order_confirmation', order_id=order_id))

    total = cart_total(items)
    prefill_name = session.get('user_name', '')
    prefill_email = session.get('user_email', '')
    return render_template('checkout.html', items=items, total=total, prefill_name=prefill_name, prefill_email=prefill_email)


@app.route('/order_confirmation/<int:order_id>')
def order_confirmation(order_id):
    order = fetch_one('SELECT * FROM `order` WHERE id = %s', (order_id,))
    if not order:
        flash('Order not found.', 'error')
        return redirect(url_for('index'))

    items = fetch_all(
        '''
        SELECT oi.quantity, oi.price, p.name
        FROM order_item oi
        JOIN product p ON oi.product_id = p.id
        WHERE oi.order_id = %s
        ''',
        (order_id,),
    )

    return render_template('order_confirmation.html', order=order, items=items)


@app.route('/register', methods=['GET', 'POST'])
def user_register():
    if is_user_logged_in():
        return redirect(url_for('index'))

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not full_name or not email or not password:
            flash('Full name, email, and password are required.', 'error')
            return redirect(url_for('user_register'))
        if '@' not in email:
            flash('Please enter a valid email address.', 'error')
            return redirect(url_for('user_register'))
        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'error')
            return redirect(url_for('user_register'))
        if password != confirm_password:
            flash('Password and confirm password do not match.', 'error')
            return redirect(url_for('user_register'))

        try:
            execute(
                '''
                INSERT INTO customer_user (full_name, email, password_hash)
                VALUES (%s, %s, %s)
                ''',
                (full_name, email, generate_password_hash(password)),
            )
        except mysql.connector.Error:
            flash('Email already registered. Please log in.', 'error')
            return redirect(url_for('user_register'))

        flash('Registration successful. Please log in.', 'success')
        return redirect(url_for('user_login'))

    return render_template('user_register.html')


@app.route('/login', methods=['GET', 'POST'])
def user_login():
    if is_user_logged_in():
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        user = fetch_one(
            'SELECT id, full_name, email, password_hash, profile_image FROM customer_user WHERE email = %s',
            (email,),
        )
        if user and check_password_hash(user['password_hash'], password):
            session['is_user'] = True
            session['user_id'] = user['id']
            session['user_name'] = user['full_name']
            session['user_email'] = user['email']
            session['user_profile_image'] = user.get('profile_image')
            flash('Logged in successfully.', 'success')
            return redirect(url_for('index'))

        flash('Invalid email or password.', 'error')

    return render_template('user_login.html')


@app.route('/logout', methods=['POST'])
def user_logout():
    session.pop('is_user', None)
    session.pop('user_id', None)
    session.pop('user_name', None)
    session.pop('user_email', None)
    session.pop('user_profile_image', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))


@app.route('/orders')
@user_required
def order_history():
    user_id = session.get('user_id')
    user_email = session.get('user_email')
    orders = fetch_all(
        '''
        SELECT id, order_number, total_amount, status, created_at
        FROM `order`
        WHERE user_id = %s OR (user_id IS NULL AND customer_email = %s)
        ORDER BY created_at DESC
        ''',
        (user_id, user_email),
    )
    return render_template('order_history.html', orders=orders)


@app.route('/profile', methods=['GET', 'POST'])
@user_required
def profile():
    user_id = session.get('user_id')
    user = fetch_one(
        'SELECT id, full_name, email, profile_image, created_at FROM customer_user WHERE id = %s',
        (user_id,),
    )
    if not user:
        session.pop('is_user', None)
        session.pop('user_id', None)
        session.pop('user_name', None)
        session.pop('user_email', None)
        session.pop('user_profile_image', None)
        flash('User not found. Please login again.', 'error')
        return redirect(url_for('user_login'))

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        new_password = request.form.get('password', '')
        image_file = request.files.get('profile_image')

        if not full_name or not email:
            flash('Full name and email are required.', 'error')
            return redirect(url_for('profile'))
        if '@' not in email:
            flash('Please enter a valid email.', 'error')
            return redirect(url_for('profile'))
        if new_password and len(new_password) < 6:
            flash('If you set a new password, minimum length is 6.', 'error')
            return redirect(url_for('profile'))
        try:
            uploaded_profile_image = save_profile_image(image_file)
        except ValueError as exc:
            flash(str(exc), 'error')
            return redirect(url_for('profile'))
        final_profile_image = uploaded_profile_image or user.get('profile_image')

        try:
            if new_password:
                execute(
                    '''
                    UPDATE customer_user
                    SET full_name = %s, email = %s, password_hash = %s, profile_image = %s
                    WHERE id = %s
                    ''',
                    (full_name, email, generate_password_hash(new_password), final_profile_image, user_id),
                )
            else:
                execute(
                    'UPDATE customer_user SET full_name = %s, email = %s, profile_image = %s WHERE id = %s',
                    (full_name, email, final_profile_image, user_id),
                )
        except mysql.connector.Error:
            flash('Email already in use. Try another email.', 'error')
            return redirect(url_for('profile'))

        session['user_name'] = full_name
        session['user_email'] = email
        session['user_profile_image'] = final_profile_image
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('profile'))

    return render_template('profile.html', user=user)


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if is_admin_logged_in():
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        admin = fetch_one(
            'SELECT id, username, password_hash FROM admin_user WHERE username = %s',
            (username,),
        )

        if admin and check_password_hash(admin['password_hash'], password):
            session['is_admin'] = True
            session['admin_id'] = admin['id']
            session['admin_username'] = admin['username']
            flash('Welcome back, admin.', 'success')
            return redirect(url_for('admin_dashboard'))

        flash('Invalid username or password.', 'error')

    return render_template('admin_login.html')


@app.route('/admin/logout', methods=['POST'])
def admin_logout():
    session.pop('is_admin', None)
    session.pop('admin_id', None)
    session.pop('admin_username', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))


@app.route('/admin')
@admin_required
def admin_dashboard():
    orders_list = fetch_all(
        '''
        SELECT id, order_number, customer_name, total_amount, status, created_at
        FROM `order`
        ORDER BY created_at DESC
        LIMIT 20
        '''
    )
    stats = fetch_one(
        '''
        SELECT
            (SELECT COUNT(*) FROM product) AS total_products,
            (SELECT COUNT(*) FROM `order`) AS total_orders,
            (SELECT COALESCE(SUM(total_amount), 0) FROM `order`) AS total_revenue
        '''
    )
    return render_template(
        'admin_dashboard.html',
        orders=orders_list,
        stats=stats,
    )


@app.route('/admin/categories')
@admin_required
def admin_categories():
    categories = fetch_categories()
    return render_template('admin_categories.html', categories=categories)


@app.route('/admin/categories/add', methods=['POST'])
@admin_required
def admin_add_category():
    name = request.form.get('name', '').strip()
    if not name:
        flash('Category name is required.', 'error')
        return redirect(url_for('admin_categories'))

    try:
        execute(
            'INSERT INTO category (name, slug) VALUES (%s, %s)',
            (name, make_slug(name)),
        )
    except mysql.connector.Error:
        flash('Category already exists or is invalid.', 'error')
        return redirect(url_for('admin_categories'))

    flash('Category added successfully.', 'success')
    return redirect(url_for('admin_categories'))


@app.route('/admin/categories/<int:category_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit_category(category_id):
    category = fetch_one('SELECT id, name, slug, created_at FROM category WHERE id = %s', (category_id,))
    if not category:
        flash('Category not found.', 'error')
        return redirect(url_for('admin_categories'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        if not name:
            flash('Category name is required.', 'error')
            return redirect(url_for('admin_edit_category', category_id=category_id))

        old_name = category['name']
        try:
            execute(
                'UPDATE category SET name = %s, slug = %s WHERE id = %s',
                (name, make_slug(name), category_id),
            )
            execute('UPDATE product SET category = %s WHERE category = %s', (name, old_name))
        except mysql.connector.Error:
            flash('Could not update category. Name may already exist.', 'error')
            return redirect(url_for('admin_edit_category', category_id=category_id))

        flash('Category updated successfully.', 'success')
        return redirect(url_for('admin_categories'))

    return render_template('admin_category_edit.html', category=category)


@app.route('/admin/categories/<int:category_id>/delete', methods=['POST'])
@admin_required
def admin_delete_category(category_id):
    category = fetch_one('SELECT id, name FROM category WHERE id = %s', (category_id,))
    if not category:
        flash('Category not found.', 'error')
        return redirect(url_for('admin_categories'))

    in_use = fetch_one('SELECT COUNT(*) AS total FROM product WHERE category = %s', (category['name'],))
    if in_use and in_use['total'] > 0:
        flash('Cannot delete category that is used by products.', 'error')
        return redirect(url_for('admin_categories'))

    execute('DELETE FROM category WHERE id = %s', (category_id,))
    flash('Category deleted successfully.', 'success')
    return redirect(url_for('admin_categories'))


@app.route('/admin/products')
@admin_required
def admin_products():
    products_list = fetch_all(
        '''
        SELECT id, name, description, category, price, stock, image_url, created_at
        FROM product
        ORDER BY created_at DESC
        '''
    )
    categories = fetch_categories()
    return render_template('admin_products.html', products=products_list, categories=categories)


@app.route('/admin/products/add', methods=['POST'])
@admin_required
def admin_add_product():
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    category = request.form.get('category', '').strip()
    category_custom = request.form.get('category_custom', '').strip()
    category = category_custom or category
    image_url = request.form.get('image_url', '').strip()

    try:
        price = float(request.form.get('price', '0'))
        stock = int(request.form.get('stock', '0'))
    except ValueError:
        flash('Price and stock must be valid numbers.', 'error')
        return redirect(url_for('admin_products'))

    if not name or price < 0 or stock < 0:
        flash('Name is required. Price and stock must be non-negative.', 'error')
        return redirect(url_for('admin_products'))

    image_file = request.files.get('image_file')
    try:
        uploaded_path = save_product_image(image_file)
    except ValueError as exc:
        flash(str(exc), 'error')
        return redirect(url_for('admin_products'))

    final_image = uploaded_path or image_url or 'https://via.placeholder.com/300x400?text=Product'
    if category:
        try:
            execute(
                'INSERT INTO category (name, slug) VALUES (%s, %s)',
                (category, make_slug(category)),
            )
        except mysql.connector.Error:
            pass
    execute(
        '''
        INSERT INTO product (name, description, price, category, stock, image_url)
        VALUES (%s, %s, %s, %s, %s, %s)
        ''',
        (name, description, price, category, stock, final_image),
    )
    flash('Product added successfully.', 'success')
    return redirect(url_for('admin_products'))


@app.route('/admin/products/<int:product_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit_product(product_id):
    product = fetch_one('SELECT * FROM product WHERE id = %s', (product_id,))
    if not product:
        flash('Product not found.', 'error')
        return redirect(url_for('admin_products'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', '').strip()
        category_custom = request.form.get('category_custom', '').strip()
        category = category_custom or category
        image_url = request.form.get('image_url', '').strip()

        try:
            price = float(request.form.get('price', '0'))
            stock = int(request.form.get('stock', '0'))
        except ValueError:
            flash('Price and stock must be valid numbers.', 'error')
            return redirect(url_for('admin_edit_product', product_id=product_id))

        if not name or price < 0 or stock < 0:
            flash('Name is required. Price and stock must be non-negative.', 'error')
            return redirect(url_for('admin_edit_product', product_id=product_id))

        image_file = request.files.get('image_file')
        try:
            uploaded_path = save_product_image(image_file)
        except ValueError as exc:
            flash(str(exc), 'error')
            return redirect(url_for('admin_edit_product', product_id=product_id))

        final_image = uploaded_path or image_url or product['image_url']
        if category:
            try:
                execute(
                    'INSERT INTO category (name, slug) VALUES (%s, %s)',
                    (category, make_slug(category)),
                )
            except mysql.connector.Error:
                pass
        execute(
            '''
            UPDATE product
            SET name = %s, description = %s, price = %s, category = %s, stock = %s, image_url = %s
            WHERE id = %s
            ''',
            (name, description, price, category, stock, final_image, product_id),
        )
        flash('Product updated successfully.', 'success')
        return redirect(url_for('admin_products'))

    categories = fetch_categories()
    return render_template('admin_product_edit.html', product=product, categories=categories)


@app.route('/admin/products/<int:product_id>/delete', methods=['POST'])
@admin_required
def admin_delete_product(product_id):
    product = fetch_one('SELECT id FROM product WHERE id = %s', (product_id,))
    if not product:
        flash('Product not found.', 'error')
        return redirect(url_for('admin_products'))

    try:
        execute('DELETE FROM product WHERE id = %s', (product_id,))
    except mysql.connector.Error:
        flash('Cannot delete this product because it is tied to existing orders.', 'error')
        return redirect(url_for('admin_products'))

    flash('Product deleted successfully.', 'success')
    return redirect(url_for('admin_products'))


@app.route('/admin/orders')
@admin_required
def admin_orders():
    selected_status = request.args.get('status', '').strip().lower()
    query = '''
        SELECT id, order_number, customer_name, customer_email, total_amount, status, created_at
        FROM `order`
    '''
    params = ()
    if selected_status:
        query += ' WHERE LOWER(status) = %s'
        params = (selected_status,)
    query += ' ORDER BY created_at DESC'
    orders = fetch_all(query, params)
    return render_template('admin_orders.html', orders=orders, selected_status=selected_status)


@app.route('/admin/orders/<int:order_id>/status', methods=['POST'])
@admin_required
def admin_update_order_status(order_id):
    status = request.form.get('status', '').strip().lower()
    allowed_statuses = {'pending', 'processing', 'shipped', 'delivered', 'cancelled'}
    if status not in allowed_statuses:
        flash('Invalid order status.', 'error')
        return redirect(url_for('admin_orders'))

    order = fetch_one('SELECT id FROM `order` WHERE id = %s', (order_id,))
    if not order:
        flash('Order not found.', 'error')
        return redirect(url_for('admin_orders'))

    execute('UPDATE `order` SET status = %s WHERE id = %s', (status, order_id))
    flash('Order status updated.', 'success')
    return redirect(url_for('admin_orders'))


@app.route('/admin/users')
@admin_required
def admin_users():
    users = fetch_all(
        '''
        SELECT id, username, created_at
        FROM admin_user
        ORDER BY created_at DESC
        '''
    )
    return render_template('admin_users.html', users=users)


@app.route('/admin/users/add', methods=['POST'])
@admin_required
def admin_add_user():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')

    if not username or len(password) < 6:
        flash('Username is required and password must be at least 6 characters.', 'error')
        return redirect(url_for('admin_users'))

    try:
        execute(
            'INSERT INTO admin_user (username, password_hash) VALUES (%s, %s)',
            (username, generate_password_hash(password)),
        )
    except mysql.connector.Error:
        flash('Username already exists or could not be created.', 'error')
        return redirect(url_for('admin_users'))

    flash('Admin user created successfully.', 'success')
    return redirect(url_for('admin_users'))


@app.route('/admin/users/<int:user_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit_user(user_id):
    user = fetch_one('SELECT id, username, created_at FROM admin_user WHERE id = %s', (user_id,))
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('admin_users'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        new_password = request.form.get('password', '')

        if not username:
            flash('Username is required.', 'error')
            return redirect(url_for('admin_edit_user', user_id=user_id))
        if new_password and len(new_password) < 6:
            flash('If provided, password must be at least 6 characters.', 'error')
            return redirect(url_for('admin_edit_user', user_id=user_id))

        try:
            if new_password:
                execute(
                    'UPDATE admin_user SET username = %s, password_hash = %s WHERE id = %s',
                    (username, generate_password_hash(new_password), user_id),
                )
            else:
                execute('UPDATE admin_user SET username = %s WHERE id = %s', (username, user_id))
        except mysql.connector.Error:
            flash('Username already exists or could not be updated.', 'error')
            return redirect(url_for('admin_edit_user', user_id=user_id))

        if session.get('admin_id') == user_id:
            session['admin_username'] = username
        flash('User updated successfully.', 'success')
        return redirect(url_for('admin_users'))

    return render_template('admin_user_edit.html', user=user)


@app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def admin_delete_user(user_id):
    if session.get('admin_id') == user_id:
        flash('You cannot delete your own logged-in account.', 'error')
        return redirect(url_for('admin_users'))

    user = fetch_one('SELECT id FROM admin_user WHERE id = %s', (user_id,))
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('admin_users'))

    count_row = fetch_one('SELECT COUNT(*) AS total FROM admin_user')
    if count_row and count_row['total'] <= 1:
        flash('At least one admin user must remain.', 'error')
        return redirect(url_for('admin_users'))

    execute('DELETE FROM admin_user WHERE id = %s', (user_id,))
    flash('User deleted successfully.', 'success')
    return redirect(url_for('admin_users'))


@app.route('/admin/reports')
@admin_required
def admin_reports():
    summary = fetch_one(
        '''
        SELECT
            (SELECT COUNT(*) FROM `order`) AS total_orders,
            (SELECT COUNT(*) FROM `order` WHERE status = 'pending') AS pending_orders,
            (SELECT COUNT(*) FROM `order` WHERE status = 'delivered') AS delivered_orders,
            (SELECT COALESCE(SUM(total_amount), 0) FROM `order`) AS total_revenue
        '''
    )
    monthly_sales = fetch_all(
        '''
        SELECT
            DATE_FORMAT(created_at, '%Y-%m') AS month,
            COUNT(*) AS orders_count,
            COALESCE(SUM(total_amount), 0) AS revenue
        FROM `order`
        GROUP BY DATE_FORMAT(created_at, '%Y-%m')
        ORDER BY month DESC
        LIMIT 6
        '''
    )
    top_products = fetch_all(
        '''
        SELECT
            p.name,
            SUM(oi.quantity) AS quantity_sold,
            COALESCE(SUM(oi.quantity * oi.price), 0) AS revenue
        FROM order_item oi
        JOIN product p ON p.id = oi.product_id
        GROUP BY p.id, p.name
        ORDER BY quantity_sold DESC
        LIMIT 10
        '''
    )
    return render_template(
        'admin_reports.html',
        summary=summary,
        monthly_sales=monthly_sales,
        top_products=top_products,
    )


if __name__ == '__main__':
    ensure_tables()
    ensure_sample_products()
    ensure_sample_categories()
    ensure_admin_user()
    PRODUCT_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    PROFILE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    app.run(debug=True)

