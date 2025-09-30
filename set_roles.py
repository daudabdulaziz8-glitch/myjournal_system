# set_roles.py
"""
Promote/demote users to roles (author | reviewer | admin).

Usage examples:
  python set_roles.py --email admin@example.com --role admin
  python set_roles.py --username reviewer1 --role reviewer
  python set_roles.py --id 12 --role author
  python set_roles.py --list
  python set_roles.py --create --email dean@uni.edu --username dean --role admin --password secret123
"""

import sys
import argparse
from journal import create_app, db, bcrypt
from journal.models import User

VALID_ROLES = {"author", "reviewer", "admin"}

def parse_args():
    p = argparse.ArgumentParser(description="Set or inspect user roles.")
    ident = p.add_mutually_exclusive_group(required=False)
    ident.add_argument("--email", help="User email")
    ident.add_argument("--username", help="User username")
    ident.add_argument("--id", type=int, help="User id")

    p.add_argument("--role", help=f"Target role ({', '.join(sorted(VALID_ROLES))})")
    p.add_argument("--list", action="store_true", help="List users and roles")
    p.add_argument("--create", action="store_true",
                   help="Create the user if not found (requires --email, --username, --password, --role)")
    p.add_argument("--password", help="Password when creating a new user")
    p.add_argument("--department", help="Optional department for new user")
    return p.parse_args()

def find_user(email=None, username=None, id_=None):
    q = User.query
    if id_ is not None:
        return q.get(id_)
    if email:
        return q.filter_by(email=email).first()
    if username:
        return q.filter_by(username=username).first()
    return None

def list_users():
    users = User.query.order_by(User.id.asc()).all()
    if not users:
        print("No users.")
        return
    print(f"{'ID':>4}  {'Username':<20}  {'Email':<30}  {'Role':<9}  {'Dept'}")
    print("-" * 80)
    for u in users:
        print(f"{u.id:>4}  {u.username:<20}  {u.email:<30}  {u.role:<9}  {u.department or ''}")

def main():
    args = parse_args()
    app = create_app()
    with app.app_context():
        # just list?
        if args.list:
            list_users()
            return

        # need a target role if modifying
        if args.role:
            role = args.role.strip().lower()
            if role not in VALID_ROLES:
                print(f"❌ Invalid role '{args.role}'. Valid: {', '.join(sorted(VALID_ROLES))}")
                sys.exit(1)
        else:
            role = None

        # must specify an identity unless --list
        if not (args.email or args.username or args.id):
            print("❌ Provide one of --email / --username / --id (or use --list).")
            sys.exit(1)

        user = find_user(args.email, args.username, args.id)

        if not user:
            if not args.create:
                print("❌ User not found. Use --create to create.")
                sys.exit(1)
            # creating
            missing = [k for k, v in {
                "--email": args.email,
                "--username": args.username,
                "--password": args.password,
                "--role": role,
            }.items() if not v]
            if missing:
                print("❌ To create, you must provide:", ", ".join(missing))
                sys.exit(1)

            # uniqueness checks
            if User.query.filter_by(username=args.username).first():
                print("❌ Username already exists.")
                sys.exit(1)
            if User.query.filter_by(email=args.email).first():
                print("❌ Email already exists.")
                sys.exit(1)

            hashed = bcrypt.generate_password_hash(args.password).decode("utf-8")
            user = User(
                username=args.username,
                email=args.email,
                password=hashed,
                role=role,
                department=args.department,
            )
            db.session.add(user)
            db.session.commit()
            print(f"✅ Created user ID={user.id} username={user.username} email={user.email} role={user.role}")
            return

        # update role if requested
        if role:
            old = user.role
            user.role = role
            db.session.commit()
            print(f"✅ Updated role for ID={user.id} ({user.username}): {old} → {user.role}")
        else:
            print(f"ℹ User found: ID={user.id} username={user.username} email={user.email} role={user.role}")

if __name__ == "__main__":
    main()
