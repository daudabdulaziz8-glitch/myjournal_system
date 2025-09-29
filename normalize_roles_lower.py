from journal import create_app
import sqlite3, re, os

# workspace DB
app = create_app()
uri = app.config['SQLALCHEMY_DATABASE_URI']
print('Workspace URI:', uri)
path = re.match(r'sqlite:///(.*)', uri).group(1)
print('Workspace DB:', path)
conn = sqlite3.connect(path)
cur = conn.cursor()
cur.execute("UPDATE user SET role = LOWER(role) WHERE role IS NOT NULL")
conn.commit()
print('Workspace rows changed:', conn.total_changes)
conn.close()

# external PyCharm DB
p = r"C:\Users\hp\PycharmProjects\myjournal_system\instance\database.db"
if os.path.exists(p):
    conn = sqlite3.connect(p)
    cur = conn.cursor()
    cur.execute("UPDATE user SET role = LOWER(role) WHERE role IS NOT NULL")
    conn.commit()
    print('External rows changed:', conn.total_changes)
    conn.close()
else:
    print('External DB not found:', p)
