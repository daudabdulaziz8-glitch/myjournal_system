# journal/__init__.py
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect, generate_csrf
try:
    from flask_migrate import Migrate
except Exception:
    Migrate = None

db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
csrf = CSRFProtect()

login_manager.login_view = 'journal.login'
login_manager.login_message_category = 'info'

def create_app(config: dict | None = None):
    # allow instance/ folder (database, uploads)
    app = Flask(__name__, instance_relative_config=True)

    # Allow callers to override config (tests pass in-memory DB, etc.)
    if config:
        app.config.update(config)

    # ---- core config ----
    # SECRET_KEY handling:
    # - Use the environment variable when provided.
    # - Allow a dev fallback only when TESTING is True or ALLOW_DEV_SECRET=1 is set.
    # - In production-like runs, raise a helpful error to force setting a secret.
    secret = os.getenv('SECRET_KEY')
    if not secret:
        if app.config.get('TESTING') or os.getenv('ALLOW_DEV_SECRET') == '1':
            secret = 'dev_secret_key_change_me'
        else:
            raise RuntimeError(
                'SECRET_KEY environment variable is required. For development you can set ALLOW_DEV_SECRET=1 or set SECRET_KEY.'
            )
    app.config['SECRET_KEY'] = secret
    # Also set the WSGI secret key attribute used by sessions
    app.secret_key = app.config['SECRET_KEY']
    # Ensure Flask-WTF has a CSRF secret key as well
    app.config.setdefault('WTF_CSRF_SECRET_KEY', app.config['SECRET_KEY'])
    os.makedirs(app.instance_path, exist_ok=True)

    # sqlite db inside instance/ (only set if caller didn't override)
    if not app.config.get('SQLALCHEMY_DATABASE_URI'):
        db_path = os.path.join(app.instance_path, 'database.db')
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config.setdefault('SQLALCHEMY_TRACK_MODIFICATIONS', False)

    # uploads
    upload_dir = os.path.join(app.instance_path, 'uploads')
    os.makedirs(upload_dir, exist_ok=True)
    app.config['UPLOAD_FOLDER'] = upload_dir
    app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB

    # ---- init extensions ----
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    # Optionally initialize Flask-Migrate if available in the environment
    if Migrate is not None:
        migrate = Migrate()
        migrate.init_app(app, db)

    # expose csrf_token() to ALL templates (for non-WTForms forms)
    @app.context_processor
    def inject_csrf():
        return dict(csrf_token=generate_csrf)

    # ---- blueprints ----
    from .routes import journal_bp
    app.register_blueprint(journal_bp)

    return app
