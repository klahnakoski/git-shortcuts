#!/usr/bin/env python3
import subprocess
import sys

from mo_files import add_suffix, File

from mo_git.utils import run


def sanitize_branch_token(branch):
    token = branch.strip().replace("/", "-").replace(" ", "_")
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.")
    return "".join(ch if ch in allowed else "-" for ch in token) or "branch"


def conflicted_stage3_blobs():
    out = run(["git", "ls-files", "-u"], capture_output=True)
    result = {}
    for line in out.splitlines():
        try:
            meta, path = line.split("\t", 1)
            mode, obj, stage = meta.split()
            if stage == "3":  # theirs
                result[path] = obj
        except ValueError:
            continue
    return result


def conflicted_paths():
    out = run(["git", "diff", "--name-only", "--diff-filter=U"], capture_output=True)
    return [line.strip() for line in out.splitlines() if line.strip()]


def write_blob_to_path(blob_sha, target_path):
    content = subprocess.run(["git", "show", blob_sha], capture_output=True, text=False).stdout
    File(target_path).write_bytes(content)


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

    stage3 = conflicted_stage3_blobs()
    branch_token = sanitize_branch_token(branch)
    wrote, skipped = [], []

    for path in conflicted:
        blob_sha = stage3.get(path)
        if not blob_sha:
            skipped.append((path, "no stage-3 blob found"))
            continue
        target = add_suffix(path, branch_token)
        try:
            write_blob_to_path(blob_sha, target)  # overwrites old copy
            wrote.append((path, str(target.rel_path)))
        except Exception as e:
            skipped.append((path, f"write error: {e!r}"))

    if wrote:
        print("  Wrote branch copies (overwrote if existed):")
        for src, dst in wrote:
            print(f"    • {src}  →  {dst}")
    if skipped:
        print("  Skipped:")
        for src, reason in skipped:
            print(f"    • {src}  ({reason})")

    # Resolve all conflicted files by keeping ours and stage them
    for path in conflicted:
        subprocess.run(["git", "checkout", "--ours", path], check=True)
        subprocess.run(["git", "add", path], check=True)

    # Stage the branch copies
    for _, dst in wrote:
        subprocess.run(["git", "add", dst], check=True)

    # Complete the merge
    subprocess.run(["git", "commit", "-m", f"merge {branch}"], check=True)
    print("\n✓ Merge completed.")
    return 1

