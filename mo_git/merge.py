#!/usr/bin/env python3
import argparse
import subprocess
import sys
from pathlib import Path

from mo_git.utils import run


def ensure_git_repo():
    try:
        run(["git", "rev-parse", "--is-inside-work-tree"])
    except subprocess.CalledProcessError:
        print("Error: not inside a Git repository.", file=sys.stderr)
        sys.exit(2)


def sanitize_branch_token(branch):
    token = branch.strip().replace("/", "-").replace(" ", "_")
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.")
    return "".join(ch if ch in allowed else "-" for ch in token) or "branch"


def insert_branch_before_suffix(p, branch_token):
    parent = p.parent
    name = p.name
    if "." in name:
        if name.startswith(".") and name.count(".") == 1:
            new_name = f"{name}.{branch_token}"
        else:
            stem = name.split(".", 1)[0]
            rest = name[len(stem) :]  # includes the dot and the rest
            new_name = f"{stem}.{branch_token}{rest}"
    else:
        new_name = f"{name}.{branch_token}"
    return parent / new_name


def conflicted_stage3_blobs():
    out = run(["git", "ls-files", "-u"]).stdout
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
    out = run(["git", "diff", "--name-only", "--diff-filter=U"]).stdout
    return [line.strip() for line in out.splitlines() if line.strip()]


def write_blob_to_path(blob_sha: str, target_path: Path):
    content = run(["git", "show", blob_sha]).stdout.encode("utf-8", "surrogatepass")
    target_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = target_path.with_suffix(target_path.suffix + ".tmp.write")
    with open(tmp, "wb") as f:
        f.write(content)
    tmp.replace(target_path)  # atomic overwrite


def merge_and_extract(branch: str) -> int:
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

    stage3 = conflicted_stage3_blobs()
    branch_token = sanitize_branch_token(branch)
    wrote, skipped = [], []

    for path in conflicted:
        blob_sha = stage3.get(path)
        if not blob_sha:
            skipped.append((path, "no stage-3 blob found"))
            continue
        original = Path(path)
        target = add_suffix(path, branch_token)
        try:
            write_blob_to_path(blob_sha, target)  # overwrites old copy
            wrote.append((path, str(target)))
        except Exception as e:
            skipped.append((path, f"write error: {e!r}"))

    print("\n⚠ Merge conflicts detected.")
    if wrote:
        print("  Wrote branch copies (overwrote if existed):")
        for src, dst in wrote:
            print(f"    • {src}  →  {dst}")
    if skipped:
        print("  Skipped:")
        for src, reason in skipped:
            print(f"    • {src}  ({reason})")

