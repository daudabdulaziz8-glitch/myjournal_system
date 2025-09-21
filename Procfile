web: bash -lc "flask db upgrade || python init_db.py; gunicorn -w 2 -k gthread -b 0.0.0.0:$PORT app:app"
