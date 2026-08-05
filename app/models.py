from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')
    create_time = db.Column(db.DateTime, default=datetime.now)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role == 'admin'

    def __repr__(self):
        return '<User %s>' % self.username


class VegetablePrice(db.Model):
    __tablename__ = 'vegetable_prices'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    category = db.Column(db.String(50), nullable=True)
    price = db.Column(db.Float, nullable=False)
    min_price = db.Column(db.Float, nullable=True)
    max_price = db.Column(db.Float, nullable=True)
    yesterday_price = db.Column(db.Float, nullable=True)
    avg_price_7d = db.Column(db.Float, nullable=True)
    avg_price_20d = db.Column(db.Float, nullable=True)
    update_time = db.Column(db.DateTime, default=datetime.now)
    source_date = db.Column(db.Date, nullable=False, index=True)
    price_history = db.Column(db.JSON, nullable=True)

    def __repr__(self):
        return '<VegetablePrice %s: %.2f>' % (self.name, self.price)


class PriceHistory(db.Model):
    __tablename__ = 'price_history'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    prod_name = db.Column(db.String(100), nullable=False, index=True)  # 改为 prod_name
    price = db.Column(db.Float, nullable=False)
    record_date = db.Column(db.Date, nullable=False, index=True)
    min_price = db.Column(db.Float, nullable=True)
    max_price = db.Column(db.Float, nullable=True)
    place = db.Column(db.String(100), nullable=True)
    unit = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)


class OperationLog(db.Model):
    __tablename__ = 'operation_logs'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    username = db.Column(db.String(50), nullable=True)
    operation_type = db.Column(db.String(50), nullable=False)
    operation_detail = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(50), nullable=True)
    create_time = db.Column(db.DateTime, default=datetime.now, index=True)