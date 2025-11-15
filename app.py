import os
import psycopg2
import asyncio  # Async function တွေကို run ဖို့
from flask import Flask, render_template, jsonify, request
import bot  # bot.py ဖိုင်ကို import လုပ်ခြင်း
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

app = Flask(__name__)

# --- Environment Keys များကို ယူခြင်း ---
TOKEN = os.environ.get('TELEGRAM_TOKEN')
DATABASE_URL = os.environ.get('DATABASE_URL')
APP_URL = os.environ.get('APP_URL') # Website လိပ်စာ (အသစ်ထည့်ရမယ်)

# --- Telegram Bot Application ကို တည်ဆောက်ခြင်း ---
if TOKEN:
    # Bot Application ကို ဒီမှာ တည်ဆောက်ထားမယ်
    persistence = None # persistence မသုံးတော့ပါ
    application = Application.builder().token(TOKEN).persistence(persistence).build()
    
    # bot.py ထဲက function တွေကို ဒီမှာ ချိတ်ပေးမယ်
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(MessageHandler(filters.PHOTO, bot.handle_photo))
else:
    print("---!!! APP ERROR: TELEGRAM_TOKEN မရှိလို့ Bot ကို မ run နိုင်ပါ။ ---!!!")

# --- Database Setup (အရင်အတိုင်း) ---
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

# --- Webhook Route (Telegram က ဒီကို လှမ်းပစ်မှာပါ) ---
@app.route(f"/{TOKEN}", methods=['POST'])
def telegram_webhook():
    if request.is_json:
        update_data = request.get_json(force=True)
        update = Update.de_json(update_data, application.bot)
        
        # Flask (Sync) ပေါ်မှာ Telegram (Async) ကို run ဖို့
        asyncio.run(application.process_update(update))
        print(f"--- Webhook received and processed for user {update.effective_user.id} ---")
        return "ok", 200
    else:
        return "Bad Request", 400

# --- Webhook ကို တစ်ခါပဲ Register လုပ်မယ့် Route ---
@app.route('/set_webhook')
def set_webhook():
    if not APP_URL or not TOKEN:
        return "Error: APP_URL or TOKEN Environment Variable မရှိပါ။", 500
        
    webhook_url = f"{APP_URL}/{TOKEN}"
    success = asyncio.run(application.bot.set_webhook(url=webhook_url))
    
    if success:
        print(f"--- Webhook set successfully to {webhook_url} ---")
        return f"Webhook set to {webhook_url}", 200
    else:
        print("--- Webhook setup failed. ---")
        return "Webhook setup failed.", 500
# --------------------------------------

# --- Website Routes (အရင်အတိုင်း) ---
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/<page_name>')
def show_page(page_name):
    if not page_name.endswith('.html'):
        page_name += '.html'
    safe_pages = ['index.html', 'shoes.html', 'clothing.html', 'accessories.html']
    if page_name in safe_pages:
        return render_template(page_name)
    else:
        return "Page Not Found", 404

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

