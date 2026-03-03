#!/usr/bin/env python3
"""
CLI interface for mo-git commands.
Handles merge and checkout operations with branch aliases.
"""
import argparse
import subprocess
import sys

from git_shortcuts.git.merge import merge
from git_shortcuts.git.checkout import checkout_branch, checkout_new_branch_with_alias
from git_shortcuts.git.aliases import handle_alias, add_alias


def main():
    parser = argparse.ArgumentParser(
        prog="hit",
        description="Enhanced git workflow utilities",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=get_examples(),
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Merge command
    merge_parser = subparsers.add_parser("merge", help="Merge branch with smart conflict resolution")
    merge_parser.add_argument("branch", help="Branch to merge into current branch")

    # Checkout command
    checkout_parser = subparsers.add_parser("checkout", help="Switch branches with smart stashing")
    checkout_parser.add_argument("branch", help="Branch name or alias to checkout")
    checkout_parser.add_argument("-b", "--new-branch", metavar="NAME", help="Create new branch with NAME")
    checkout_parser.add_argument("--as", dest="alias", metavar="ALIAS", help="Alias for the new branch")
    checkout_parser.add_argument(
        "--from", dest="base", metavar="BASE", help="Base branch to branch from (name or alias)"
    )

    # Alias command
    alias_parser = subparsers.add_parser("alias", help="Create an alias for a branch")
    alias_parser.add_argument("branch", nargs="?", help="Branch name to alias (defaults to current branch)")
    alias_parser.add_argument("--as", dest="alias", metavar="ALIAS", required=True, help="Short alias for the branch")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    if args.command == "merge":
        return handle_merge(args)

    if args.command == "checkout":
        return handle_checkout(args)

    if args.command == "alias":
        return handle_alias(args)

    return 1


def handle_merge(args):
    """Merge a branch with conflict resolution that creates branch copies."""
    return merge(args.branch)


def handle_checkout(args):
    """Checkout branch with stash/unstash and alias support."""
    # Create new branch
    if args.new_branch:
        long_name = args.new_branch

        # If base branch specified, checkout base first
        if args.base:
            checkout_branch(args.base)

        # Create branch with or without alias
        checkout_new_branch_with_alias(long_name, args.alias)

        return 0

    # Checkout existing branch (or alias)
    checkout_branch(args.branch)
    return 0


def handle_alias(args):
    """Create an alias for an existing branch."""
    if not args.branch:
        # Use current branch
        result = subprocess.run(["git", "branch", "--show-current"], capture_output=True, text=True)
        args.branch = result.stdout.strip()
    else:
        # Check if branch exists
        result = subprocess.run(["git", "branch", "--list", args.branch], capture_output=True, text=True)
        if args.branch not in result.stdout:
            print(f"✘ Error: Branch '{args.branch}' does not exist.")
            return 1
    add_alias(args.branch, args.alias)
    print(f"✔ Alias '{args.alias}' created for branch '{args.branch}'.")
    return 0


def get_examples():
    return """
Examples:
  # Merge with conflict resolution
  hit merge feature/new-api

  # Create branch without alias
  hit checkout -b feature/user-authentication

  # Create branch with alias (any order)
  hit checkout -b feature/user-auth --as ua
  hit checkout --as ua -b feature/user-auth

  # Create from specific base (any order)
  hit checkout -b hotfix/security-patch --from main
  hit checkout --from main -b hotfix/security-patch

  # Create with alias and base (any order)
  hit checkout -b feature/api-v2 --as api2 --from develop
  hit checkout --as api2 --from develop -b feature/api-v2
  hit checkout --from develop -b feature/api-v2 --as api2

  # Switch to branch using alias
  hit checkout ua

  # Create alias for existing branch
  hit alias feature/very-long-branch-name --as vlbn

  # Create alias for current branch
  hit alias --as cb

Notes:
  - Merge creates .branch-name copies of conflicted files (their version)
  - Merge keeps ours version in original files and auto-commits
  - Checkout automatically stashes/unstashes changes
  - Checkout preserves staged/unstaged file status
  - Branch aliases are stored for quick access
"""


if __name__ == "__main__":
    sys.exit(main())
