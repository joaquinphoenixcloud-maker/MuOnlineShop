import os
import psycopg2
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ကိုကို့ Token
TOKEN = '8180483853:AAGU6BHy2Ws-PboyopehdBFkWY5kpedJn6Y'
UPLOAD_FOLDER = 'static/uploads'

# Render က ပေးတဲ့ Database URL
DATABASE_URL = os.environ.get('DATABASE_URL')

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    caption = update.message.caption
    if not caption or "," not in caption:
        await update.message.reply_text("ပုံစံမှားနေပါတယ်။ Caption မှာ 'Name, Price, Category' ရေးပေးပါ။")
        return

    parts = [p.strip() for p in caption.split(',')]
    if len(parts) < 3:
        await update.message.reply_text("အချက်အလက် မပြည့်စုံပါ။")
        return

    name, price, category = parts[0], parts[1], parts[2].lower()

    # ပုံသိမ်းခြင်း (Render Free မှာ ပုံက ခဏနေပျက်နိုင်တာ သတိပြုပါ)
    if not os.path.exists(UPLOAD_FOLDER): os.makedirs(UPLOAD_FOLDER)
    photo_file = await update.message.photo[-1].get_file()
    filename = f"{update.message.id}.jpg"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    await photo_file.download_to_drive(filepath)

    # Postgres ထဲ ထည့်ခြင်း
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        # SQLite (?) အစား Postgres မှာ (%s) သုံးရပါတယ်
        cur.execute("INSERT INTO products (name, price, category, image) VALUES (%s, %s, %s, %s)",
                    (name, price, category, f"/static/uploads/{filename}"))
        conn.commit()
        cur.close()
        conn.close()
        
        await update.message.reply_text(f"✅ {name} ကို Database (Postgres) မှာ သိမ်းလိုက်ပါပြီ။")
    except Exception as e:
        await update.message.reply_text(f"❌ Database Error: {e}")

if __name__ == '__main__':
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    print("Bot is running...")
    app.run_polling()
    
