import os
import psycopg2
import threading  # Bot ကို နောက်ကွယ်မှာ run ဖို့
from flask import Flask, render_template, jsonify

# --- bot.py ဖိုင်ထဲက Function တွေကို ခေါ်သုံးဖို့ ---
import bot 

app = Flask(__name__)

# --- Database Setup (အရင်အတိုင်း) ---
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        print(f"[App Error] DB Connection Failed: {e}")
        return None

def init_db():
    try:
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            cur.execute('''
                CREATE TABLE IF NOT EXISTS products (
                    id SERIAL PRIMARY KEY, name TEXT, price TEXT, category TEXT, image TEXT
                )
            ''')
            conn.commit()
            cur.close()
            conn.close()
            print("--- Database initialized successfully. ---")
    except Exception as e:
        print(f"[App Error] DB Init Error: {e}")

if DATABASE_URL:
    init_db()
# --------------------------------------

# --- Website Routes (HTML စာမျက်နှာတွေ) ---
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/<page_name>')
def show_page(page_name):
    # .html မပါဘဲ ခေါ်မိရင်
    if not page_name.endswith('.html'):
        page_name += '.html'
        
    # Security အတွက် ကိုကို့မှာ ရှိတဲ့ ဖိုင်နာမည်တွေကိုပဲ ဖွင့်ပေးမယ်
    safe_pages = ['index.html', 'shoes.html', 'clothing.html', 'accessories.html']
    if page_name in safe_pages:
        return render_template(page_name)
    else:
        return "Page Not Found", 404

# --- API Route (Database က ပစ္စည်းတွေ ပြန်ပို့ပေးဖို့) ---
@app.route('/api/products')
def get_products():
    product_list = []
    try:
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            cur.execute('SELECT id, name, price, category, image FROM products ORDER BY id DESC')
            products = cur.fetchall()
            cur.close()
            conn.close()
            
            for p in products:
                product_list.append({
                    "id": p[0], "name": p[1], "price": p[2], "category": p[3], "image": p[4]
                })
    except Exception as e:
        print(f"[App Error] Get Products API Error: {e}")
        
    return jsonify(product_list)
# --------------------------------------

# --- Bot ကို Background Thread အဖြစ် စတင်ခြင်း ---
# Gunicorn က ဒီဖိုင်ကို run တာနဲ့ Bot လည်း အတူတူ စ run မယ်
print("--- Starting background bot thread... ---")
bot_thread = threading.Thread(target=bot.run_bot)
bot_thread.daemon = True  # Main app ရပ်ရင် Bot ပါ အတူရပ်မယ်
bot_thread.start()
# --------------------------------------

if __name__ == '__main__':
    # ဒါက Local မှာ run ရင် သုံးဖို့
    app.run(port=5000, debug=True)

