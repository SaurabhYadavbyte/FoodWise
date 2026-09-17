from app import db
from datetime import date
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class FoodItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(20), nullable=False)
    purchase_date = db.Column(db.Date, nullable=True)
    expiry_date = db.Column(db.Date, nullable=False)
    storage_location = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    @property
    def expiry_status(self):
        if not self.expiry_date:
            return "Unknown"
        today = date.today()
        delta = (self.expiry_date - today).days
        if delta < 0:
            return "Expired"
        elif delta == 0:
            return "Use Today"
        elif delta <= 3:
            return "Use Soon"
        else:
            return "Safe for Now"

class WasteLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    food_name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False, default='Other')
    quantity = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(20), nullable=False)
    date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.String(200), nullable=False)
    disposal_method = db.Column(db.String(100), nullable=False)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

class MealPlan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    plan_date = db.Column(db.Date, nullable=False)
    meal_type = db.Column(db.String(50), nullable=False)
    meal_name = db.Column(db.String(100), nullable=False)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
