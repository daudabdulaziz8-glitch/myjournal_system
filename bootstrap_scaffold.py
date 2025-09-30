# bootstrap_scaffold.py
import os, textwrap

ROOT = os.path.abspath(os.path.dirname(__file__))
def p(*parts): return os.path.join(ROOT, *parts)

# --- directories ---
dirs = [
    "instance",
    "journal",
    "journal/templates",
    "journal/static",
]
for d in dirs:
    os.makedirs(p(d), exist_ok=True)

# --- files with minimal content if not present ---
files = {
    "app.py": textwrap.dedent("""\
        from journal import create_app
        app = create_app()

        if __name__ == "__main__":
            app.run(debug=True)
    """),

    "requirements.txt": textwrap.dedent("""\
        Flask
        Flask-Login
        Flask-Bcrypt
        Flask-WTF
        Flask-SQLAlchemy
        python-dotenv
    """),

    "journal/__init__.py": textwrap.dedent("""\
        import os
        from flask import Flask
        from flask_sqlalchemy import SQLAlchemy
        from flask_bcrypt import Bcrypt
        from flask_login import LoginManager
        from flask_wtf.csrf import CSRFProtect

        db = SQLAlchemy()
        bcrypt = Bcrypt()
        login_manager = LoginManager()
        csrf = CSRFProtect()

        login_manager.login_view = 'journal.login'
        login_manager.login_message_category = 'info'

        def create_app():
            app = Flask(__name__, instance_relative_config=True)

            # secret + instance
            app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev_secret_key')
            os.makedirs(app.instance_path, exist_ok=True)

            # sqlite in instance/
            db_path = os.path.join(app.instance_path, 'database.db')
            app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
            app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

            # uploads (used later)
            up = os.path.join(app.instance_path, 'uploads')
            os.makedirs(up, exist_ok=True)
            app.config['UPLOAD_FOLDER'] = up
            app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10 MB

            db.init_app(app)
            bcrypt.init_app(app)
            login_manager.init_app(app)
            csrf.init_app(app)

            from .routes import journal_bp
            app.register_blueprint(journal_bp)

            return app
    """),

    # Minimal models so db.create_all() won’t explode
    "journal/models.py": textwrap.dedent("""\
        from datetime import datetime
        from flask_login import UserMixin
        from . import db, login_manager
        import enum

        @login_manager.user_loader
        def load_user(user_id):
            return User.query.get(int(user_id))

        class SubmissionStatus(enum.Enum):
            PENDING = "pending"
            UNDER_REVIEW = "under_review"
            ACCEPTED = "accepted"
            REJECTED = "rejected"

        class User(db.Model, UserMixin):
            id = db.Column(db.Integer, primary_key=True)
            username = db.Column(db.String(50), unique=True, nullable=False)
            email = db.Column(db.String(120), unique=True, nullable=False)
            password = db.Column(db.String(255), nullable=False)
            role = db.Column(db.String(20), default='author')  # 'author'|'reviewer'|'admin'
            department = db.Column(db.String(100))
            submissions = db.relationship('Submission', backref='author', lazy=True, foreign_keys='Submission.author_id')

        class Submission(db.Model):
            id = db.Column(db.Integer, primary_key=True)
            title = db.Column(db.String(200), nullable=False)
            abstract = db.Column(db.Text, nullable=False)
            keywords = db.Column(db.String(200))
            authors_text = db.Column(db.String(255))
            department = db.Column(db.String(100))
            status = db.Column(db.Enum(SubmissionStatus), default=SubmissionStatus.PENDING, nullable=False)
            created_at = db.Column(db.DateTime, default=datetime.utcnow)

            author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
            assigned_reviewer_id = db.Column(db.Integer, db.ForeignKey('user.id'))

            assigned_reviewer = db.relationship('User', foreign_keys=[assigned_reviewer_id])
    """),

    "journal/forms.py": textwrap.dedent("""\
        from flask_wtf import FlaskForm
        from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField, SelectField, IntegerField
        from wtforms.validators import DataRequired, Length, Email, EqualTo, NumberRange
        from flask_wtf.file import FileField, FileAllowed

        DEPARTMENTS = [
            ("Mathematics", "Mathematics"),
            ("Computer Science", "Computer Science"),
            ("Statistics", "Statistics"),
            ("Other", "Other"),
        ]

        class RegistrationForm(FlaskForm):
            username = StringField('Username', validators=[DataRequired(), Length(min=3, max=50)])
            email = StringField('Email', validators=[DataRequired(), Email()])
            department = SelectField('Department', choices=DEPARTMENTS)
            password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
            confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
            submit = SubmitField('Create Account')

        class LoginForm(FlaskForm):
            email = StringField('Email', validators=[DataRequired(), Email()])
            password = PasswordField('Password', validators=[DataRequired()])
            remember = BooleanField('Remember Me')
            submit = SubmitField('Login')

        class SubmissionForm(FlaskForm):
            title = StringField('Title', validators=[DataRequired(), Length(min=4, max=200)])
            abstract = TextAreaField('Abstract', validators=[DataRequired(), Length(min=20)])
            keywords = StringField('Keywords (comma-separated)')
            authors_text = StringField('Co-authors (optional)')
            department = SelectField('Department', choices=DEPARTMENTS)
            manuscript = FileField('PDF Manuscript (optional)', validators=[FileAllowed(['pdf'], 'PDFs only')])
            submit = SubmitField('Submit')

        class ReviewForm(FlaskForm):
            comment = TextAreaField('Reviewer Comments', validators=[DataRequired(), Length(min=10)])
            score = IntegerField('Score (1-5)', validators=[NumberRange(min=1, max=5)], default=5)
            decision = SelectField('Decision', choices=[
                ("accept", "Accept"),
                ("minor_revision", "Minor Revision"),
                ("major_revision", "Major Revision"),
                ("reject", "Reject")
            ], validators=[DataRequired()])
            submit = SubmitField('Submit Review')
    """),

    "journal/routes.py": textwrap.dedent("""\
        from functools import wraps
        from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, current_app, send_from_directory
        from flask_login import login_user, logout_user, login_required, current_user
        from werkzeug.utils import secure_filename
        import os

        from . import db, bcrypt
        from .models import User, Submission, SubmissionStatus
        from .forms import RegistrationForm, LoginForm, SubmissionForm

        journal_bp = Blueprint("journal", __name__, template_folder="templates", static_folder="static")

        def role_required(*roles):
            def decorator(fn):
                @wraps(fn)
                def wrapper(*args, **kwargs):
                    if not current_user.is_authenticated:
                        return redirect(url_for("journal.login", next=request.url))
                    if getattr(current_user, "role", None) not in roles:
                        abort(403)
                    return fn(*args, **kwargs)
                return wrapper
            return decorator

        @journal_bp.route("/", endpoint="home")
        def home_view():
            return render_template("base.html")

        @journal_bp.route("/register", methods=["GET", "POST"])
        def register():
            if current_user.is_authenticated:
                return redirect(url_for("journal.dashboard"))
            form = RegistrationForm()
            if form.validate_on_submit():
                exists = User.query.filter((User.username == form.username.data) | (User.email == form.email.data)).first()
                if exists:
                    flash("Username or Email already exists.", "danger")
                    return render_template("register.html", form=form)
                user = User(
                    username=form.username.data,
                    email=form.email.data,
                    department=form.department.data,
                    password=bcrypt.generate_password_hash(form.password.data).decode("utf-8"),
                    role="author",
                )
                db.session.add(user)
                db.session.commit()
                flash("Account created! Please log in.", "success")
                return redirect(url_for("journal.login"))
            return render_template("register.html", form=form)

        @journal_bp.route("/login", methods=["GET", "POST"])
        def login():
            if current_user.is_authenticated:
                return redirect(url_for("journal.dashboard"))
            form = LoginForm()
            if form.validate_on_submit():
                user = User.query.filter_by(email=form.email.data).first()
                if user and bcrypt.check_password_hash(user.password, form.password.data):
                    login_user(user, remember=form.remember.data)
                    flash("Logged in successfully!", "success")
                    return redirect(request.args.get("next") or url_for("journal.dashboard"))
                flash("Invalid email or password", "danger")
            return render_template("login.html", form=form)

        @journal_bp.route("/logout")
        def logout():
            logout_user()
            flash("Logged out.", "info")
            return redirect(url_for("journal.login"))

        @journal_bp.route("/dashboard")
        @login_required
        def dashboard():
            subs = Submission.query.filter_by(author_id=current_user.id).order_by(Submission.created_at.desc()).all()
            return render_template("dashboard.html", submissions=subs)

        def _pdf_filename(submission_id: int) -> str:
            return f"submission_{submission_id}.pdf"

        @journal_bp.route("/submit", methods=["GET", "POST"])
        @login_required
        def submit():
            if current_user.role != "author":
                abort(403)
            form = SubmissionForm()
            if request.method == "GET" and getattr(current_user, "department", None):
                form.department.data = current_user.department
            if form.validate_on_submit():
                s = Submission(
                    title=form.title.data,
                    abstract=form.abstract.data,
                    keywords=form.keywords.data,
                    authors_text=form.authors_text.data,
                    department=form.department.data,
                    author_id=current_user.id,
                    status=SubmissionStatus.PENDING,
                )
                db.session.add(s)
                db.session.commit()

                if form.manuscript.data:
                    pdf = form.manuscript.data
                    filename = secure_filename(_pdf_filename(s.id))
                    save_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
                    try:
                        pdf.stream.seek(0)
                        pdf.save(save_path)
                        flash("Submission created with manuscript attached.", "success")
                    except Exception as e:
                        flash(f"Submission saved, but file upload failed: {e}", "danger")
                else:
                    flash("Submission created! Pending assignment.", "success")
                return redirect(url_for("journal.dashboard"))
            return render_template("submit.html", form=form)

        @journal_bp.route("/submission/<int:submission_id>/download")
        @login_required
        def download_submission(submission_id):
            s = Submission.query.get_or_404(submission_id)
            # Only the author can download in this minimal bootstrap
            if s.author_id != current_user.id and current_user.role not in ("admin", "reviewer"):
                abort(403)
            filename = _pdf_filename(s.id)
            path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
            if not os.path.exists(path):
                flash("No manuscript uploaded for this submission.", "warning")
                return redirect(url_for("journal.dashboard"))
            return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename, as_attachment=True)
    """),

    "journal/templates/base.html": textwrap.dedent("""\
        <!doctype html>
        <html lang="en">
        <head>
          <meta charset="utf-8" />
          <meta name="viewport" content="width=device-width, initial-scale=1" />
          <title>Faculty Journal System</title>
          <link rel="stylesheet" href="{{ url_for('journal.static', filename='styles.css') }}">
        </head>
        <body>
          <nav class="nav">
            <a href="{{ url_for('journal.home') }}" class="brand">FMCS JournalSys</a>
            <div class="links">
              {% if current_user.is_authenticated %}
                <a href="{{ url_for('journal.dashboard') }}">Dashboard</a>
                {% if current_user.role == 'author' %}
                  <a href="{{ url_for('journal.submit') }}">New Submission</a>
                {% endif %}
                <a href="{{ url_for('journal.logout') }}">Logout</a>
              {% else %}
                <a href="{{ url_for('journal.login') }}">Login</a>
                <a href="{{ url_for('journal.register') }}">Register</a>
              {% endif %}
            </div>
          </nav>
          <main class="container">
            {% with messages = get_flashed_messages(with_categories=true) %}
              {% if messages %}
                <ul class="flashes">
                  {% for category, message in messages %}
                    <li class="flash {{ category }}">{{ message }}</li>
                  {% endfor %}
                </ul>
              {% endif %}
            {% endwith %}

            {% block body %}
              {% if current_user.is_authenticated %}
                <h2>Welcome, {{ current_user.username }}!</h2>
              {% else %}
                <h2>Faculty Journal Submission System</h2>
                <p>Submit and track manuscripts for the Faculty of Mathematics & Computer Science.</p>
              {% endif %}
            {% endblock %}
          </main>
        </body>
        </html>
    """),

    "journal/templates/register.html": textwrap.dedent("""\
        {% extends 'base.html' %}
        {% block body %}
        <main class="container">
          <h3>Create Account</h3>
          <form method="POST">
            {{ form.hidden_tag() }}
            <label>{{ form.username.label }} {{ form.username(class_='input') }}</label>
            <label>{{ form.email.label }} {{ form.email(class_='input') }}</label>
            <label>{{ form.department.label }} {{ form.department(class_='input') }}</label>
            <label>{{ form.password.label }} {{ form.password(class_='input') }}</label>
            <label>{{ form.confirm_password.label }} {{ form.confirm_password(class_='input') }}</label>
            {{ form.submit(class_='btn') }}
          </form>
          <p>Already have an account? <a href="{{ url_for('journal.login') }}">Login</a></p>
        </main>
        {% endblock %}
    """),

    "journal/templates/login.html": textwrap.dedent("""\
        {% extends 'base.html' %}
        {% block body %}
        <main class="container">
          <h3>Login</h3>
          <form method="POST">
            {{ form.hidden_tag() }}
            <label>{{ form.email.label }} {{ form.email(class_='input') }}</label>
            <label>{{ form.password.label }} {{ form.password(class_='input') }}</label>
            <label class="check">{{ form.remember() }} Remember me</label>
            {{ form.submit(class_='btn') }}
          </form>
          <p>No account? <a href="{{ url_for('journal.register') }}">Register</a></p>
        </main>
        {% endblock %}
    """),

    "journal/templates/dashboard.html": textwrap.dedent("""\
        {% extends 'base.html' %}
        {% block body %}
        <main class="container">
          <h3>Your Submissions</h3>
          {% if current_user.role == 'author' %}
            <p><a class="btn" href="{{ url_for('journal.submit') }}">➕ New Submission</a></p>
          {% endif %}

          {% if submissions %}
            <ul class="list">
              {% for s in submissions %}
                <li>
                  <strong>{{ s.title }}</strong>
                  <div class="muted">{{ s.created_at.strftime('%Y-%m-%d %H:%M') }} · Status: {{ s.status.value.replace('_',' ') }}</div>
                  <p><em>Keywords:</em> {{ s.keywords or '—' }}</p>
                  <p>{{ s.abstract[:160] }}{% if s.abstract|length > 160 %}...{% endif %}</p>
                  <p><a class="btn" href="{{ url_for('journal.download_submission', submission_id=s.id) }}">⬇ Download PDF</a></p>
                </li>
              {% endfor %}
            </ul>
          {% else %}
            <p>No submissions yet. Create your first one.</p>
          {% endif %}
        </main>
        {% endblock %}
    """),

    "journal/templates/submit.html": textwrap.dedent("""\
        {% extends 'base.html' %}
        {% block body %}
        <main class="container">
          <h3>New Submission</h3>
          <form method="POST" enctype="multipart/form-data">
            {{ form.hidden_tag() }}
            <label>{{ form.title.label }} {{ form.title(class_='input') }}</label>
            <label>{{ form.abstract.label }} {{ form.abstract(class_='input', rows=6) }}</label>
            <label>{{ form.keywords.label }} {{ form.keywords(class_='input') }}</label>
            <label>{{ form.authors_text.label }} {{ form.authors_text(class_='input') }}</label>
            <label>{{ form.department.label }} {{ form.department(class_='input') }}</label>
            <label>{{ form.manuscript.label }} {{ form.manuscript(class_='input', accept='application/pdf') }}</label>
            {{ form.submit(class_='btn') }}
          </form>
        </main>
        {% endblock %}
    """),

    "journal/static/styles.css": textwrap.dedent("""\
        body { font-family: system-ui, Arial, sans-serif; margin:0; color:#222; }
        .nav { display:flex; align-items:center; justify-content:space-between; padding:12px 16px; background:#0b3d91; color:#fff; }
        .nav a { color:#fff; margin-right:12px; text-decoration:none; }
        .nav .brand { font-weight:700; }
        .container { max-width:900px; margin:24px auto; padding:0 16px; }
        .btn { display:inline-block; padding:8px 12px; border:1px solid #0b3d91; border-radius:8px; text-decoration:none; cursor:pointer; }
        .input, textarea.input, select.input { width:100%; padding:8px; margin:4px 0 12px; }
        .list { list-style:none; padding:0; }
        .list li { padding:12px 0; border-bottom:1px solid #eee; }
        .muted { color:#666; font-size:.9rem; }
        .flashes { list-style:none; padding:0; }
        .flash { padding:8px 12px; border-radius:6px; margin:8px 0; }
        .flash.success { background:#e8f7ee; border:1px solid #8ad2a5; }
        .flash.info { background:#eef3ff; border:1px solid #9bb6ff; }
        .flash.danger { background:#ffecec; border:1px solid #ffc2c2; }
        .flash.warning { background:#fff8e1; border:1px solid #ffd54f; }
    """),
}

for rel, content in files.items():
    abs_path = p(rel)
    if not os.path.exists(abs_path):
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"✔ created {rel}")
    else:
        print(f"• kept existing {rel} (not overwritten)")

print("✅ Scaffold ensured. Next:")
print("1) pip install -r requirements.txt")
print("2) python -c \"from journal import create_app, db; app=create_app(); app.app_context().push(); db.create_all(); print('DB ready')\"")
print("3) python app.py")
