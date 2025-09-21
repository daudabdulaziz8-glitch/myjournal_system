# journal/forms.py
from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, SubmitField, BooleanField,
    TextAreaField, SelectField, IntegerField
)
from wtforms.validators import DataRequired, Length, Email, EqualTo, NumberRange, Optional
from flask_wtf.file import FileField, FileAllowed, FileRequired

DEPARTMENTS = [
    ("Computer Science", "Computer Science"),
    ("Mathematics", "Mathematics"),
    ("Statistics", "Statistics"),
    ("Other", "Other"),
]


class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=50)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    department = SelectField('Department', choices=DEPARTMENTS, validators=[Optional()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6, max=128)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Create Account')


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6, max=128)])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')


class SubmissionForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(min=4, max=200)])
    abstract = TextAreaField('Abstract', validators=[DataRequired(), Length(min=20)])
    keywords = StringField('Keywords (comma-separated)', validators=[Optional(), Length(max=200)])
    authors_text = StringField('Co-authors (optional)', validators=[Optional(), Length(max=255)])
    department = SelectField('Department', choices=DEPARTMENTS, validators=[Optional()])
    manuscript = FileField('PDF Manuscript (optional)', validators=[FileAllowed(['pdf'], 'PDFs only')])
    submit = SubmitField('Submit')


class ReviewForm(FlaskForm):
    comment = TextAreaField('Reviewer Comments', validators=[DataRequired(), Length(min=10)])
    score = IntegerField('Score (1-5)', validators=[NumberRange(min=1, max=5)], default=5)
    decision = SelectField('Decision', choices=[
        ("accept", "Accept"),
        ("minor_revision", "Minor Revision"),
        ("major_revision", "Major Revision"),
        ("reject", "Reject"),
    ], validators=[DataRequired()])
    submit = SubmitField('Submit Review')


class RevisionUploadForm(FlaskForm):
    """For authors to upload a new PDF version with an optional note."""
    file = FileField('Revised PDF', validators=[FileRequired(), FileAllowed(['pdf'], 'PDFs only')])
    note = StringField('Note (optional)', validators=[Optional(), Length(max=255)])
    submit = SubmitField('Upload Revision')
