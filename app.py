import os
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv

from models import db, User, MetroLine, Station
from seed_data import seed_metro_data

# تحميل متغيرات البيئة من ملف .env
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///cairo_metro.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# تهيئة قاعدة البيانات وإدارة الجلسات
db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'index'
login_manager.login_message = "يرجى تسجيل الدخول بحساب Google للوصول إلى هذه الميزة."
login_manager.login_message_category = "warning"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# إعداد Google OAuth 2.0 باستخدام Authlib
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

# إنشاء الجداول وتعبئة البيانات عند أول تشغيل
with app.app_context():
    db.create_all()
    seed_metro_data()

# --- مسارات المصادقة (Google Auth Routes) ---

@app.route('/login/google')
def login_google():
    redirect_uri = url_for('auth_callback', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/auth/callback')
def auth_callback():
    token = google.authorize_access_token()
    user_info = token.get('userinfo')
    if not user_info:
        flash("فشل تسجيل الدخول عبر Google، حاول مرة أخرى.", "danger")
        return redirect(url_for('index'))

    google_id = user_info['sub']
    user = User.query.filter_by(google_id=google_id).first()

    # إنشاء حساب جديد تلقائياً إذا لم يكن موجوداً
    if not user:
        user = User(
            google_id=google_id,
            name=user_info.get('name', 'مستخدم مترو القاهرة'),
            email=user_info.get('email'),
            picture=user_info.get('picture')
        )
        db.session.add(user)
    else:
        # تحديث الاسم والصورة في حال تغيرهما في جوجل
        user.name = user_info.get('name', user.name)
        user.picture = user_info.get('picture', user.picture)

    db.session.commit()
    login_user(user, remember=True)
    flash(f"أهلاً بك، {user.name}!", "success")
    return redirect(url_for('index'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("تم تسجيل الخروج بنجاح.", "info")
    return redirect(url_for('index'))

# --- مسارات التطبيق الأساسية ---

@app.route('/')
def index():
    search_query = request.args.get('q', '').strip()
    line_filter = request.args.get('line', type=int)
    interchange_only = request.args.get('interchange') == '1'

    lines = MetroLine.query.all()
    query = Station.query

    if search_query:
        query = query.filter(Station.name.contains(search_query))
    if line_filter:
        query = query.filter(Station.line_id == line_filter)
    if interchange_only:
        query = query.filter(Station.is_interchange.is_(True))

    stations = query.order_by(Station.line_id, Station.order_index).all()
    
    # جلب معرفات المحطات المفضلة للمستخدم الحالي لتسهيل عرض أيقونة القلب
    fav_ids = [s.id for s in current_user.favorites] if current_user.is_authenticated else []

    return render_template(
        'index.html',
        lines=lines,
        stations=stations,
        search_query=search_query,
        line_filter=line_filter,
        interchange_only=interchange_only,
        fav_ids=fav_ids
    )

@app.route('/station/<int:station_id>')
def station_detail(station_id):
    station = Station.query.get_or_404(station_id)
    # جلب المحطات السابقة والتالية في نفس الخط
    prev_station = Station.query.filter_by(line_id=station.line_id, order_index=station.order_index - 1).first()
    next_station = Station.query.filter_by(line_id=station.line_id, order_index=station.order_index + 1).first()
    
    # التحقق مما إذا كانت المحطة مشتركة مع خط آخر بنفس الاسم
    same_name_stations = Station.query.filter(Station.name == station.name, Station.id != station.id).all()
    
    is_fav = current_user.is_authenticated and (station in current_user.favorites)
    return render_template(
        'station_detail.html',
        station=station,
        prev_station=prev_station,
        next_station=next_station,
        same_name_stations=same_name_stations,
        is_fav=is_fav
    )

# --- مسارات محمية للمستخدمين المسجلين فقط ---

@app.route('/favorites')
@login_required
def favorites():
    return render_template('favorites.html', stations=current_user.favorites)

@app.route('/favorite/toggle/<int:station_id>', methods=['POST'])
@login_required
def toggle_favorite(station_id):
    station = Station.query.get_or_404(station_id)
    if station in current_user.favorites:
        current_user.favorites.remove(station)
        flash(f"تمت إزالة محطة ({station.name}) من المفضلة.", "info")
    else:
        current_user.favorites.append(station)
        flash(f"تمت إضافة محطة ({station.name}) إلى المفضلة.", "success")
    db.session.commit()
    return redirect(request.referrer or url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)