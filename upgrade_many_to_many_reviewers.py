from journal import create_app, db
from sqlalchemy import inspect, text

app = create_app()
with app.app_context():
    insp = inspect(db.engine)
    tables = insp.get_table_names()
    if 'submission_reviewer' not in tables:
        db.session.execute(text("""
        CREATE TABLE submission_reviewer (
            submission_id INTEGER NOT NULL,
            reviewer_id  INTEGER NOT NULL,
            PRIMARY KEY (submission_id, reviewer_id),
            FOREIGN KEY(submission_id) REFERENCES submission (id) ON DELETE CASCADE,
            FOREIGN KEY(reviewer_id)  REFERENCES user (id) ON DELETE CASCADE
        );
        """))
        db.session.commit()
        print("✔ Created table submission_reviewer")
    print("✅ Done.")
