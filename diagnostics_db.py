from journal import create_app
import sqlite3
import re

app = create_app()
uri = app.config.get('SQLALCHEMY_DATABASE_URI')
print('SQLALCHEMY_DATABASE_URI:', uri)

m = re.match(r'sqlite:///(.*)', uri)
if not m:
    print('Cannot parse sqlite path from URI')
    raise SystemExit(1)

db_path = m.group(1)
print('Database file path:', db_path)

conn = sqlite3.connect(db_path)
cur = conn.cursor()

# List tables
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
print('Tables:', cur.fetchall())

# Try to read user table if present
try:
    cur.execute('SELECT id, username, role FROM user')
    rows = cur.fetchall()
    print('user rows:')
    for r in rows:
        print(r)
except Exception as e:
    print('Error reading user table:', e)

conn.close()
