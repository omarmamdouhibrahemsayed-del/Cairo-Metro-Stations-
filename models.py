from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

# جدول وسيط لربط المستخدمين بالمحطات المفضلة (Many-to-Many)
user_favorites = db.Table(
    'user_favorites',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('station_id', db.Integer, db.ForeignKey('stations.id'), primary_key=True),
    db.Column('added_at', db.DateTime, default=datetime.utcnow)
)

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    picture = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # علاقة المحطات المفضلة
    favorites = db.relationship('Station', secondary=user_favorites, backref='favorited_by')

class MetroLine(db.Model):
    __tablename__ = 'metro_lines'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)       # مثال: الخط الأول
    route_desc = db.Column(db.String(200), nullable=False) # مثال: حلوان - المرج الجديدة
    color_hex = db.Column(db.String(20), nullable=False)   # لون الخط المميز
    stations = db.relationship('Station', backref='line', lazy=True, order_by='Station.order_index')

class Station(db.Model):
    __tablename__ = 'stations'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    line_id = db.Column(db.Integer, db.ForeignKey('metro_lines.id'), nullable=False)
    order_index = db.Column(db.Integer, nullable=False)    # ترتيب المحطة الفعلي على الخط
    branch = db.Column(db.String(100), default='المسار الرئيسي') # لتمييز تفريعتي الخط الثالث
    is_interchange = db.Column(db.Boolean, default=False)
    interchange_info = db.Column(db.String(250), nullable=True) # تفاصيل التبادل
    station_type = db.Column(db.String(50), default='سطحية')    # نفقية / علوية / سطحية