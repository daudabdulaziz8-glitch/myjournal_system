# fix_reviewer_status_casing.py
from sqlalchemy import text
from journal import create_app, db

app = create_app()
with app.app_context():
    engine = db.engine

    with engine.begin() as conn:
        # Show current distinct values (optional)
        rows = conn.execute(text("SELECT DISTINCT reviewer_status FROM user")).fetchall()
        print("Before:", [r[0] for r in rows])

        # Normalize to UPPERCASE variants expected by the Enum
        conn.execute(text("UPDATE user SET reviewer_status='PENDING'  WHERE reviewer_status='pending'"))
        conn.execute(text("UPDATE user SET reviewer_status='APPROVED' WHERE reviewer_status='approved'"))
        conn.execute(text("UPDATE user SET reviewer_status='REJECTED' WHERE reviewer_status='rejected'"))

        # Also handle mixed/leading/trailing spaces, just in case
        conn.execute(text("UPDATE user SET reviewer_status=UPPER(TRIM(reviewer_status)) WHERE reviewer_status IS NOT NULL"))

        rows = conn.execute(text("SELECT DISTINCT reviewer_status FROM user")).fetchall()
        print("After:", [r[0] for r in rows])

    print("✅ reviewer_status values normalized.")
