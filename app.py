import os
import requests
import asyncio
from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin, AdminIndexView, ModelView
# --- UserMixin က ဒီထဲမှာ ရှိတာ မှန်ပါတယ် ---
from flask_login import UserMixin, LoginManager, login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
# --- wtforms Import အမှားကို ဒီမှာ ပြင်ထားပါတယ် ---
from wtforms import Form as WtformsForm  # 'form' အသေး မဟုတ်ပါ
from wtforms import StringField, PasswordField # 'fields' မဟုတ်ပါ
from wtforms import validators
# ------------------------------------------

# --- Environment Keys များကို ယူခြင်း ---
DATABASE_URL = os.environ.get('DATABASE_URL')
SECRET_KEY = os.environ.get('SECRET_KEY') 
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
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

class ProductAdminView(ProtectedModelView):
    column_searchable_list = ('name', 'category')
    column_filters = ('category',)

class OrderAdminView(ProtectedModelView):
    column_list = ('id', 'customer_name', 'phone_number', 'items', 'receipt_image_url', 'is_delivered')
    can_create = False

class UserAdminView(ProtectedModelView):
    form_excluded_columns = ('password_hash',)
    def on_model_change(self, form, model, is_created):
        if hasattr(form, 'password') and form.password.data:
            model.set_password(form.password.data)

# --- Login Form တည်ဆောက်ခြင်း (Import အမှား ပြင်ထား) ---
class LoginForm(WtformsForm): # 'form.Form' မဟုတ်ပါ
    username = StringField(validators=[validators.InputRequired()]) # 'fields.StringField' မဟုတ်ပါ
    password = PasswordField(validators=[validators.InputRequired()]) # 'fields.PasswordField' မဟုတ်ပါ

# --- Flask App ကို တည်ဆောက်မယ့် ပင်မ Function (Factory) ---
def create_app():
    app = Flask(__name__)
    
    app.config['SECRET_KEY'] = SECRET_KEY
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
    
    db.init_app(app)
    login_manager.init_app(app)
    
    admin = Admin(app, name='K Online Admin', template_mode='bootstrap4', index_view=MyAdminIndexView())
    admin.add_view(ProductAdminView(Product, db.session))
    admin.add_view(OrderAdminView(Order, db.session))
    admin.add_view(UserAdminView(User, db.session))

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # --- Login Routes (Admin ဝင်ဖို့) ---
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        form = LoginForm(request.form)
        if request.method == 'POST' and form.validate():
            user = db.session.query(User).filter_by(username=form.username.data).first()
            if user and user.check_password(form.password.data):
                login_user(user)
                return redirect(url_for('admin.index'))
            flash('Invalid username or password')
        return render_template('login.html', form=form)

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

    @app.route('/submit_order', methods=['POST'])
    def submit_order():
        # (ဒါက နောက်တစ်ဆင့်မှ ဆက်လုပ်ပါမယ်)
        return "Order Received (Bot function not yet built)", 200
        
    # --- လျှို့ဝှက် Admin Account ဆောက်မယ့် Link ---
    @app.route('/create_first_admin_123xyz')
    def create_first_admin():
        try:
            user_exists = db.session.query(User).filter_by(username='admin').first()
            if not user_exists:
                u = User(username='admin')
                u.set_password('12345') # Password ကို 12345 လို့ ပေးထားတယ်
                db.session.add(u)
                db.session.commit()
                return "<h1>Admin User (admin) Created Successfully!</h1>"
            else:
                return "<h1>Admin User already exists.</h1>"
        except Exception as e:
            return f"<h1>Error creating admin: {e}</h1>"
            
    print("--- Flask App created successfully with Admin Panel. ---")
    return app

# --- Gunicorn က ဒီ file ကို run ရင် ဒီ create_app() ကို ခေါ်သုံးလိမ့်မယ် ---
app = create_app()

# --- Database Tables တွေကို အလိုအလျောက် ဆောက်ပေးဖို့ ---
with app.app_context():
    db.create_all()

