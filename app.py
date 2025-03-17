from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector
from flask_bcrypt import Bcrypt

app = Flask(__name__)
app.secret_key = "vietanh_secret_key"
bcrypt = Bcrypt(app)

# Cấu hình kết nối MySQL
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Vietanh21405@",  # Thay bằng mật khẩu của bạn
    database="ecommerce2"
)
cursor = db.cursor()

# Trang đăng ký (GET)
@app.route('/register', methods=['GET'])
def register_page():
    return render_template('register.html')

# API đăng ký (POST)
@app.route('/register', methods=['POST'])
def register():
    username = request.form['username']
    email = request.form['email']
    password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')

    try:
        cursor.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)", (username, email, password))
        db.commit()
        return redirect(url_for('login_page'))
    except mysql.connector.Error as err:
        return f"Lỗi: {err}"

# Trang đăng nhập (GET)
@app.route('/login', methods=['GET'])
def login_page():
    return render_template('login.html')

# API đăng nhập (POST)
@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    cursor.execute("SELECT id, password FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()

    if user and bcrypt.check_password_hash(user[1], password):
        session['user_id'] = user[0]
        return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('login_page'))

# Trang chủ (dashboard)
@app.route('/dashboard')
def dashboard():
    if 'user_id' in session:
        cursor.execute("SELECT * FROM products")
        products = cursor.fetchall()
        return render_template('dashboard.html', products=products)
    return redirect(url_for('login_page'))

# Thêm sản phẩm vào giỏ hàng
@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    if 'user_id' in session:
        user_id = session['user_id']
        cursor.execute("SELECT id, quantity FROM cart WHERE user_id = %s AND product_id = %s", (user_id, product_id))
        item = cursor.fetchone()

        if item:
            cursor.execute("UPDATE cart SET quantity = quantity + 1 WHERE id = %s", (item[0],))
        else:
            cursor.execute("INSERT INTO cart (user_id, product_id, quantity) VALUES (%s, %s, 1)", (user_id, product_id))
        
        db.commit()
        return redirect(url_for('cart'))
    return redirect(url_for('login_page'))

# Xóa sản phẩm khỏi giỏ hàng
@app.route('/remove_from_cart/<int:cart_id>', methods=['POST'])
def remove_from_cart(cart_id):
    if 'user_id' in session:
        cursor.execute("DELETE FROM cart WHERE id=%s", (cart_id,))
        db.commit()
        return redirect(url_for('cart'))
    return redirect(url_for('login_page'))

# Hiển thị giỏ hàng
@app.route("/cart")
def cart():
    if "user_id" not in session:
        return redirect(url_for("login_page"))

    user_id = session["user_id"]
    cursor.execute("""
        SELECT cart.id, products.name, products.price, products.image, cart.quantity 
        FROM cart 
        JOIN products ON cart.product_id = products.id 
        WHERE cart.user_id = %s
    """, (user_id,))
    
    cart_items = cursor.fetchall()
    total_price = sum(item[2] * item[4] for item in cart_items)

    return render_template("cart.html", cart_items=cart_items, total_price=total_price)

# Mua hàng (chuyển hướng sang trang thanh toán thành công)
@app.route('/checkout', methods=['POST']) 
def checkout(): 
    if 'user_id' in session: 
        user_id = session['user_id'] 
        # Lấy thông tin giỏ hàng 
        cursor.execute(""" 
            SELECT products.name, products.price, cart.quantity  
            FROM cart  
            JOIN products ON cart.product_id = products.id  
            WHERE cart.user_id = %s 
        """, (user_id,)) 
        cart_items = cursor.fetchall() 
        # Tính tổng tiền 
        total_price = sum(item[1] * item[2] for item in cart_items) 
        # Xóa giỏ hàng sau khi thanh toán 
        cursor.execute("DELETE FROM cart WHERE user_id=%s", (user_id,)) 
        db.commit() 
        return render_template('checkout_success.html', cart_items=cart_items, total_price=total_price) 


    return redirect(url_for('login_page')) 

 
# Cập nhật số lượng sản phẩm trong giỏ hàng
@app.route('/update_cart/<int:cart_id>', methods=['POST'])
def update_cart(cart_id):
    if 'user_id' in session:
        new_quantity = request.form.get('quantity', type=int)
        if new_quantity and new_quantity > 0:
            cursor.execute("UPDATE cart SET quantity = %s WHERE id = %s", (new_quantity, cart_id))
            db.commit()
        return redirect(url_for('cart'))
    return redirect(url_for('login_page'))

# Đăng xuất
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login_page'))
    

@app.route('/')
def home():
    return redirect(url_for('dashboard'))  # Hoặc có thể render một template khác nếu cần

# đăng kí cho admin 
@app.route('/admin_register', methods=['GET', 'POST'])
def admin_register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("INSERT INTO admin (username, password) VALUES (%s, %s)", (username, hashed_password))
            conn.commit()
            conn.close()
            return redirect('/admin_login')
        except mysql.connector.Error as err:
            conn.close()
            return f"Lỗi: {err}"

    return render_template('admin_register.html')


# đăng nhập cho admin
@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT password FROM admin WHERE username = %s", (username,))
        admin = cursor.fetchone()
        conn.close()

        if admin and bcrypt.check_password_hash(admin[0], password):
            session['admin'] = username
            return redirect('/admin_dashboard')
        else:
            return "Sai tài khoản hoặc mật khẩu!"

    return render_template('admin_login.html')


@app.route('/admin_logout')
def admin_logout():
    session.pop('admin', None)
    return redirect('/admin_login')

# sửa lý danh sách sản phẩm 
@app.route('/admin_dashboard')
def admin_dashboard():
    if 'admin' not in session:
        return redirect('/admin_login')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    conn.close()

    return render_template('admin_dashboard.html', products=products)

# code sử lý thêm sản phẩm 
@app.route('/admin_add_product', methods=['GET', 'POST'])
def admin_add_product():
    if 'admin' not in session:
        return redirect('/admin_login')

    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = request.form['price']
        image = request.form['image']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO products (name, description, price, image) VALUES (%s, %s, %s, %s)",
                       (name, description, price, image))
        conn.commit()
        conn.close()

        return redirect('/admin_dashboard')

    return render_template('admin_add_product.html')
 
 # code sửa sản phẩm 
@app.route('/admin_edit_product/<int:id>', methods=['GET', 'POST'])
def admin_edit_product(id):

    if 'admin' not in session:
        return redirect('/admin_login')

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = request.form['price']
        image = request.form['image']

        cursor.execute("UPDATE products SET name=%s, description=%s, price=%s, image=%s WHERE id=%s",
                       (name, description, price, image, id))
        conn.commit()
        conn.close()

        return redirect('/admin_dashboard')

    cursor.execute("SELECT * FROM products WHERE id=%s", (id,))
    product = cursor.fetchone()
    conn.close()

    return render_template('admin_edit_product.html', product=product)
 
 # code xóa sản phẩm 
@app.route('/admin_delete_product/<int:id>')
def admin_delete_product(id):
    if 'admin' not in session:
        return redirect('/admin_login')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM products WHERE id=%s", (id,))
    conn.commit()
    conn.close()

    return redirect('/admin_dashboard')

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Vietanh21405@",  # Thay bằng mật khẩu của bạn
        database="ecommerce2"
    )

if __name__ == "__main__":
    app.run(debug=True)
