#!/usr/bin/env python3
import re
import subprocess
import sys

from mo_files import File


# Regex pattern for git conflict markers:
# <<<<<<<\n...ours...\n=======\n...theirs...\n>>>>>>>
# Using DOTALL to match across newlines
CONFLICTS = re.compile(rb"<<<<<<<[^\n]*\n(.*?)\n=======\n(.*?)\n>>>>>>>[^\n]*", re.DOTALL,)


def sanitize_branch_token(branch):
    token = branch.strip().replace("/", "-").replace(" ", "_")
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.")
    return "".join(ch if ch in allowed else "-" for ch in token) or "branch"


def conflicted_paths():
    out = subprocess.run(["git", "diff", "--name-only", "--diff-filter=U"], capture_output=True, text=True).stdout.strip()
    return [line.strip() for line in out.splitlines() if line.strip()]


def split_conflict_markers(path):
    """
    Split a file with conflict markers into main (ours) and feature (theirs) versions.
    Uses regex to match (ours, theirs) conflict triples.
    Returns (main_content, feature_content) as bytes.
    """
    content = File(path).read_bytes()

    main_parts = []
    feature_parts = []
    last_end = 0

    # Find all conflict marker matches
    for match in CONFLICTS.finditer(content):
        main_parts.append(content[last_end : match.start()])
        feature_parts.append(content[last_end : match.start()])
        main_parts.append(match.group(1))
        feature_parts.append(match.group(2))
        last_end = match.end()

    # Add remaining content after last conflict
    main_parts.append(content[last_end:])
    feature_parts.append(content[last_end:])

    return b"".join(main_parts), b"".join(feature_parts)


def merge(branch):
    print(f"→ Merging branch '{branch}' into current branch…")
    merge_cmd = ["git", "merge", "--no-ff", "-m", f"merge {branch}", branch]
    merge_proc = subprocess.run(merge_cmd, capture_output=True, text=True)
    if merge_proc.returncode not in (0, 1):
        sys.stdout.write(merge_proc.stdout)
        sys.stderr.write(merge_proc.stderr)
        print("✖ Merge failed unexpectedly.", file=sys.stderr)
        return merge_proc.returncode

    conflicted = conflicted_paths()
    if not conflicted:
        if merge_proc.returncode == 0:
            print("✓ Merge completed with no conflicts.")
            return 0
        print("! Merge reported issues, but no conflicted files detected.")
        return 0

    print("\n⚠ Merge conflicts detected.")

    branch_token = sanitize_branch_token(branch)
    wrote, skipped = [], []

    # Process each conflicted file
    for path in conflicted:
        try:
            main_content, feature_content = split_conflict_markers(path)

            # Write feature copy with feature's version
            target = File(path).add_suffix(branch_token)
            target.write_bytes(feature_content)
            wrote.append((path, str(target.rel_path)))

            # Write main file with our version (clean, no markers)
            File(path).write_bytes(main_content)
        except Exception as e:
            skipped.append((path, f"error: {e!r}"))

    if wrote:
        print("  Wrote branch copies (overwrote if existed):")
        for src, dst in wrote:
            print(f"    • {src}  →  {dst}")
    if skipped:
        print("  Skipped:")
        for src, reason in skipped:
            print(f"    • {src}  ({reason})")

    # Stage all resolved files
    for path in conflicted:
        subprocess.run(["git", "add", path], check=True)

    for _, dst in wrote:
        subprocess.run(["git", "add", dst], check=True)

    # Complete the merge
    subprocess.run(["git", "commit", "-m", f"merge {branch}"], check=True)
    print("\n✓ Merge completed.")
    return 1
