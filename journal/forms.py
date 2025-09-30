# journal/forms.py
from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, SubmitField, TextAreaField,
    BooleanField, SelectField, FileField
)
from wtforms.validators import DataRequired, Email, Length, EqualTo, NumberRange


# -----------------------------
# Registration Form
# -----------------------------
class RegistrationForm(FlaskForm):
    username = StringField(
        "Username",
        validators=[DataRequired(), Length(min=3, max=25)]
    )
    email = StringField(
        "Email",
        validators=[DataRequired(), Email()]
    )
    department = StringField(
        "Department",
        validators=[DataRequired(), Length(max=100)]
    )
    password = PasswordField(
        "Password",
        validators=[DataRequired(), Length(min=6)]
    )
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[DataRequired(), EqualTo("password")]
    )
    submit = SubmitField("Register")


# -----------------------------
# Login Form
# -----------------------------
class LoginForm(FlaskForm):
    email = StringField(
        "Email",
        validators=[DataRequired(), Email()]
    )
    password = PasswordField(
        "Password",
        validators=[DataRequired()]
    )
    remember = BooleanField("Remember Me")
    submit = SubmitField("Login")


# -----------------------------
# Submission Form (Author uploads PDF)
# -----------------------------
class SubmissionForm(FlaskForm):
    title = StringField(
        "Title",
        validators=[DataRequired(), Length(max=200)]
    )
    abstract = TextAreaField(
        "Abstract",
        validators=[DataRequired()]
    )
    keywords = StringField(
        "Keywords",
        validators=[DataRequired()]
    )
    authors_text = StringField(
        "Authors",
        validators=[DataRequired()]
    )
    department = StringField(
        "Department",
        validators=[DataRequired()]
    )
    pdf_file = FileField(
        "Upload Manuscript (PDF)",
        validators=[DataRequired()]
    )
    submit = SubmitField("Submit Manuscript")


# -----------------------------
# Review Form (Reviewer feedback)
# -----------------------------
class ReviewForm(FlaskForm):
    score = StringField(
        "Score (1–10)",
        validators=[DataRequired(), Length(max=2)]
    )
    decision = SelectField(
        "Decision",
        choices=[
            ("ACCEPT", "Accept"),
            ("REJECT", "Reject"),
            ("REVISION", "Revision"),
        ],
        validators=[DataRequired()]
    )
    comment = TextAreaField(
        "Comments",
        validators=[DataRequired(), Length(min=10)]
    )
    submit = SubmitField("Submit Review")
