import os
import psycopg2
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
# --- .persistence(None) ထည့်ဖို့ import လုပ်မယ် ---
from telegram.ext import PicklePersistence 

# --- Render Environment ကနေ Key တွေကို ဆွဲယူပါမယ် ---
TOKEN = os.environ.get('TELEGRAM_TOKEN')
DATABASE_URL = os.environ.get('DATABASE_URL')
IMGBB_API_KEY = os.environ.get('IMGBB_API_KEY')
# ----------------------------------------------------

IMGBB_UPLOAD_URL = "https://api.imgbb.com/1/upload"

# Start Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "မင်္ဂလာပါ ကိုကို... Persistence (None) စနစ် အဆင်သင့်ပါ။\n\n"
        "ပုံစံ: နာမည်, ဈေးနှုန်း, အမျိုးအစား"
    )

# ပုံကို ImgBB ပေါ် တင်မယ့် Function
async def upload_to_imgbb(photo_bytes):
    try:
        payload = {'key': IMGBB_API_KEY}
        files = {'image': ('image.jpg', photo_bytes)}
        response = requests.post(IMGBB_UPLOAD_URL, data=payload, files=files)
        result = response.json()
        
        if result.get('success'):
            return result['data']['url']
        else:
            print(f"[Bot Error] ImgBB Upload Failed: {result.get('error', {}).get('message')}")
            return None
    except Exception as e:
        print(f"[Bot Error] Upload Function Error: {e}")
        return None

# ပုံနဲ့ စာ လက်ခံမယ့် Function
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    caption = update.message.caption
    if not caption or "," not in caption:
        await update.message.reply_text("⚠️ ပုံစံမှားနေပါတယ်။ (Name, Price, Category)")
        return

    parts = [p.strip() for p in caption.split(',')]
    if len(parts) < 3:
        await update.message.reply_text("⚠️ (အမည်, ဈေးနှုန်း, အမျိုးအစား) ၃ ခု ပါရပါမယ်။")
        return

    name, price, category = parts[0], parts[1], parts[2].lower()

    try:
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()
    except Exception as e:
        print(f"[Bot Error] Photo Download Error: {e}")
        await update.message.reply_text("❌ ပုံကို Download ဆွဲလို့မရပါ။")
        return

    web_image_path = await upload_to_imgbb(photo_bytes)
    
    if not web_image_path:
        await update.message.reply_text("❌ ပုံကို ImgBB ပေါ် တင်မရ ဖြစ်နေပါတယ် ကိုကို။")
        return

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("INSERT INTO products (name, price, category, image) VALUES (%s, %s, %s, %s)",
                    (name, price, category, web_image_path))
        conn.commit()
        cur.close()
        conn.close()
        
        await update.message.reply_text(f"✅ {name} ကို ImgBB မှာ တင်ပြီးပါပြီ။\nLink: {web_image_path}")
    except Exception as e:
        print(f"[Bot Error] Database Insert Error: {e}")
        await update.message.reply_text(f"❌ Database Error: {e}")

# app.py က ခေါ် run မယ့် ပင်မ Function
def run_bot():
    if not all([TOKEN, DATABASE_URL, IMGBB_API_KEY]):
        print("---!!! BOT ERROR: Environment Variables တွေ အကုန်မပြည့်စုံလို့ Bot ကို မ run နိုင်ပါ။ ---!!!")
        return

    try:
        print("--- Bot background thread is starting (Persistence=None)... ---")
        
        # --- ဒီနေရာမှာ .persistence(None) ကို ထည့်လိုက်ပါတယ် ---
        # ဒါမှ Render Server မှာ ယာယီဖိုင် Error မတက်တော့မှာပါ
        app = Application.builder().token(TOKEN).persistence(None).build()
        # ----------------------------------------------------
        
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
        
        print("--- Bot is now polling. ---")
        app.run_polling()
    except Exception as e:
        print(f"---!!! BOT CRASHED: {e} ---!!!")
        
