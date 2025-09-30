# upgrade_user_reviewer_fields.py
# Safely adds user.orcid, user.reviewer_status, user.reviewer_note to SQLite.

from journal import create_app, db

def get_columns(conn, table):
    rows = conn.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()
    return [row[1] for row in rows]  # row[1] = name

def add_column(conn, ddl):
    conn.exec_driver_sql(ddl)

def main():
    app = create_app()
    with app.app_context():
        engine = db.engine

        with engine.connect() as conn:
            # Ensure the table exists
            tbls = conn.exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            table_names = {t[0] for t in tbls}
            if "user" not in table_names:
                raise SystemExit("❌ 'user' table not found. Initialize DB first (run init_db).")

            cols = set(get_columns(conn, "user"))

            # 1) ORCID
            if "orcid" not in cols:
                add_column(conn, "ALTER TABLE user ADD COLUMN orcid TEXT")
                print("✅ Added column user.orcid")

            # 2) reviewer_status (pending|approved|rejected)
            if "reviewer_status" not in cols:
                add_column(conn, "ALTER TABLE user ADD COLUMN reviewer_status TEXT DEFAULT 'pending'")
                # Backfill existing reviewers to approved
                conn.exec_driver_sql("""
                    UPDATE user
                    SET reviewer_status = 'approved'
                    WHERE role IN ('REVIEWER','reviewer')
                """)
                print("✅ Added column user.reviewer_status (default 'pending') and backfilled reviewers to 'approved'")

            # 3) reviewer_note
            if "reviewer_note" not in cols:
                add_column(conn, "ALTER TABLE user ADD COLUMN reviewer_note TEXT")
                print("✅ Added column user.reviewer_note")

            # Show final schema
            final_cols = get_columns(conn, "user")
            print("\n📋 user table columns now:")
            for c in final_cols:
                print(f" - {c}")

            print("\n🎉 Done. Restart your app.")

if __name__ == "__main__":
    main()
