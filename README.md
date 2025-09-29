# MyJournal System

Flask + SQLite application for the Faculty of Computing & Mathematical Sciences.
Roles: Author, Reviewer, Admin
Submissions, reviewing, assignments
File uploads to `instance/uploads/`

## Dev
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
set FLASK_APP=app.py
Run the app with:

	python app.py

Recommended management commands (from project root, with venv activated):

	# show the DB URI used by the app
	python manage.py show-uri

	# create missing tables
	python manage.py init-db

	# normalize role values in the DB (UPPERCASE required by Enum)
	python manage.py normalize-roles

Notes:
- I added `manage.py` to help with safe DB operations.
- Temporary helper scripts used during debugging (`diagnostics_db.py`, `apply_external_db_fix.py`) can be removed if you want a clean workspace.

Testing & migrations
--------------------
- Run unit tests with pytest (install pytest in your venv first):

		pip install pytest
		pytest -q

- Optional Alembic migration added: `migrations/versions/20250929_normalize_roles.py`.
	Run migrations with:

		alembic upgrade head

	(Only run if your environment is configured with Alembic; the script simply lowercases stored role values.)
# FACOMS Journal Submission System

Flask + SQLite application for the Faculty of Computing & Mathematical Sciences.
- Roles: Author, Reviewer, Admin
- Submissions, reviewing, assignments
- File uploads to `instance/uploads/`

## Dev
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
set FLASK_APP=app.py
python app.py

Migrations & CI
---------------
- To run migrations locally (applies role normalization and other revisions):

		python run_migrations.py

- A GitHub Actions workflow was added at `.github/workflows/ci.yml` to run
	migrations, tests, and smoke checks on push/PR to `main`.

Security note: the code includes a development fallback `SECRET_KEY`. For
production, set a strong `SECRET_KEY` in your environment before deploying.
