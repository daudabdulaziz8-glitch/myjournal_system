# upgrade_add_doi_orcid.py
from sqlalchemy import inspect, text
from journal import create_app, db

def main():
    app = create_app()
    with app.app_context():
        engine = db.engine
        insp = inspect(engine)

        if 'submission' not in insp.get_table_names():
            print("❌ Table 'submission' not found. Run your DB init first.")
            return

        # Current columns
        cols = {
            row['name']
            for row in db.session.execute(text("PRAGMA table_info(submission)")).mappings()
        }

        # Add missing columns (SQLite supports simple ADD COLUMN)
        if 'doi' not in cols:
            print("➕ Adding submission.doi ...")
            db.session.execute(text("ALTER TABLE submission ADD COLUMN doi VARCHAR(255)"))
        else:
            print("✅ 'doi' already exists.")

        if 'primary_orcid' not in cols:
            print("➕ Adding submission.primary_orcid ...")
            db.session.execute(text("ALTER TABLE submission ADD COLUMN primary_orcid VARCHAR(19)"))
        else:
            print("✅ 'primary_orcid' already exists.")

        db.session.commit()

        # Show final schema
        print("\n📋 submission columns now:")
        for c in db.session.execute(text("PRAGMA table_info(submission)")).mappings():
            print(f" - {c['name']} ({c['type']})")

if __name__ == "__main__":
    main()
