# seed.py
from journal import create_app, db, bcrypt
from journal.models import User, Submission, Review, SubmissionStatus, ReviewDecision, Role

app = create_app()

with app.app_context():
    # --- Ensure Users ---
    def get_or_create_user(username, email, role_enum, department, password):
        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(
                username=username,
                email=email,
                department=department,
                password=bcrypt.generate_password_hash(password).decode("utf-8"),
                role=role_enum   # ✅ Enum instead of string
            )
            db.session.add(user)
            db.session.commit()
            print(f"✅ Created {role_enum.value} user: {email} / {password}")
        return user

    admin = get_or_create_user("admin", "admin@example.com", Role.ADMIN, "System", "admin123")
    reviewer = get_or_create_user("reviewer", "reviewer@example.com", Role.REVIEWER, "Research", "reviewer123")
    author = get_or_create_user("author", "author@example.com", Role.AUTHOR, "Computing", "author123")

    # --- Ensure Sample Submissions ---
    if not Submission.query.filter_by(title="AI in Education").first():
        sub1 = Submission(
            title="AI in Education",
            abstract="Exploring the impact of AI on modern learning.",
            keywords="AI, Education",
            authors_text="John Doe",
            department="Computing",
            author_id=author.id,
            status=SubmissionStatus.PENDING
        )
        db.session.add(sub1)

    if not Submission.query.filter_by(title="Blockchain in Healthcare").first():
        sub2 = Submission(
            title="Blockchain in Healthcare",
            abstract="How blockchain improves medical record keeping.",
            keywords="Blockchain, Healthcare",
            authors_text="Jane Smith",
            department="Health",
            author_id=author.id,
            status=SubmissionStatus.UNDER_REVIEW,
            assigned_reviewer_id=reviewer.id
        )
        db.session.add(sub2)
        db.session.commit()

        # Attach a review
        review = Review(
            submission_id=sub2.id,
            reviewer_id=reviewer.id,
            comment="Strong paper, but needs more citations.",
            score=7,
            decision=ReviewDecision.MINOR_REVISION
        )
        db.session.add(review)

    db.session.commit()
    print("✅ Database seeded successfully (using Enum roles).")
