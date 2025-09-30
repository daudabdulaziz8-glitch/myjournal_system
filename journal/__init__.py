import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

# --- create extension instances at import time ---
db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
csrf = CSRFProtect()


login_manager.login_view = 'journal.login'
login_manager.login_message_category = 'info'


def create_app():
    """Application factory."""
    app = Flask(__name__, instance_relative_config=True)

    # Secret key
    app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "dev_secret_key")

    # Ensure instance/ exists
    os.makedirs(app.instance_path, exist_ok=True)

    # SQLite DB in instance folder
    db_path = os.path.join(app.instance_path, 'database.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Uploads folder
    upload_dir = os.path.join(app.instance_path, 'uploads')
    os.makedirs(upload_dir, exist_ok=True)
    app.config['UPLOAD_FOLDER'] = upload_dir
    app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10 MB

    # init extensions
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    @app.context_processor
    def inject_role_helpers():
        def role_val(user):
            r = getattr(user, "role", None)
            return getattr(r, "value", r)
        return dict(role_val=role_val)

    # Register blueprint
    from .routes import journal_bp
    app.register_blueprint(journal_bp)

    return app
