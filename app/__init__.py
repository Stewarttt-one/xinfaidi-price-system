from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from config import Config
import os

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = '请先登录访问系统'


def create_app(config_class=Config):
    # 获取项目根目录
    project_root = os.path.dirname(os.path.abspath(__file__))  # app目录
    project_root = os.path.dirname(project_root)  # 项目根目录

    template_dir = os.path.join(project_root, 'templates')
    static_dir = os.path.join(project_root, 'static')

    os.makedirs(template_dir, exist_ok=True)
    os.makedirs(static_dir, exist_ok=True)

    app = Flask(__name__,
                template_folder=template_dir,
                static_folder=static_dir,
                static_url_path='/static')
    app.config.from_object(config_class)

    # 初始化扩展
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # 注册蓝图
    from app.auth import auth_bp
    from app.main import main_bp
    from app.admin import admin_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(main_bp, url_prefix='/')
    app.register_blueprint(admin_bp, url_prefix='/admin')

    # 用户加载回调
    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return User.query.get(int(user_id))

    # 上下文处理器
    @app.context_processor
    def inject_user():
        from flask_login import current_user
        return dict(current_user=current_user)

    return app