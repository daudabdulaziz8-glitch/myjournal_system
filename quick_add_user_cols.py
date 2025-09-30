# quick_add_user_cols.py  (run:  python quick_add_user_cols.py)
from journal import create_app, db

def colnames(conn, table):
    return [r[1] for r in conn.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()]

app = create_app()
with app.app_context():
    engine = db.engine
    with engine.connect() as conn:
        # Ensure table exists
        tables = {t[0] for t in conn.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        if "user" not in tables:
            raise SystemExit("❌ 'user' table not found. Initialize DB first.")

        cols = set(colnames(conn, "user"))

        if "orcid" not in cols:
            conn.exec_driver_sql("ALTER TABLE user ADD COLUMN orcid TEXT")
            print("✅ Added user.orcid")

        if "reviewer_status" not in cols:
            conn.exec_driver_sql(
                "ALTER TABLE user ADD COLUMN reviewer_status TEXT DEFAULT 'pending'"
            )
            conn.exec_driver_sql(
                "UPDATE user SET reviewer_status='approved' WHERE role IN ('REVIEWER','reviewer')"
            )
            print("✅ Added user.reviewer_status")

        if "reviewer_note" not in cols:
            conn.exec_driver_sql("ALTER TABLE user ADD COLUMN reviewer_note TEXT")
            print("✅ Added user.reviewer_note")

        print("\n📋 user columns now:")
        for c in colnames(conn, "user"):
            print(" -", c)

print("\n🎉 Done. Restart your app.")
