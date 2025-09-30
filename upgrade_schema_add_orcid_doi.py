# upgrade_schema_add_orcid_doi.py
import os
import sqlite3

DB_PATH = os.path.join("instance", "database.db")

def col_exists(conn, table, col):
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r[1] == col for r in rows)

def add_col(conn, table, col, ddl):
    if not col_exists(conn, table, col):
        print(f"Adding {table}.{col} ...")
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")
    else:
        print(f"{table}.{col} already exists.")

def main():
    if not os.path.exists(DB_PATH):
        raise SystemExit(f"DB not found at {DB_PATH}. Start the app once or create it via init_db.py")

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("BEGIN")
        # Add columns used by your models/templates
        add_col(conn, "user", "orcid", "VARCHAR(19)")
        add_col(conn, "submission", "doi", "VARCHAR(255)")
        add_col(conn, "submission", "primary_orcid", "VARCHAR(19)")
        conn.commit()
        print("✅ Schema upgrade complete.")
    except Exception as e:
        conn.rollback()
        raise
    finally:
        print("\nuser columns:")
        for r in conn.execute("PRAGMA table_info(user)"):
            print(" -", r[1])
        print("\nsubmission columns:")
        for r in conn.execute("PRAGMA table_info(submission)"):
            print(" -", r[1])
        conn.close()

if __name__ == "__main__":
    main()
