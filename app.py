import os
import psycopg2
from flask import Flask, render_template, jsonify

app = Flask(__name__)
UPLOAD_FOLDER = 'static/uploads'

# Render က ပေးတဲ့ Database URL ကို ယူမယ်
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL)
    return conn

# Database ဇယား ဆောက်ခြင်း
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    # Postgres မှာ AUTOINCREMENT အစား SERIAL သုံးရတယ်
    cur.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            price TEXT NOT NULL,
            category TEXT NOT NULL,
            image TEXT NOT NULL
        )
    ''')
    conn.commit()
    cur.close()
    conn.close()

# Server စစချင်း Database ဆောက်မယ်
if DATABASE_URL:
    try:
        init_db()
    except Exception as e:
        print(f"DB Error: {e}")

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/products')
def get_products():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT id, name, price, category, image FROM products ORDER BY id DESC')
    products = cur.fetchall()
    cur.close()
    conn.close()
    
    # List of Dictionaries ပုံစံပြောင်းခြင်း
    product_list = []
    for p in products:
        product_list.append({
            "id": p[0], "name": p[1], "price": p[2], "category": p[3], "image": p[4]
        })
    return jsonify(product_list)

if __name__ == '__main__':
    if not os.path.exists(UPLOAD_FOLDER): os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True)
    