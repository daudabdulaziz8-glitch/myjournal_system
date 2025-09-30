# list_users.py
from journal import create_app, db
from journal.models import User

def main():
    app = create_app()
    with app.app_context():
        users = User.query.order_by(User.id.asc()).all()
        if not users:
            print("No users found.")
            return

        print(f"{'ID':<4} {'Username':<20} {'Email':<32} {'Role'}")
        print("-" * 70)
        for u in users:
            print(f"{u.id:<4} {u.username:<20} {u.email:<32} {u.role}")

if __name__ == "__main__":
    main()
