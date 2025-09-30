# scripts/normalize_roles.py
from journal import create_app, db
from journal.models import User, Role

app = create_app()
with app.app_context():
    # Map any lowercase (or mixed) to proper Enum
    mapping = {
        'admin': Role.ADMIN,
        'reviewer': Role.REVIEWER,
        'author': Role.AUTHOR,
    }
    changed = 0
    for u in User.query.all():
        val = u.role
        # handle both string storage and Enum storage
        raw = val if isinstance(val, str) else getattr(val, 'value', None)
        if not raw:
            continue
        low = raw.lower()
        if low in mapping and (not isinstance(u.role, Role) or u.role != mapping[low]):
            u.role = mapping[low]
            changed += 1
    if changed:
        db.session.commit()
    print(f"✅ normalized {changed} user role(s)")
