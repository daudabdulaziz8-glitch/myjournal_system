from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField, SelectField, FileField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from flask_wtf.file import FileAllowed

from .models import User  # ✅ import User model for validators


# -----------------------------
# Registration & Login
# -----------------------------
class RegistrationForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    department = StringField("Department", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    confirm_password = PasswordField("Confirm Password", validators=[DataRequired(), EqualTo("password")])
    submit = SubmitField("Sign Up")

    # ✅ Custom validators
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError("That username is already taken. Please choose another.")

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError("That email is already registered. Please choose another.")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Remember Me")
    submit = SubmitField("Login")


# -----------------------------
# Submission (Authors)
# -----------------------------
class SubmissionForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired()])
    abstract = TextAreaField("Abstract", validators=[DataRequired()])
    keywords = StringField("Keywords", validators=[DataRequired()])
    authors_text = StringField("Authors", validators=[DataRequired()])
    department = StringField("Department", validators=[DataRequired()])
    pdf_file = FileField("Upload PDF", validators=[DataRequired(), FileAllowed(["pdf"], "PDF only!")])
    submit = SubmitField("Submit Paper")


# -----------------------------
# Review (Reviewers)
# -----------------------------
class ReviewForm(FlaskForm):
    comment = TextAreaField("Comments", validators=[DataRequired()])
    score = StringField("Score (1-10)", validators=[DataRequired()])
    decision = SelectField(
        "Decision",
        choices=[
            ("ACCEPT", "Accept"),
            ("REJECT", "Reject"),
            ("MINOR_REVISION", "Minor Revision"),
            ("MAJOR_REVISION", "Major Revision"),
        ],
        validators=[DataRequired()]
    )
    submit = SubmitField("Submit Review")
