import sqlite3
import os

db_path = r"C:\Users\hp\PycharmProjects\myjournal_system\instance\database.db"
print('Target DB path:', db_path)

if not os.path.exists(db_path):
    print('ERROR: database file not found at path')
    raise SystemExit(1)

conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Print roles before
try:
    cur.execute("SELECT id, username, role FROM user")
    rows = cur.fetchall()
    print(f'user rows before ({len(rows)}):')
    for r in rows:
        print(r)
except Exception as e:
    print('Error reading user table:', e)
    conn.close()
    raise

before_changes = conn.total_changes

# Update lowercase roles to uppercase using raw SQL
cur.execute("UPDATE user SET role = UPPER(role) WHERE lower(role) IN ('admin','reviewer','author')")
conn.commit()

affected = conn.total_changes - before_changes
print(f'Rows affected by update: {affected}')

# Print roles after
cur.execute("SELECT id, username, role FROM user")
rows_after = cur.fetchall()
print(f'user rows after ({len(rows_after)}):')
for r in rows_after:
    print(r)

conn.close()
print('Done')
