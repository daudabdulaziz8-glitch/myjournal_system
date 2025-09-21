# journal/models.py
from datetime import datetime
import enum

from flask_login import UserMixin
from . import db, login_manager


# ---------- Login loader ----------
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ---------- Enums ----------
class Role(enum.Enum):
    AUTHOR = "author"
    REVIEWER = "reviewer"
    ADMIN = "admin"


class SubmissionStatus(enum.Enum):
    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    REVISIONS_REQUESTED = "revisions_requested"   # <-- required by routes


class ReviewDecision(enum.Enum):
    ACCEPT = "accept"
    MINOR = "minor_revision"
    MAJOR = "major_revision"
    REJECT = "reject"


# ---------- Core models ----------
class User(db.Model, UserMixin):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)

    # We keep simple string role stored as Enum(Role)
    role = db.Column(db.Enum(Role), default=Role.AUTHOR, nullable=False)

    username = db.Column(db.String(50), unique=True, nullable=False)
    email    = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

    department = db.Column(db.String(100), nullable=True)

    # Author submissions
    submissions = db.relationship(
        "Submission",
        back_populates="author",
        primaryjoin="User.id==Submission.author_id",
        lazy="dynamic",
    )

    # Reviewer assigned submissions
    assigned_submissions = db.relationship(
        "Submission",
        back_populates="assigned_reviewer",
        primaryjoin="User.id==Submission.assigned_reviewer_id",
        lazy="dynamic",
    )

    reviews = db.relationship(
        "Review",
        back_populates="reviewer",
        primaryjoin="User.id==Review.reviewer_id",
        lazy="dynamic",
    )

    def is_reviewer(self):
        return self.role == Role.REVIEWER

    def is_admin(self):
        return self.role == Role.ADMIN

    def __repr__(self):
        return f"<User {self.username} ({self.role.value})>"


class Issue(db.Model):
    """
    Optional 'journal issue' (Volume/Number/Year).
    Your routes use /issues and may assign Submission.issue_id later.
    """
    __tablename__ = "issue"
    __table_args__ = (
        db.UniqueConstraint("volume", "number", "year", name="uq_issue_vny"),
    )

    id = db.Column(db.Integer, primary_key=True)
    volume = db.Column(db.Integer, nullable=False)
    number = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    published_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    submissions = db.relationship(
        "Submission",
        back_populates="issue",
        lazy="dynamic",
    )

    def __repr__(self):
        return f"<Issue V{self.volume} N{self.number} ({self.year})>"


class Submission(db.Model):
    __tablename__ = "submission"

    id = db.Column(db.Integer, primary_key=True)

    title        = db.Column(db.String(200), nullable=False)
    abstract     = db.Column(db.Text, nullable=False)
    keywords     = db.Column(db.String(200))
    authors_text = db.Column(db.String(255))
    department   = db.Column(db.String(100))

    status = db.Column(db.Enum(SubmissionStatus), nullable=False,
                       default=SubmissionStatus.PENDING)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Foreign keys
    author_id            = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    assigned_reviewer_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    issue_id             = db.Column(db.Integer, db.ForeignKey("issue.id"))

    # Relationships (disambiguated with foreign_keys)
    author = db.relationship(
        "User",
        foreign_keys=[author_id],
        back_populates="submissions",
    )

    assigned_reviewer = db.relationship(
        "User",
        foreign_keys=[assigned_reviewer_id],
        back_populates="assigned_submissions",
    )

    issue = db.relationship(
        "Issue",
        back_populates="submissions",
    )

    # Versioned file attachments (latest first)
    files = db.relationship(
        "SubmissionFile",
        back_populates="submission",
        order_by="SubmissionFile.version.desc()",
        lazy="select",
        cascade="all, delete-orphan",
    )

    reviews = db.relationship(
        "Review",
        back_populates="submission",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def latest_version(self) -> int | None:
        """Return the highest version number or None if no files."""
        if not self.files:
            return None
        return max(f.version for f in self.files)

    def __repr__(self):
        return f"<Submission {self.title[:20]!r} {self.status.value}>"


class SubmissionFile(db.Model):
    """
    Stores versioned PDF files per submission.
    filenames are like: submission_<submission_id>_v<version>.pdf
    """
    __tablename__ = "submission_file"
    __table_args__ = (
        db.UniqueConstraint("submission_id", "version", name="uq_submission_file_version"),
    )

    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.Integer, db.ForeignKey("submission.id"), nullable=False)

    version  = db.Column(db.Integer, nullable=False)  # 1,2,3...
    filename = db.Column(db.String(300), nullable=False)
    note     = db.Column(db.String(255))

    uploaded_by_user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    uploaded_at         = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    submission = db.relationship("Submission", back_populates="files")
    uploaded_by = db.relationship("User")

    def __repr__(self):
        return f"<SubmissionFile sub={self.submission_id} v={self.version} {self.filename}>"


class Review(db.Model):
    __tablename__ = "review"

    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.Integer, db.ForeignKey("submission.id"), nullable=False)
    reviewer_id   = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    comment  = db.Column(db.Text, nullable=False)
    score    = db.Column(db.Integer)  # optional 1..5
    decision = db.Column(db.Enum(ReviewDecision), nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    submission = db.relationship("Submission", back_populates="reviews")
    reviewer   = db.relationship("User", back_populates="reviews")

    def __repr__(self):
        return f"<Review sub={self.submission_id} by={self.reviewer_id} {self.decision.value}>"
