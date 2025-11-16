import os
import requests
import asyncio
from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin, AdminIndexView, ModelView
from flask_login import UserMixin, LoginManager, login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from wtforms import form, fields, validators

# --- Environment Keys များကို ယူခြင်း ---
DATABASE_URL = os.environ.get('DATABASE_URL')
# Flask-Login အတွက် လျှို့ဝှက် Key (အသစ်ထည့်ရမယ်)
SECRET_KEY = os.environ.get('SECRET_KEY') 
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
# ကိုကို့ Telegram ID (Bot က Order ပို့ဖို့)
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID') 

# --- App နှင့် Database တည်ဆောက်ခြင်း ---
db = SQLAlchemy()
login_manager = LoginManager()

# --- Database Models (အချက်အလက် သိမ်းမယ့် ဇယားများ) ---

# Admin Panel ကို Login ဝင်မယ့် User ဇယား
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    password_hash = db.Column(db.String(200))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# ပစ္စည်း (Product) ဇယား
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    price = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(100))
    image_url = db.Column(db.String(500)) # ImgBB Link ကို ဒီမှာ သိမ်းမယ်

# Order ဇယား (Customer က မှာရင်)
class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(200))
    phone_number = db.Column(db.String(100))
    items = db.Column(db.Text) # ဘာတွေဝယ်လဲ
    receipt_image_url = db.Column(db.String(500)) # ပြေစာ ImgBB Link
    is_delivered = db.Column(db.Boolean, default=False)

# --- Admin Panel Setup ---

# Login မဝင်ထားရင် Admin Panel ကို ဝင်မရအောင် ကာကွယ်ခြင်း
class MyAdminIndexView(AdminIndexView):
    def is_accessible(self):
        return current_user.is_authenticated
    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login', next=request.url))

class ProtectedModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated
    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login', next=request.url))

# Product ဇယားကို Admin Panel မှာ ပြင်လို့ရအောင် ထည့်ခြင်း
class ProductAdminView(ProtectedModelView):
    column_searchable_list = ('name', 'category') # Search လုပ်လို့ရအောင်
    column_filters = ('category',) # Filter ခွဲလို့ရအောင်

# Order ဇယားကို Admin Panel မှာ ကြည့်လို့ရအောင် ထည့်ခြင်း
class OrderAdminView(ProtectedModelView):
    column_list = ('id', 'customer_name', 'phone_number', 'items', 'receipt_image_url', 'is_delivered')
    can_create = False # Admin က Order အသစ် မဖန်တီးနိုင်၊ ကြည့်ရုံပဲ

# User (Admin) ဇယားကို Admin Panel မှာ ပြင်လို့ရအောင် ထည့်ခြင်း
class UserAdminView(ProtectedModelView):
    # Password Hash ကို Admin Panel မှာ မပြအောင် ဖွက်ထားမယ်
    form_excluded_columns = ('password_hash',)
    # User အသစ်ဆောက်ရင် Password ကို hash လုပ်မယ်
    def on_model_change(self, form, model, is_created):
        if form.password.data:
            model.set_password(form.password.data)

# --- Login Form တည်ဆောက်ခြင်း ---
class LoginForm(form.Form):
    username = fields.StringField(validators=[validators.InputRequired()])
    password = fields.PasswordField(validators=[validators.InputRequired()])

# --- Flask App ကို တည်ဆောက်မယ့် ပင်မ Function (Factory) ---
def create_app():
    app = Flask(__name__)
    
    # Render Environment က Key တွေကို App ထဲ ထည့်ခြင်း
    app.config['SECRET_KEY'] = SECRET_KEY
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
    
    # Database (db) နှင့် LoginManager ကို App နှင့် ချိတ်ဆက်ခြင်း
    db.init_app(app)
    login_manager.init_app(app)
    
    # Admin Panel ကို App နှင့် ချိတ်ဆက်ခြင်း
    admin = Admin(app, name='K Online Admin', template_mode='bootstrap4', index_view=MyAdminIndexView())
    admin.add_view(ProductAdminView(Product, db.session))
    admin.add_view(OrderAdminView(Order, db.session))
    admin.add_view(UserAdminView(User, db.session))

    # --- Login Routes (Admin ဝင်ဖို့) ---
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        form = LoginForm(request.form)
        if request.method == 'POST' and form.validate():
            user = db.session.query(User).filter_by(username=form.username.data).first()
            if user and user.check_password(form.password.data):
                login_user(user)
                return redirect(url_for('admin.index'))
            flash('Invalid username or password')
        return render_template('login.html', form=form) # login.html လိုမယ်

    @app.route('/logout')
    def logout():
        logout_user()
        return redirect(url_for('admin.index'))

    # --- Website Routes (Customer ကြည့်ဖို့) ---
    @app.route('/')
    def home():
        return render_template('index.html')

    @app.route('/<page_name>')
    def show_page(page_name):
        if not page_name.endswith('.html'): page_name += '.html'
        safe_pages = ['index.html', 'shoes.html', 'clothing.html', 'accessories.html', 'checkout.html']
        if page_name in safe_pages: return render_template(page_name)
        else: return "Page Not Found", 404

    @app.route('/api/products')
    def get_products():
        products = db.session.query(Product).order_by(Product.id.desc()).all()
        product_list = [
            {"id": p.id, "name": p.name, "price": p.price, "category": p.category, "image_url": p.image_url}
            for p in products
        ]
        return jsonify(product_list)

    # --- Order တင်ရင် Bot ကို လှမ်းပို့မယ့် Route (အနာဂတ်အတွက်) ---
    @app.route('/submit_order', methods=['POST'])
    def submit_order():
        # ဒီနေရာမှာ Customer က ပို့လိုက်တဲ့ Order နဲ့ ပြေစာပုံကို လက်ခံပြီး
        # Database (Order ဇယား) ထဲ ထည့်မယ်
        # ပြီးရင် Telegram Bot ကနေ ကိုကို့ဆီကို "Order တက်ပါတယ်" လို့ ပို့ခိုင်းမယ်
        # (ဒါက နောက်တစ်ဆင့်မှ ဆက်လုပ်ပါမယ်)
        return "Order Received (Bot function not yet built)", 200

    print("--- Flask App created successfully with Admin Panel. ---")
    return app

# --- Gunicorn က ဒီ file ကို run ရင် ဒီ create_app() ကို ခေါ်သုံးလိမ့်မယ် ---
app = create_app()

# --- Database Tables တွေကို အလိုအလျောက် ဆောက်ပေးဖို့ ---
# (Server စ run တိုင်း ဇယားတွေ ရှိမရှိ စစ်ပေးပါလိမ့်မယ်)
with app.app_context():
    db.create_all()

