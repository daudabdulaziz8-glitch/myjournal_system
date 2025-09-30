from journal import create_app, db
from sqlalchemy import text

app = create_app()
with app.app_context():
    def column_exists(table, col):
        rows = db.session.execute(text(f"PRAGMA table_info({table})")).all()
        return any(r[1] == col for r in rows)

    added = False
    if not column_exists('submission', 'doi'):
        db.session.execute(text("ALTER TABLE submission ADD COLUMN doi VARCHAR(100)"))
        print("Added column: submission.doi")
        added = True

    if not column_exists('submission', 'primary_orcid'):
        db.session.execute(text("ALTER TABLE submission ADD COLUMN primary_orcid VARCHAR(19)"))
        print("Added column: submission.primary_orcid")
        added = True

    db.session.commit()
    print("✅ Migration complete" if added else "✅ Columns already present")
