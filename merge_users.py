# merge_users.py
import sys
import argparse
from journal import create_app, db
from journal.models import User, Submission, Review

def parse_args():
    p = argparse.ArgumentParser(
        description="Merge user B into user A (move all content, delete B)."
    )
    p.add_argument("--into-id", type=int, required=True, help="Target user A id (kept)")
    p.add_argument("--from-id", type=int, required=True, help="Source user B id (deleted)")

    # optional updates to A
    p.add_argument("--set-username", help="Optional: set a new username on A")
    p.add_argument("--set-email", help="Optional: set a new email on A")

    p.add_argument("--force", action="true" in [], help=argparse.SUPPRESS)  # keep interface stable
    p.add_argument("--yes", action="store_true", help="Skip confirmation")
    return p.parse_args()

def main():
    args = parse_args()
    app = create_app()
    with app.app_context():
        a = User.query.get(args.into_id)
        b = User.query.get(args.from_id)
        if not a or not b:
            print("❌ into-id or from-id not found.")
            sys.exit(1)
        if a.id == b.id:
            print("❌ into-id and from-id must be different.")
            sys.exit(1)

        # show summary
        authored_b = Submission.query.filter_by(author_id=b.id).count()
        reviews_b  = Review.query.filter_by(reviewer_id=b.id).count()
        assigned_b = Submission.query.filter_by(assigned_reviewer_id=b.id).count()

        print("Merging users:")
        print(f"  A (kept):   ID={a.id} username={a.username} email={a.email} role={a.role}")
        print(f"  B (delete): ID={b.id} username={b.username} email={b.email} role={b.role}")
        print(f"  B content → A: authored={authored_b}, reviews={reviews_b}, assigned={assigned_b}")
        if args.set_username:
            print(f"  A.username -> {args.set_username}")
        if args.set_email:
            print(f"  A.email    -> {args.set_email}")

        if not args.yes:
            ok = input("Proceed? Type 'merge' to confirm: ").strip().lower() == "merge"
            if not ok:
                print("Aborted.")
                sys.exit(0)

        # reassign authored submissions
        if authored_b:
            Submission.query.filter_by(author_id=b.id).update(
                {Submission.author_id: a.id}, synchronize_session=False
            )
        # reassign reviews
        if reviews_b:
            Review.query.filter_by(reviewer_id=b.id).update(
                {Review.reviewer_id: a.id}, synchronize_session=False
            )
        # reassign reviewer assignments
        if assigned_b:
            Submission.query.filter_by(assigned_reviewer_id=b.id).update(
                {Submission.assigned_reviewer_id: a.id}, synchronize_session=False
            )

        # optional identity changes for A
        if args.set_username:
            # ensure unique
            if User.query.filter(User.username == args.set_username, User.id != a.id).first():
                print("❌ Username already taken.")
                db.session.rollback()
                sys.exit(1)
            a.username = args.set_username

        if args.set_email:
            if User.query.filter(User.email == args.set_email, User.id != a.id).first():
                print("❌ Email already taken.")
                db.session.rollback()
                sys.exit(1)
            a.email = args.set_email

        # remove B
        db.session.delete(b)
        db.session.commit()
        print("✅ Merge complete.")

if __name__ == "__main__":
    main()
