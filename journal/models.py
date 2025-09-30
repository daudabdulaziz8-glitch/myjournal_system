import enum
from datetime import datetime
from flask_login import UserMixin
from . import db, login_manager


# ------------ Enums ------------
class Role(enum.Enum):
    AUTHOR = "author"
    REVIEWER = "reviewer"
    ADMIN = "admin"


class SubmissionStatus(enum.Enum):
    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class ReviewDecision(enum.Enum):
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    MINOR_REVISION = "MINOR_REVISION"
    MAJOR_REVISION = "MAJOR_REVISION"
    REVISE = "REVISE"  # kept for backward compatibility


# ------------ Flask-Login loader ------------
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ------------ Models ------------
class User(db.Model, UserMixin):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(50), unique=True, nullable=False)
    email    = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

    # use Enum(Role) to match routes that import Role
    role = db.Column(db.Enum(Role), nullable=False, default=Role.AUTHOR)
    department = db.Column(db.String(100), nullable=True)

    # Disambiguated relationships
    submissions = db.relationship(
        "Submission",
        back_populates="author",
        foreign_keys="Submission.author_id",
        lazy=True,
    )
    assigned_reviews = db.relationship(
        "Submission",
        back_populates="assigned_reviewer",
        foreign_keys="Submission.assigned_reviewer_id",
        lazy=True,
    )

    def is_reviewer(self) -> bool:
        val = self.role.value if isinstance(self.role, Role) else self.role
        return val == "reviewer"

    def is_admin(self) -> bool:
        val = self.role.value if isinstance(self.role, Role) else self.role
        return val == "admin"

    def __repr__(self):
        val = self.role.value if isinstance(self.role, Role) else self.role
        return f"<User {self.username} ({val})>"


class Submission(db.Model):
    __tablename__ = "submission"

    id = db.Column(db.Integer, primary_key=True)

    title        = db.Column(db.String(200), nullable=False)
    abstract     = db.Column(db.Text, nullable=False)
    keywords     = db.Column(db.String(200), nullable=True)
    authors_text = db.Column(db.String(255), nullable=True)
    department   = db.Column(db.String(100), nullable=True)

    status = db.Column(db.Enum(SubmissionStatus), nullable=False, default=SubmissionStatus.PENDING)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    author_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    assigned_reviewer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)

    author = db.relationship(
        "User",
        back_populates="submissions",
        foreign_keys=[author_id],
    )
    assigned_reviewer = db.relationship(
        "User",
        back_populates="assigned_reviews",
        foreign_keys=[assigned_reviewer_id],
    )

    def __repr__(self):
        return f"<Submission {self.title[:20]}... {self.status.value}>"


class Review(db.Model):
    __tablename__ = "review"

    id = db.Column(db.Integer, primary_key=True)

    submission_id = db.Column(db.Integer, db.ForeignKey("submission.id"), nullable=False)
    reviewer_id   = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    comment  = db.Column(db.Text, nullable=False)
    score    = db.Column(db.Integer, nullable=True)
    decision = db.Column(db.Enum(ReviewDecision), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    submission = db.relationship("Submission", backref=db.backref("reviews", lazy=True))
