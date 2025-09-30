import os
from functools import wraps
from datetime import datetime
from flask import (
    Blueprint, render_template, redirect, url_for, flash, request, abort,
    current_app, send_from_directory
)
from werkzeug.utils import secure_filename
from flask_login import login_user, logout_user, login_required, current_user
from . import db, bcrypt
from .models import User, Submission, Review, Role, SubmissionStatus, ReviewDecision

journal_bp = Blueprint(
    "journal",
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/journal/static"
)

# -----------------------------
# Context Processor (adds year everywhere)
# -----------------------------
@journal_bp.app_context_processor
def inject_now():
    return {"year": datetime.utcnow().year}

# -----------------------------
# Helpers
# -----------------------------
def _pdf_filename(submission_id: int) -> str:
    return f"submission_{submission_id}.pdf"

def _current_role_name(user) -> str:
    raw = getattr(user, "role", None)
    return getattr(raw, "value", raw) if raw is not None else ""


def role_required(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("journal.login", next=request.url))

            # Normalize the user’s role to uppercase string
            user_role = getattr(current_user, "role", "")
            if hasattr(user_role, "value"):  # Enum
                user_role = user_role.value
            user_role = str(user_role).upper()

            # Normalize allowed roles too
            allowed = [
                r.value.upper() if hasattr(r, "value") else str(r).upper()
                for r in roles
            ]

            if user_role not in allowed:
                abort(403)

            return fn(*args, **kwargs)
        return wrapper
    return decorator


# -----------------------------
# Public / Auth
# -----------------------------
@journal_bp.route("/")
def home():
    recent = Submission.query.order_by(Submission.created_at.desc()).limit(5).all()
    stats = {
        "total_submissions": Submission.query.count(),
        "accepted": Submission.query.filter_by(status=SubmissionStatus.ACCEPTED).count(),
        "under_review": Submission.query.filter_by(status=SubmissionStatus.UNDER_REVIEW).count(),
        "reviewers": User.query.filter_by(role="REVIEWER").count()
    }
    return render_template("landing.html", recent=recent, stats=stats)

@journal_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("journal.dashboard"))

    from .forms import RegistrationForm
    form = RegistrationForm()

    if form.validate_on_submit():
        exists = User.query.filter(
            (User.username == form.username.data) | (User.email == form.email.data)
        ).first()
        if exists:
            flash("Username or Email already exists.", "danger")
            return render_template("register.html", form=form)

        hashed = bcrypt.generate_password_hash(form.password.data).decode("utf-8")
        user = User(
            username=form.username.data,
            email=form.email.data,
            department=form.department.data,
            password=hashed,
            role=Role.AUTHOR   # ✅ default role as Enum
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

    from .forms import LoginForm
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
    flash("You have been logged out.", "info")
    return redirect(url_for("journal.login"))

# -----------------------------
# Author dashboard & submission
# -----------------------------
@journal_bp.route("/dashboard")
@login_required
def dashboard():
    my_subs = (
        Submission.query.filter_by(author_id=current_user.id)
        .order_by(Submission.created_at.desc())
        .all()
    )
    return render_template("dashboard.html", submissions=my_subs)

@journal_bp.route("/submit", methods=["GET", "POST"])
@login_required
def submit():
    from .forms import SubmissionForm
    from .models import Role  # make sure Role is imported at the top of routes.py

    # ✅ Only allow authors
    if _current_role_name(current_user).upper() != "AUTHOR":
        flash("Only authors can submit manuscripts.", "danger")
        return redirect(url_for("journal.dashboard"))

    form = SubmissionForm()

    if form.validate_on_submit():
        file = form.pdf_file.data
        if not file:
            flash("You must upload a PDF file.", "danger")
            return render_template("submit.html", form=form)

        # ✅ Create new submission record
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

        # ✅ Save PDF file using submission ID
        pdf_name = _pdf_filename(s.id)
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], pdf_name)
        try:
            file.save(file_path)
            flash("Submission created and PDF uploaded successfully!", "success")
        except Exception as e:
            flash(f"Error saving file: {e}", "danger")

        return redirect(url_for("journal.dashboard"))

    # ✅ Debugging: print form errors in console
    if form.errors:
        print("DEBUG: Submission form errors ->", form.errors)

    return render_template("submit.html", form=form)

@journal_bp.route("/submission/<int:submission_id>")
@login_required
def submission_detail(submission_id):
    sub = Submission.query.get_or_404(submission_id)
    reviews = Review.query.filter_by(submission_id=sub.id).all()

    # Only author, assigned reviewer, or admin can view
    is_admin = _current_role_name(current_user).upper() == "ADMIN"
    is_reviewer = sub.assigned_reviewer_id == current_user.id
    is_author = sub.author_id == current_user.id
    if not (is_admin or is_reviewer or is_author):
        abort(403)

    return render_template("submission_detail.html", submission=sub, reviews=reviews)
@journal_bp.route("/submissions")
@login_required
def submissions():
    my_subs = (
        Submission.query.filter_by(author_id=current_user.id)
        .order_by(Submission.created_at.desc())
        .all()
    )
    return render_template("submissions.html", submissions=my_subs)
# -----------------------------
# Admin
# -----------------------------
@journal_bp.route("/admin/submissions")
@login_required
@role_required("ADMIN")
def admin_submissions():
    all_subs = Submission.query.order_by(Submission.created_at.desc()).all()
    reviewers = [u for u in User.query.all() if _current_role_name(u).upper() == "REVIEWER"]
    return render_template("admin_submissions.html", submissions=all_subs, reviewers=reviewers)

@journal_bp.route("/admin/assign", methods=["POST"])
@login_required
@role_required("ADMIN")
def assign_reviewer():
    sub_id = request.form.get("submission_id")
    reviewer_id = request.form.get("reviewer_id")

    sub = Submission.query.get_or_404(sub_id)
    reviewer = User.query.get_or_404(reviewer_id)

    sub.assigned_reviewer_id = reviewer.id
    sub.status = SubmissionStatus.UNDER_REVIEW
    db.session.commit()

    flash(f"Reviewer {reviewer.username} assigned.", "success")
    return redirect(url_for("journal.admin_submissions"))

@journal_bp.route("/admin/users")
@login_required
@role_required("ADMIN")
def admin_users():
    all_users = User.query.order_by(User.username.asc()).all()
    return render_template("admin_users.html", users=all_users)

@journal_bp.route("/admin/users/update_role", methods=["POST"])
@login_required
@role_required("ADMIN")
def update_user_role():
    user_id = request.form.get("user_id")
    new_role = request.form.get("role")

    user = User.query.get_or_404(user_id)
    user.role = new_role.upper()
    db.session.commit()

    flash(f"Role for {user.username} updated to {new_role}.", "success")
    return redirect(url_for("journal.admin_users"))

# -----------------------------
# Reviewer
# -----------------------------
@journal_bp.route("/reviewer/queue")
@login_required
@role_required("REVIEWER")
def reviewer_queue():
    queue = (
        Submission.query.filter_by(assigned_reviewer_id=current_user.id)
        .order_by(Submission.created_at.desc())
        .all()
    )
    return render_template("review_queue.html", submissions=queue)

@journal_bp.route("/reviewer/review/<int:submission_id>", methods=["GET", "POST"])
@login_required
@role_required("REVIEWER")
def review_submission(submission_id):
    sub = Submission.query.get_or_404(submission_id)
    if sub.assigned_reviewer_id != current_user.id:
        abort(403)

    from .forms import ReviewForm
    form = ReviewForm()

    if form.validate_on_submit():
        review = Review(
            submission_id=sub.id,
            reviewer_id=current_user.id,
            comment=form.comment.data,
            score=form.score.data,
            decision=ReviewDecision[form.decision.data]  # ✅ safe enum lookup
        )

        if review.decision == ReviewDecision.ACCEPT:
            sub.status = SubmissionStatus.ACCEPTED
        elif review.decision == ReviewDecision.REJECT:
            sub.status = SubmissionStatus.REJECTED
        else:
            sub.status = SubmissionStatus.UNDER_REVIEW

        db.session.add(review)
        db.session.commit()
        flash("Review submitted.", "success")
        return redirect(url_for("journal.reviewer_queue"))

    return render_template("review_form.html", form=form, submission=sub)

# -----------------------------
# Download Submission PDF
# -----------------------------
@journal_bp.route('/submission/<int:submission_id>/download')
@login_required
def download_submission(submission_id):
    s = Submission.query.get_or_404(submission_id)

    is_admin = str(current_user.role).upper() == "ADMIN"
    is_reviewer = s.assigned_reviewer_id and s.assigned_reviewer_id == current_user.id
    is_author = s.author_id == current_user.id
    if not (is_admin or is_reviewer or is_author):
        abort(403)

    filename = _pdf_filename(s.id)
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)

    if not os.path.exists(file_path):
        flash('No manuscript uploaded for this submission.', 'warning')
        if is_admin:
            return redirect(url_for('journal.admin_submissions'))
        if str(current_user.role).upper() == "REVIEWER":
            return redirect(url_for('journal.reviewer_queue'))
        return redirect(url_for('journal.dashboard'))

    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename, as_attachment=True)
@journal_bp.route("/test-css")
def test_css():
    return """
    <!DOCTYPE html>
    <html>
    <head>
      <link rel="stylesheet" href='""" + url_for('static', filename='css/style.css') + """'>
    </head>
    <body>
      <h1>CSS Test Page</h1>
      <p>If this text is styled (blue links, background color, navbar styles), then CSS is working.</p>
      <a href="#">Test Link</a>
    </body>
    </html>
    """
