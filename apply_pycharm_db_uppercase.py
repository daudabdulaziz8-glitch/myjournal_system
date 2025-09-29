import sqlite3
import os

p = r"C:\Users\hp\PycharmProjects\myjournal_system\instance\database.db"
print('Target DB:', p)
if not os.path.exists(p):
    print('DB not found')
    raise SystemExit(1)

conn = sqlite3.connect(p)
cur = conn.cursor()

# show distinct roles before
cur.execute("SELECT role, COUNT(*) FROM user GROUP BY role")
print('Before:')
for row in cur.fetchall():
    print(row)

# Map lowercase -> uppercase names
cur.execute("UPDATE user SET role = CASE WHEN lower(role)='admin' THEN 'ADMIN' WHEN lower(role)='reviewer' THEN 'REVIEWER' WHEN lower(role)='author' THEN 'AUTHOR' ELSE role END WHERE role IS NOT NULL")
conn.commit()

cur.execute("SELECT role, COUNT(*) FROM user GROUP BY role")
print('After:')
for row in cur.fetchall():
    print(row)

conn.close()
print('Done')
