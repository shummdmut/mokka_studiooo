import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = 'super_secret_key_for_mokka_studio_exclusive'

DB_FILE = 'database.db'

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                price INTEGER NOT NULL,
                discount_price INTEGER DEFAULT NULL,
                image TEXT NOT NULL,
                status TEXT NOT NULL
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_name TEXT NOT NULL,
                client_phone TEXT NOT NULL,
                items_text TEXT NOT NULL,
                total_price INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM products")
        if cursor.fetchone() == 0:
            products_data = [
                ("Кругла сумка-кросбоді 'Mokka Mini'", 1450, None, "bag_round.jpg", "available"),
                ("Капелюх-канотьє з чорною стрічкою", 1200, None, "hat_canotier.jpg", "available"),
                ("Трендовий шопер 'Еко-Елегант'", 1900, None, "shopper_tan.jpg", "available"),
                ("Серветки для сервірування (сет 4 шт)", 850, None, "placemats.jpg", "order"),
                ("Плетений кошик для дрібниць", 950, None, "basket_decor.jpg", "order"),
                ("Сумка 'Вінтаж' з дерев'яними ручками", 1600, None, "bag_vintage.jpg", "order")
            ]
            conn.executemany(
                "INSERT INTO products (name, price, discount_price, image, status) VALUES (?, ?, ?, ?, ?)",
                products_data
            )
        conn.commit()

init_db()

@app.route('/')
def home():
    conn = get_db()
    # Сортуємо так, щоб available (В наявності) завжди було вгорі вітрини
    all_items = conn.execute("SELECT * FROM products ORDER BY status ASC, id DESC").fetchall()
    conn.close()
    return render_template('index.html', products=all_items)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        try:
            conn = get_db()
            conn.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)", (username, email, password))
            conn.commit()
            conn.close()
            flash('Реєстрація успішна! Тепер увійдіть.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Користувач з таким логіном або email вже існує.', 'error')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == 'admin' and password == 'admin123':
            session['is_admin'] = True
            session['username'] = 'Адміністратор Mokka'
            flash('Ви увійшли в панель адміністратора!', 'success')
            return redirect(url_for('admin_panel'))
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password)).fetchone()
        conn.close()
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash('Вхід успішний! Приємних покупок.', 'success')
            return redirect(url_for('home'))
        flash('Неправильне ім\'я користувача або пароль.', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Ви вийшли з особистого акаунту.', 'success')
    return redirect(url_for('home'))

@app.route('/admin')
def admin_panel():
    if not session.get('is_admin'):
        flash('Доступ заборонено! Спочатку увійдіть як адміністратор.', 'error')
        return redirect(url_for('login'))
    conn = get_db()
    all_products = conn.execute("SELECT * FROM products").fetchall()
    all_orders = conn.execute("SELECT * FROM orders ORDER BY created_at DESC").fetchall()
    conn.close()
    processed_orders = []
    for order in all_orders:
        raw_phone = order['client_phone']
        clean_phone = "".join([c for c in raw_phone if c.isdigit()])
        order_dict = dict(order)
        order_dict['clean_phone'] = clean_phone
        processed_orders.append(order_dict)
    return render_template('admin.html', products=all_products, orders=processed_orders)

@app.route('/admin/add', methods=['POST'])
def admin_add():
    if not session.get('is_admin'): return redirect(url_for('login'))
    name = request.form['name']
    price = int(request.form['price'])
    status = request.form['status']
    image = request.form['image'] if request.form['image'] else "default.jpg"
    conn = get_db()
    conn.execute("INSERT INTO products (name, price, image, status) VALUES (?, ?, ?, ?)", (name, price, image, status))
    conn.commit()
    conn.close()
    flash('Товар успішно додано на сайт!', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/admin/delete/<int:product_id>')
def admin_delete(product_id):
    if not session.get('is_admin'): return redirect(url_for('login'))
    conn = get_db()
    conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()
    flash('Товар видалено з бази даних.', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/admin/discount/<int:product_id>', methods=['POST'])
def admin_discount(product_id):
    if not session.get('is_admin'): return redirect(url_for('login'))
    action = request.form['action']
    conn = get_db()
    if action == 'set':
        disc_price = int(request.form['discount_price'])
        conn.execute("UPDATE products SET discount_price = ? WHERE id = ?", (disc_price, product_id))
        flash('Знижку активовано!', 'success')
    elif action == 'remove':
        conn.execute("UPDATE products SET discount_price = NULL WHERE id = ?", (product_id,))
        flash('Знижку скасовано. Повернуто стандартну ціну.', 'success')
    conn.commit()
    conn.close()
    return redirect(url_for('admin_panel'))

@app.route('/admin/order_done/<int:order_id>')
def admin_order_done(order_id):
    if not session.get('is_admin'): return redirect(url_for('login'))
    conn = get_db()
    conn.execute("DELETE FROM orders WHERE id = ?", (order_id,))
    conn.commit()
    conn.close()
    flash('Замовлення успішно виконано та архівовано!', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/add_to_cart/<int:product_id>')
def add_to_cart(product_id):
    if 'cart' not in session:
        session['cart'] = []
    cart = session['cart']
    cart.append(product_id)
    session['cart'] = cart
    flash('Товар додано до кошика Mokka Studio!', 'success')
    return redirect(url_for('home'))

@app.route('/cart')
def cart():
    if 'cart' not in session or len(session['cart']) == 0:
        return render_template('cart.html', products=[], total=0)
    conn = get_db()
    placeholders = ', '.join('?' for _ in session['cart'])
    cart_products = conn.execute(f"SELECT * FROM products WHERE id IN ({placeholders})", session['cart']).fetchall()
    conn.close()
    total_price = 0
    for item in cart_products:
        total_price += item['discount_price'] if item['discount_price'] else item['price']
    return render_template('cart.html', products=cart_products, total=total_price)

@app.route('/clear_cart')
def clear_cart():
    session.pop('cart', None)
    flash('Кошик очищено.', 'success')
    return redirect(url_for('cart'))

@app.route('/checkout', methods=['POST'])
def checkout():
    if 'cart' not in session or len(session['cart']) == 0:
        return redirect(url_for('home'))
    client_name = request.form['name']
    client_phone = request.form['phone']
    conn = get_db()
    placeholders = ', '.join('?' for _ in session['cart'])
    cart_products = conn.execute(f"SELECT * FROM products WHERE id IN ({placeholders})", session['cart']).fetchall()
    order_items_text = ""
    total_price = 0
    for idx, item in enumerate(cart_products, 1):
        price = item['discount_price'] if item['discount_price'] else item['price']
        total_price += price
        status_text = "В наявності" if item['status'] == 'available' else "Під замовлення"
        order_items_text += f"{idx}. {item['name']} ({status_text}) — {price} грн; "
    conn.execute(
        "INSERT INTO orders (client_name, client_phone, items_text, total_price) VALUES (?, ?, ?, ?)",
        (client_name, client_phone, order_items_text, total_price)
    )
    conn.commit()
    conn.close()
    session.pop('cart', None)
    flash('Дякуємо! Ваше замовлення успішно оформлено. Чекайте на дзвінок майстра Mokka Studio.', 'success')
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
