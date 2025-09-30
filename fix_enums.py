# fix_enums.py
from sqlalchemy import text
from journal import create_app, db

VALID_REVIEWER = ("PENDING", "APPROVED", "REJECTED")
VALID_SUB      = ("PENDING", "UNDER_REVIEW", "ACCEPTED", "REJECTED")

app = create_app()
with app.app_context():
    eng = db.engine
    with eng.begin() as conn:
        # Show current distincts (optional)
        print("Before reviewer:", [r[0] for r in conn.execute(text(
            "SELECT DISTINCT reviewer_status FROM user"
        ))])
        print("Before submission:", [r[0] for r in conn.execute(text(
            "SELECT DISTINCT status FROM submission"
        ))])

        # Normalize reviewer_status → UPPERCASE
        conn.execute(text("UPDATE user SET reviewer_status = UPPER(TRIM(reviewer_status)) "
                          "WHERE reviewer_status IS NOT NULL"))

        # If any invalid reviewer_status values exist, coerce to PENDING
        conn.execute(text("UPDATE user SET reviewer_status = 'PENDING' "
                          "WHERE reviewer_status NOT IN ('PENDING','APPROVED','REJECTED') "
                          "OR reviewer_status IS NULL"))

        # Normalize submission.status → UPPERCASE
        conn.execute(text("UPDATE submission SET status = UPPER(TRIM(status)) "
                          "WHERE status IS NOT NULL"))

        # Map legacy / invalid submission states to valid ones
        # e.g. legacy: REVISIONS_REQUESTED → UNDER_REVIEW
        conn.execute(text("UPDATE submission SET status='UNDER_REVIEW' "
                          "WHERE status IN ('REVISIONS_REQUESTED', 'REVISION_REQUESTED', 'REVISE')"))

        # Any remaining invalids → PENDING
        conn.execute(text("UPDATE submission SET status='PENDING' "
                          "WHERE status NOT IN ('PENDING','UNDER_REVIEW','ACCEPTED','REJECTED') "
                          "OR status IS NULL"))

        print("After reviewer:", [r[0] for r in conn.execute(text(
            "SELECT DISTINCT reviewer_status FROM user"
        ))])
        print("After submission:", [r[0] for r in conn.execute(text(
            "SELECT DISTINCT status FROM submission"
        ))])

    print("✅ Enum values normalized.")
