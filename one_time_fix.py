from journal import create_app, db
from sqlalchemy import text

app = create_app()
app.app_context().push()

# --- Fix role strings in user table ---
db.session.execute(text("UPDATE user SET role='ADMIN'    WHERE role='admin'"))
db.session.execute(text("UPDATE user SET role='REVIEWER' WHERE role='reviewer'"))
db.session.execute(text("UPDATE user SET role='AUTHOR'   WHERE role='author'"))
db.session.execute(text("UPDATE user SET role='AUTHOR'   WHERE role IS NULL"))

# --- Fix submission status strings (if any are lowercase) ---
db.session.execute(text("UPDATE submission SET status='PENDING'       WHERE status='pending'"))
db.session.execute(text("UPDATE submission SET status='UNDER_REVIEW'  WHERE status='under_review'"))
db.session.execute(text("UPDATE submission SET status='ACCEPTED'      WHERE status='accepted'"))
db.session.execute(text("UPDATE submission SET status='REJECTED'      WHERE status='rejected'"))

# --- Fix review decision strings (if any are lowercase) ---
db.session.execute(text("UPDATE review SET decision='ACCEPT'          WHERE decision='accept'"))
db.session.execute(text("UPDATE review SET decision='MINOR'           WHERE decision='minor_revision'"))
db.session.execute(text("UPDATE review SET decision='MAJOR'           WHERE decision='major_revision'"))
db.session.execute(text("UPDATE review SET decision='REJECT'          WHERE decision='reject'"))

db.session.commit()
print("✅ Normalized enum-like strings to enum names.")
