# journal/routes.py
import os
from functools import wraps
from datetime import datetime

from flask import (
    Blueprint, render_template, redirect, url_for, flash,
    request, abort, current_app, send_from_directory
)
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename

from . import db, bcrypt
from .models import (
    User,
    Submission,
    Review,
    Role,
    SubmissionStatus,
    ReviewDecision,
    Issue,
    SubmissionFile,
)

from .forms import RegistrationForm, LoginForm, SubmissionForm, ReviewForm
from sqlalchemy import or_


# Optional mail helper; if unavailable, send_email() is a no-op
try:
    from .mailer import send_email
except Exception:
    def send_email(*args, **kwargs):  # pylint: disable=unused-argument
        return False

journal_bp = Blueprint(
    "journal",
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/static",
)

# ---------- helpers ----------
def role_required(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("journal.login", next=request.url))
            allowed = [r.value if hasattr(r, "value") else r for r in roles]
            if current_user.role.value not in allowed:
                abort(403)
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def _pdf_filename(submission_id: int, version: int | None = None) -> str:
    return f"submission_{submission_id}.pdf" if not version else f"submission_{submission_id}_v{version}.pdf"


# ---------- public ----------
@journal_bp.route('/')
def home():
    # quick stats
    stats = {
        "submissions": Submission.query.count(),
        "accepted": Submission.query.filter_by(status=SubmissionStatus.ACCEPTED).count(),
        "reviewers": User.query.filter_by(role=Role.REVIEWER).count(),
        "departments": db.session.query(Submission.department)
                                 .filter(Submission.department.isnot(None))
                                 .distinct()
                                 .count(),
    }
    # recent feed (latest 5 of anything)
    recent = (Submission.query
              .order_by(Submission.created_at.desc())
              .limit(5).all())

    # FEATURED: show latest accepted (or fall back to latest overall)
    featured = (Submission.query
                .filter(Submission.status == SubmissionStatus.ACCEPTED)
                .order_by(Submission.created_at.desc())
                .limit(8).all())
    if not featured:
        featured = (Submission.query
                    .order_by(Submission.created_at.desc())
                    .limit(8).all())

    return render_template("landing.html", stats=stats, recent=recent, featured=featured)


@journal_bp.route("/issues")
def issues():
    issues = Issue.query.order_by(Issue.published_at.desc()).all()
    return render_template("issues.html", issues=issues)


# ---------- auth ----------
@journal_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("journal.dashboard"))

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
            role=Role.AUTHOR,
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
    flash("You have been logged out.", "info")
    return redirect(url_for("journal.login"))


# ---------- author ----------
@journal_bp.route("/dashboard")
@login_required
def dashboard():
    my_subs = (Submission.query
               .filter_by(author_id=current_user.id)
               .order_by(Submission.created_at.desc())
               .all())
    return render_template("dashboard.html", submissions=my_subs)


@journal_bp.route("/submit", methods=["GET", "POST"])
@login_required
def submit():
    form = SubmissionForm()
    if request.method == "GET" and getattr(current_user, "department", None):
        form.department.data = current_user.department

    if form.validate_on_submit():
        # 1) create submission
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
        db.session.commit()  # s.id now available

        # 2) optional: save PDF as version 1 AND create SubmissionFile row
        if hasattr(form, "manuscript") and form.manuscript.data:
            v = 1
            filename = secure_filename(_pdf_filename(s.id, v))
            dest = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
            try:
                form.manuscript.data.stream.seek(0)
                form.manuscript.data.save(dest)

                sf = SubmissionFile(
                    submission_id=s.id,
                    version=v,
                    filename=filename,
                    note="Initial submission",
                    uploaded_by_user_id=current_user.id,
                )
                db.session.add(sf)
                db.session.commit()
                flash("Submission created with manuscript v1.", "success")
            except Exception as e:
                flash(f"Submission saved, but file upload failed: {e}", "danger")
        else:
            flash("Submission created! Pending assignment.", "success")

        return redirect(url_for("journal.dashboard"))

    return render_template("submit.html", form=form)


@journal_bp.route("/submissions")
@login_required
def submissions():
    my_subs = (Submission.query
               .filter_by(author_id=current_user.id)
               .order_by(Submission.created_at.desc())
               .all())
    return render_template("submissions.html", submissions=my_subs)


@journal_bp.route("/submission/<int:submission_id>")
@login_required
def submission_detail(submission_id: int):
    """
    Simple detail page showing latest file (if any).
    """
    s = Submission.query.get_or_404(submission_id)
    allowed = (
        s.author_id == current_user.id
        or (s.assigned_reviewer_id and s.assigned_reviewer_id == current_user.id)
        or current_user.role == Role.ADMIN
    )
    if not allowed:
        abort(403)

    return render_template("submission_detail.html", submission=s)


@journal_bp.route("/submission/<int:submission_id>/download")
@login_required
def download_submission(submission_id: int):
    """
    Download the latest version (if any).
    """
    s = Submission.query.get_or_404(submission_id)
    allowed = (
        s.author_id == current_user.id
        or (s.assigned_reviewer_id and s.assigned_reviewer_id == current_user.id)
        or current_user.role == Role.ADMIN
    )
    if not allowed:
        abort(403)

    latest = s.files[0] if s.files else None
    if not latest:
        flash("No manuscript uploaded for this submission.", "warning")
        # sensible redirect
        if current_user.role == Role.ADMIN:
            return redirect(url_for("journal.admin_submissions"))
        if current_user.role == Role.REVIEWER:
            return redirect(url_for("journal.reviewer_queue"))
        return redirect(url_for("journal.dashboard"))

    return send_from_directory(current_app.config["UPLOAD_FOLDER"], latest.filename, as_attachment=True)


@journal_bp.route("/submission/<int:submission_id>/file/<int:file_id>/download")
@login_required
def download_specific_file(submission_id: int, file_id: int):
    s = Submission.query.get_or_404(submission_id)
    f = SubmissionFile.query.get_or_404(file_id)
    if f.submission_id != s.id:
        abort(404)

    allowed = (
        s.author_id == current_user.id
        or (s.assigned_reviewer_id and s.assigned_reviewer_id == current_user.id)
        or current_user.role == Role.ADMIN
    )
    if not allowed:
        abort(403)

    return send_from_directory(current_app.config["UPLOAD_FOLDER"], f.filename, as_attachment=True)


# ---------- admin ----------
@journal_bp.route("/admin/submissions")
@login_required
@role_required(Role.ADMIN)
def admin_submissions():
    all_subs = Submission.query.order_by(Submission.created_at.desc()).all()
    reviewers = User.query.filter_by(role=Role.REVIEWER).all()
    return render_template("admin_submissions.html", submissions=all_subs, reviewers=reviewers)


@journal_bp.route("/admin/assign", methods=["POST"])
@login_required
@role_required(Role.ADMIN)
def assign_reviewer():
    sub_id = request.form.get("submission_id", type=int)
    reviewer_id = request.form.get("reviewer_id", type=int)
    sub = Submission.query.get_or_404(sub_id)
    reviewer = User.query.get_or_404(reviewer_id)

    sub.assigned_reviewer_id = reviewer.id
    sub.status = SubmissionStatus.UNDER_REVIEW
    db.session.commit()

    # notify reviewer (optional; no-op if mail not configured)
    send_email(
        to=reviewer.email,
        subject="[FACOMS] New Review Assignment",
        template_name="email/test.html",
        now=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    )

    flash(f"Reviewer {reviewer.username} assigned.", "success")
    return redirect(url_for("journal.admin_submissions"))


@journal_bp.route("/admin/email-test", methods=["POST"])
@login_required
@role_required(Role.ADMIN)
def admin_email_test():
    """
    Stub so your template action doesn't 404. Will send if mail is wired,
    otherwise flashes a dev message.
    """
    to = request.form.get("to") or current_user.email
    ok = send_email(
        to=to,
        subject="[FACOMS] Test Email",
        template_name="email/test.html",
        now=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    )
    flash("Email sent." if ok else "Email suppressed / not configured (dev).", "info")
    return redirect(url_for("journal.admin_submissions"))

# ---------- simple site-wide search ----------
@journal_bp.route('/search')
def search():
    q = (request.args.get('q') or "").strip()
    results = []
    if len(q) >= 2:
        # search title, abstract, keywords, authors_text (case-insensitive)
        results = (Submission.query
                   .filter(
                       or_(
                           Submission.title.ilike(f"%{q}%"),
                           Submission.abstract.ilike(f"%{q}%"),
                           Submission.keywords.ilike(f"%{q}%"),
                           Submission.authors_text.ilike(f"%{q}%")
                       )
                   )
                   .order_by(Submission.created_at.desc())
                   .limit(50)
                   .all())
    elif q:
        flash("Please enter at least 2 characters to search.", "info")
    return render_template("search_results.html", q=q, results=results)

# ---------- reviewer ----------
@journal_bp.route("/reviewer/queue")
@login_required
@role_required(Role.REVIEWER)
def reviewer_queue():
    queue = (Submission.query
             .filter_by(assigned_reviewer_id=current_user.id)
             .order_by(Submission.created_at.desc())
             .all())
    return render_template("review_queue.html", submissions=queue)


@journal_bp.route("/reviewer/review/<int:submission_id>", methods=["GET", "POST"])
@login_required
@role_required(Role.REVIEWER)
def review_submission(submission_id: int):
    sub = Submission.query.get_or_404(submission_id)
    if sub.assigned_reviewer_id != current_user.id:
        abort(403)

    form = ReviewForm()
    if form.validate_on_submit():
        review = Review(
            submission_id=sub.id,
            reviewer_id=current_user.id,
            comment=form.comment.data,
            score=form.score.data,
            decision=ReviewDecision(form.decision.data),
        )

        # Map decision → submission status (keep 4-state workflow)
        if review.decision == ReviewDecision.ACCEPT:
            sub.status = SubmissionStatus.ACCEPTED
        elif review.decision == ReviewDecision.REJECT:
            sub.status = SubmissionStatus.REJECTED
        else:
            sub.status = SubmissionStatus.UNDER_REVIEW

        db.session.add(review)
        db.session.commit()

        # Notify author (optional)
        send_email(
            to=sub.author.email,
            subject=f"[FACOMS] Review Decision: {review.decision.value.replace('_',' ').title()}",
            template_name="email/test.html",
            now=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        )

        flash("Review submitted.", "success")
        return redirect(url_for("journal.reviewer_queue"))

    return render_template("review_form.html", form=form, submission=sub)

