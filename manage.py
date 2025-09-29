"""Simple project management commands:
- show-uri: print SQLALCHEMY_DATABASE_URI
- init-db: create all tables
- normalize-roles: uppercase role values in the user table (safe, raw SQL)

Usage: python manage.py <command>
"""
import sys
from journal import create_app, db
from sqlalchemy import text


def show_uri(app):
    print('SQLALCHEMY_DATABASE_URI:', app.config.get('SQLALCHEMY_DATABASE_URI'))


def init_db(app):
    with app.app_context():
        db.create_all()
        print('✅ Tables created successfully')


def normalize_roles(app):
    with app.app_context():
        # Use raw SQL to avoid Enum casting issues
        with db.engine.connect() as conn:
            res = conn.execute(text("UPDATE user SET role = UPPER(role) WHERE lower(role) IN ('admin','reviewer','author')"))
            print(f'Rows affected: {res.rowcount}')


def main():
    if len(sys.argv) < 2:
        print('Usage: python manage.py show-uri|init-db|normalize-roles')
        raise SystemExit(1)

    cmd = sys.argv[1]
    app = create_app()

    if cmd == 'show-uri':
        show_uri(app)
    elif cmd == 'init-db':
        init_db(app)
    elif cmd == 'normalize-roles':
        normalize_roles(app)
    else:
        print('Unknown command', cmd)


if __name__ == '__main__':
    main()
