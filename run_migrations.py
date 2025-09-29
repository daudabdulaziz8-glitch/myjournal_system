"""Run Alembic migrations (upgrade head) using the project's migrations folder.

Usage: python run_migrations.py

This script imports the Flask app and uses Alembic's command API to run
upgrade head. It requires Flask-Migrate and Alembic to be installed in the
current environment.
"""
import sys
from logging.config import fileConfig
from alembic import command
from alembic.config import Config
from journal import create_app


def main():
    app = create_app()
    # Create app context so migrations/env.py can reference current_app
    with app.app_context():
        alembic_cfg = Config("migrations/alembic.ini")
        # ensure logging config from alembic.ini is loaded
        if alembic_cfg.config_file_name:
            fileConfig(alembic_cfg.config_file_name)
        print('Running alembic upgrade head...')
        command.upgrade(alembic_cfg, "head")
        print('Alembic upgrade head finished')


if __name__ == '__main__':
    main()
