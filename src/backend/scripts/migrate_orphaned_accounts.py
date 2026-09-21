"""
Migration helper: link orphaned Zerodha accounts to a default user.

Background
----------
The `users` table and the `accounts.user_id` foreign key were introduced in
Alembic revision 4b86235fc91f.  The column is **nullable**, so any accounts
that existed before that migration ran will have ``user_id = NULL`` and will
be invisible to the authenticated API.

This one-time script:
  1. Checks for accounts whose ``user_id`` is NULL ("orphaned" accounts).
  2. If no users exist yet, creates a default admin user and prompts you to
     set a password immediately after.
  3. If exactly one user exists, assigns all orphaned accounts to that user.
  4. If multiple users exist, lists them and asks you to pick one.
  5. Prints a summary and commits the change.

Usage
-----
  cd backend
  conda activate investment_dashboard   # or your venv
  python scripts/migrate_orphaned_accounts.py

  # Dry-run (show what would change without writing):
  python scripts/migrate_orphaned_accounts.py --dry-run

The script is idempotent: running it again when there are no orphaned accounts
is a no-op.
"""

import argparse
import sys
import os
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Bootstrap the Flask app so SQLAlchemy models are available
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # backend/

from app import create_app  # noqa: E402  (must come after sys.path insert)
from app.database import db  # noqa: E402
from app.models.account import Account  # noqa: E402
from app.models.user import User  # noqa: E402


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _pick_user(users: list[User]) -> User:
    """Prompt the operator to select a user from a numbered list."""
    print("\nMultiple users found – choose which one to own the orphaned accounts:")
    for i, u in enumerate(users, 1):
        print(f"  [{i}] {u.email}  (id={u.id}, name={u.full_name or '—'})")
    while True:
        raw = input("\nEnter number: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(users):
            return users[int(raw) - 1]
        print("  Invalid choice, try again.")


def _create_default_user() -> User:
    """Interactively create an admin user when the users table is empty."""
    print("\nNo users found in the database.")
    print("A default admin user will be created so the orphaned accounts can")
    print("be claimed.  You can update the password later via the API.\n")
    email = input("Admin email address: ").strip()
    if not email:
        raise SystemExit("Aborted: email cannot be empty.")
    full_name = input("Full name (optional): ").strip() or None

    import getpass
    password = getpass.getpass("Password: ")
    if len(password) < 8:
        raise SystemExit("Aborted: password must be at least 8 characters.")

    user = User(
        email=email,
        full_name=full_name,
        is_active=True,
        created_at=_utcnow(),
        updated_at=_utcnow(),
    )
    user.set_password(password)
    db.session.add(user)
    db.session.flush()  # assign user.id without committing yet
    print(f"\n  ✓ Created user '{email}' (id={user.id})")
    return user


def main(dry_run: bool = False) -> None:
    app = create_app()
    with app.app_context():
        # ------------------------------------------------------------------
        # 1. Find orphaned accounts
        # ------------------------------------------------------------------
        orphaned: list[Account] = Account.query.filter(
            Account.user_id.is_(None)
        ).all()

        if not orphaned:
            print("No orphaned accounts found (all accounts already have a user_id). Nothing to do.")
            return

        print(f"Found {len(orphaned)} orphaned account(s):")
        for acct in orphaned:
            print(f"  id={acct.id}  name={acct.account_name!r}  active={acct.is_active}")

        # ------------------------------------------------------------------
        # 2. Determine the target user
        # ------------------------------------------------------------------
        all_users: list[User] = User.query.filter_by(is_active=True).all()

        if len(all_users) == 0:
            target_user = _create_default_user()
        elif len(all_users) == 1:
            target_user = all_users[0]
            print(f"\nSingle user found: '{target_user.email}' (id={target_user.id})")
            print("All orphaned accounts will be assigned to this user.")
        else:
            target_user = _pick_user(all_users)

        # ------------------------------------------------------------------
        # 3. Assign and commit (or print dry-run summary)
        # ------------------------------------------------------------------
        if dry_run:
            print(f"\n[DRY-RUN] Would assign {len(orphaned)} account(s) to user '{target_user.email}':")
            for acct in orphaned:
                print(f"  accounts.id={acct.id} → user_id={target_user.id}")
            print("\nNo changes written (dry-run mode).")
            return

        confirm = input(
            f"\nAssign {len(orphaned)} account(s) to '{target_user.email}'? [y/N] "
        ).strip().lower()
        if confirm != 'y':
            print("Aborted.")
            return

        for acct in orphaned:
            acct.user_id = target_user.id
            acct.updated_at = _utcnow()

        db.session.commit()
        print(f"\n✓ {len(orphaned)} account(s) successfully linked to user '{target_user.email}'.")
        print("  You can verify by running:")
        print("    SELECT id, account_name, user_id FROM accounts WHERE user_id IS NOT NULL;")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        '--dry-run', action='store_true',
        help="Print what would change without modifying the database."
    )
    args = parser.parse_args()
    main(dry_run=args.dry_run)
