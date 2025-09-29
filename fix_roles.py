"""Fix and inspect user.role values.

This script does two things:
- Print distinct `role` values in the current app DB (SQLAlchemy URL), then
  normalize them to UPPER('role') for compatibility with older enum mappings.
- Print distinct `role` values found in the external PyCharm DB path so you
  can confirm that DB's values as well.

Run with the project's venv Python: python fix_roles.py
"""

import os
import sqlite3
from sqlalchemy import text

from journal import create_app, db

# External PyCharm DB path (change if your PyCharm project is elsewhere)
PYCHARM_DB = r"C:\Users\hp\PycharmProjects\myjournal_system\instance\database.db"


def distinct_roles_from_conn(conn):
    cur = conn.execute(text("SELECT role, COUNT(*) FROM user GROUP BY role"))
    return [(row[0], row[1]) for row in cur.fetchall()]


def print_roles(title, rows):
    print(title)
    if not rows:
        print('  (no rows)')
    for r, c in rows:
        print(f"  {r!r}: {c}")


def fix_admin_role():
    app = create_app()
    print('App SQLALCHEMY_DATABASE_URI:', app.config.get('SQLALCHEMY_DATABASE_URI'))

    with app.app_context():
        # Inspect current app DB
        with db.engine.connect() as conn:
            before = distinct_roles_from_conn(conn)
            print_roles('Workspace DB - before:', before)

            # Normalize role values to LOWER (store enum.value) using raw SQL
            res = conn.execute(text(
                """
                UPDATE user
                SET role = LOWER(role)
                WHERE lower(role) IN ('admin','reviewer','author') OR upper(role) IN ('ADMIN','REVIEWER','AUTHOR')
                """
            ))
            conn.commit()
            print(f'Workspace DB - rows affected: {res.rowcount}')

            after = distinct_roles_from_conn(conn)
            print_roles('Workspace DB - after:', after)

    # Also inspect the external PyCharm DB file (read-only, sqlite3)
    print('\nChecking external PyCharm DB at:', PYCHARM_DB)
    if not os.path.exists(PYCHARM_DB):
        print('External PyCharm DB not found:', PYCHARM_DB)
        return

    conn = sqlite3.connect(PYCHARM_DB)
    try:
        cur = conn.cursor()
        # show before
        cur.execute("SELECT role, COUNT(*) FROM user GROUP BY role")
        rows_before = cur.fetchall()
        print_roles('PyCharm DB - before:', rows_before)

        # normalize to lowercase values
        cur.execute("UPDATE user SET role = LOWER(role) WHERE lower(role) IN ('admin','reviewer','author') OR upper(role) IN ('ADMIN','REVIEWER','AUTHOR')")
        conn.commit()

        cur.execute("SELECT role, COUNT(*) FROM user GROUP BY role")
        rows_after = cur.fetchall()
        print_roles('PyCharm DB - after:', rows_after)
    except sqlite3.DatabaseError as e:
        print('Error reading/updating external DB:', e)
    finally:
        conn.close()


if __name__ == '__main__':
    fix_admin_role()
