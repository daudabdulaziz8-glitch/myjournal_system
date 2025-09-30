from journal import create_app, db
from sqlalchemy import inspect, text

app = create_app()
with app.app_context():
    insp = inspect(db.engine)
    tables = set(insp.get_table_names())

    # ensure issue table exists
    if 'issue' not in tables:
        db.session.execute(text("""
        CREATE TABLE issue (
            id INTEGER PRIMARY KEY,
            volume INTEGER NOT NULL,
            number INTEGER NOT NULL,
            year INTEGER NOT NULL,
            published_at DATETIME,
            CONSTRAINT uq_issue_volume_number_year UNIQUE (volume, number, year)
        )
        """))
        print("Created table: issue")

    # ensure submission columns exist
    cols = {c['name'] for c in db.session.execute(text("PRAGMA table_info(submission)")).mappings()}
    need = []
    if 'issue_id' not in cols:
        need.append("ADD COLUMN issue_id INTEGER REFERENCES issue(id)")
    if 'doi' not in cols:
        need.append("ADD COLUMN doi VARCHAR(128)")
    if 'primary_orcid' not in cols:
        need.append("ADD COLUMN primary_orcid VARCHAR(19)")

    for clause in need:
        db.session.execute(text(f"ALTER TABLE submission {clause}"))
        print("Altered submission:", clause)

    # ensure user.orcid exists
    ucols = {c['name'] for c in db.session.execute(text("PRAGMA table_info(user)")).mappings()}
    if 'orcid' not in ucols:
        db.session.execute(text("ALTER TABLE user ADD COLUMN orcid VARCHAR(19)"))
        print("Altered user: add column orcid")

    db.session.commit()
    print("Schema check done.")
