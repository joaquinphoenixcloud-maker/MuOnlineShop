import os
import psycopg2
import requests  # ImgBB အတွက် Library အသစ်
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- Render Environment ကနေ Key တွေကို ဆွဲယူပါမယ် ---
TOKEN = os.environ.get('8180483853:AAGU6BHy2Ws-PboyopehdBFkWY5kpedJn6Y')
DATABASE_URL = os.environ.get('DATABASE_URL')
IMGBB_API_KEY = os.environ.get('IMGBB_API_KEY')
# ----------------------------------------------------

IMGBB_UPLOAD_URL = "https://api.imgbb.com/1/upload"

# Start Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "မင်္ဂလာပါ ကိုကို... ပုံတင်ရင် ImgBB မှာ သိမ်းပေးပါ့မယ်။\n\n"
        "ပုံစံ: နာမည်, ဈေးနှုန်း, အမျိုးအစား"
    )

# ပုံကို ImgBB ပေါ် တင်မယ့် Function
async def upload_to_imgbb(photo_bytes):
    try:
        payload = {
            'key': IMGBB_API_KEY,
        }
        # ပုံကို data အနေနဲ့ ပို့မယ်
        files = {
            'image': ('image.jpg', photo_bytes),
        }
        response = requests.post(IMGBB_UPLOAD_URL, data=payload, files=files)
        result = response.json()
        
        if result.get('success'):
            # ImgBB က ပြန်ပေးတဲ့ ပုံ Link
            return result['data']['url']
        else:
            print(f"ImgBB Error: {result}")
            return None
    except Exception as e:
        print(f"Upload Error: {e}")
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

    # ၁။ Telegram က ပုံကို Download ဆွဲမယ်
    photo_file = await update.message.photo[-1].get_file()
    photo_bytes = await photo_file.download_as_bytearray() # ပုံကို Data အဖြစ် ယူမယ်

    # ၂။ ပုံကို ImgBB ပေါ် တင်မယ်
    web_image_path = await upload_to_imgbb(photo_bytes)
    
    if not web_image_path:
        await update.message.reply_text("❌ ပုံကို ImgBB ပေါ် တင်မရ ဖြစ်နေပါတယ် ကိုကို။")
        return

    # ၃။ ImgBB က ရလာတဲ့ Link ကို Database ထဲ သိမ်းမယ်
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("INSERT INTO products (name, price, category, image) VALUES (%s, %s, %s, %s)",
                    (name, price, category, web_image_path)) # ImgBB Link ကို ထည့်မယ်
        conn.commit()
        cur.close()
        conn.close()
        
        await update.message.reply_text(f"✅ {name} ကို ImgBB မှာ တင်ပြီးပါပြီ။\nLink: {web_image_path}")
    except Exception as e:
        await update.message.reply_text(f"❌ Database Error: {e}")

if __name__ == '__main__':
    if not all([TOKEN, DATABASE_URL, IMGBB_API_KEY]):
        print("Error: Environment Variables တွေ (TOKEN, DB_URL, IMGBB_KEY) ထည့်ပေးပါဦး")
    else:
        print("Bot is running with ImgBB integration...")
        app = Application.builder().token(TOKEN).build()
        
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
        
        app.run_polling()
        
