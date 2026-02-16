#!/usr/bin/env python3
import subprocess
import sys

from mo_files import File

from mo_git.utils import run


def sanitize_branch_token(branch):
    token = branch.strip().replace("/", "-").replace(" ", "_")
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.")
    return "".join(ch if ch in allowed else "-" for ch in token) or "branch"


def conflicted_paths():
    out = run(["git", "diff", "--name-only", "--diff-filter=U"], capture_output=True)
    return [line.strip() for line in out.splitlines() if line.strip()]


def split_conflict_markers(path):
    """
    Split a file with conflict markers into main (ours) and feature (theirs) versions.
    Returns (main_content, feature_content) as bytes.
    Removes conflict markers and keeps clean hunks in both versions.
    """
    content = File(path).read_bytes()

    main_parts = []
    feature_parts = []
    i = 0

    while i < len(content):
        # Look for conflict marker start
        conflict_start = content.find(b"\n<<<<<<<", i)

        if conflict_start < 0:
            # No more conflicts - copy rest as-is to both
            main_parts.append(content[i:])
            feature_parts.append(content[i:])
            break

        # Copy non-conflicting content before this conflict
        main_parts.append(content[i:conflict_start + 1])  # include the newline
        feature_parts.append(content[i:conflict_start + 1])

        # Find the separator markers
        conflict_start += 1  # move past the newline
        ours_end = content.find(b"\n=======", conflict_start)

        if ours_end < 0:
            # Malformed conflict, just copy rest
            main_parts.append(content[conflict_start:])
            feature_parts.append(content[conflict_start:])
            break

        theirs_end = content.find(b"\n>>>>>>>", ours_end)

        if theirs_end < 0:
            # Malformed conflict
            main_parts.append(content[conflict_start:])
            feature_parts.append(content[conflict_start:])
            break

        # Extract ours and theirs content (without the markers)
        ours_content_start = conflict_start + 8 + content[conflict_start + 8:ours_end].find(b"\n") + 1
        ours_content = content[ours_content_start:ours_end]

        theirs_content_start = ours_end + 8 + content[ours_end + 8:theirs_end].find(b"\n") + 1
        theirs_content = content[theirs_content_start:theirs_end]

        # Add to appropriate versions
        main_parts.append(ours_content)
        feature_parts.append(theirs_content)

        # Skip to end of conflict marker and newline
        marker_end = theirs_end + content[theirs_end:].find(b"\n")
        if marker_end == theirs_end - 1:
            marker_end = len(content)
        else:
            marker_end += 1

        i = marker_end

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
            target = path.add_suffix(branch_token)
            File(target).write_bytes(feature_content)
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





