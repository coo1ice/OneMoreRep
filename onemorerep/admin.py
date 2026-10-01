"""Promote or demote an existing account without exposing role changes over HTTP."""
import argparse

from onemorerep.database import connect, transaction


def main():
    parser=argparse.ArgumentParser(description="Manage OneMoreRep account roles")
    parser.add_argument("username")
    parser.add_argument("role",choices=("user","admin"))
    args=parser.parse_args()
    with transaction() as conn:
        row=conn.execute("UPDATE users SET role=%s WHERE username=%s RETURNING username,role",(args.role,args.username)).fetchone()
    if not row:
        parser.error(f"No account found for username {args.username!r}")
    print(f"Updated @{row['username']} role to {row['role']}.")


if __name__ == "__main__":
    main()
