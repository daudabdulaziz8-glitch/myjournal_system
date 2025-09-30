# delete_user.py
import sys
import argparse
from journal import create_app, db
from journal.models import User, Submission, Review

def parse_args():
    p = argparse.ArgumentParser(
        description="Delete a user safely (with reassignment or cascade)."
    )
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--id", type=int, help="User ID to delete")
    g.add_argument("--email", help="User email to delete")
    g.add_argument("--username", help="User username to delete")

    p.add_argument("--reassign-to-id", type=int,
                   help="User ID that will receive all authored submissions and reviews")
    p.add_argument("--delete-submissions", action="store_true",
                   help="Delete this user's authored submissions instead of reassigning")
    p.add_argument("--delete-reviews", action="store_true",
                   help="Delete this user's reviews instead of reassigning")

    p.add_argument("--force", action="store_true",
                   help="Do not prompt for confirmation")
    return p.parse_args()

def main():
    args = parse_args()

    app = create_app()
    with app.app_context():
        # locate target user
        q = User.query
        if args.id is not None:
            target = q.get(args.id)
        elif args.email:
            target = q.filter_by(email=args.email).first()
        else:
            target = q.filter_by(username=args.username).first()

        if not target:
            print("❌ Target user not found.")
            sys.exit(1)

        if target.role == "admin":
            print("❌ Refusing to delete an admin account. Demote first if intentional.")
            sys.exit(1)

        # resolve reassignment user if provided
        reassign_to = None
        if args.reassign_to_id:
            if args.reassign_to_id == target.id:
                print("❌ --reassign-to-id cannot be the same as the target user.")
                sys.exit(1)
            reassign_to = User.query.get(args.reassign_to_id)
            if not reassign_to:
                print("❌ Reassignment user not found.")
                sys.exit(1)

        # sanity: require a strategy for submissions AND reviews
        authored_count = Submission.query.filter_by(author_id=target.id).count()
        reviews_count  = Review.query.filter_by(reviewer_id=target.id).count()

        if authored_count:
            if not (args.reassign_to_id or args.delete_submissions):
                print(f"❌ User authored {authored_count} submission(s). "
                      f"Provide --reassign-to-id or --delete-submissions.")
                sys.exit(1)

        if reviews_count:
            if not (args.reassign_to_id or args.delete_reviews):
                print(f"❌ User wrote {reviews_count} review(s). "
                      f"Provide --reassign-to-id or --delete-reviews.")
                sys.exit(1)

        # summary
        print("About to delete user:")
        print(f"  ID={target.id}  username={target.username}  email={target.email}  role={target.role}")
        print(f"  Authored submissions: {authored_count}")
        print(f"  Reviews: {reviews_count}")
        if reassign_to:
            print(f"  Reassigning to ID={reassign_to.id} ({reassign_to.username})")
        if args.delete_submissions:
            print("  Will DELETE authored submissions.")
        if args.delete_reviews:
            print("  Will DELETE reviews.")

        if not args.force:
            ok = input("Proceed? Type 'yes' to confirm: ").strip().lower() == "yes"
            if not ok:
                print("Aborted.")
                sys.exit(0)

        # perform updates
        if authored_count:
            if args.delete_submissions:
                Submission.query.filter_by(author_id=target.id).delete(synchronize_session=False)
            else:
                Submission.query.filter_by(author_id=target.id).update(
                    {Submission.author_id: reassign_to.id}, synchronize_session=False
                )

        if reviews_count:
            if args.delete_reviews:
                Review.query.filter_by(reviewer_id=target.id).delete(synchronize_session=False)
            else:
                Review.query.filter_by(reviewer_id=target.id).update(
                    {Review.reviewer_id: reassign_to.id}, synchronize_session=False
                )

        # clear reviewer assignment on submissions where this user was assigned
        assigned_count = Submission.query.filter_by(assigned_reviewer_id=target.id).count()
        if assigned_count:
            Submission.query.filter_by(assigned_reviewer_id=target.id).update(
                {Submission.assigned_reviewer_id: None}, synchronize_session=False
            )
            print(f"  Cleared assigned_reviewer on {assigned_count} submission(s).")

        # finally delete the user
        db.session.delete(target)
        db.session.commit()
        print("✅ User deleted successfully.")

if __name__ == "__main__":
    main()
