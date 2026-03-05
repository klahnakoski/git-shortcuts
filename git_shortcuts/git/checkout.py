from datetime import datetime

import subprocess

from git_shortcuts.git.aliases import load_aliases, add_alias
from git_shortcuts.utils import run

STASH_PREFIX = "stash"


def stash():
    # Check if anything to stash
    status = run(["git", "status", "--porcelain"], capture_output=True)
    if not status:
        branch = get_current_branch()
        print(f"No changes to stash on branch '{branch}'")
        return branch

    # Create unique label
    branch = get_current_branch()
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    tag_name = "-".join([STASH_PREFIX, branch, timestamp])

    # Save the current index state (staged files) before stashing
    # This creates a tree object representing the staged state
    index_tree = run(["git", "write-tree"], capture_output=True)

    # Push stash with message, including untracked files
    # This will stash all changes (staged, unstaged, and untracked)
    run(["git", "stash", "push", "-u", "-m", tag_name])

    # Get most recent stash ref
    stash_ref = run(["git", "stash", "list"], capture_output=True).splitlines()[0].split(":")[0]

    # Create tags: one for the stash, one for the index state
    run(["git", "tag", tag_name, stash_ref])
    run(["git", "tag", f"{tag_name}-index", index_tree])

    print(f"✔ Stashed as {stash_ref} and tagged as {tag_name}")
    return branch


def stash_apply(long_name):
    # Restore stash if it was created
    stashes = run(["git", "stash", "list"], capture_output=True)
    if not stashes:
        return

    stash_prefix = "-".join([STASH_PREFIX, long_name])

    for line in stashes.splitlines():
        if stash_prefix in line:
            break
    else:
        return

    stash_ref = line.split(":")[0]

    # Get the tag name from the stash message
    tag_name = line.split(":")[-1].strip().split()[-1]  # Extract tag from message
    index_tag = f"{tag_name}-index"

    # Check if we have a saved index state
    index_tree = run(["git", "rev-parse", "--verify", index_tag], capture_output=True, check=False)

    if not index_tree:
        return
    # First, apply the stash (this brings back all changes as unstaged)
    run(["git", "stash", "apply", stash_ref])

    # Now restore the staged state from the saved index tree
    # Get all files from the saved index
    staged_files_output = run(["git", "ls-tree", "-r", "--name-only", index_tree], capture_output=True)

    # For each file that was in the index, check if it differs from HEAD
    # If it does, it was staged and should be re-staged
    for filepath in staged_files_output.splitlines():
        if not filepath.strip():
            continue
        # Check if this file was actually changed in the index compared to HEAD
        # by comparing the index tree with HEAD
        file_in_index = run(["git", "ls-tree", index_tree, filepath.strip()], capture_output=True, check=False)
        file_in_head = run(["git", "ls-tree", "HEAD", filepath.strip()], capture_output=True, check=False)

        # If they differ, this file had staged changes
        if file_in_index != file_in_head:
            run(["git", "add", filepath.strip()], check=False)

    # Drop the stash and clean up tags
    run(["git", "stash", "drop", stash_ref])
    run(["git", "tag", "-d", tag_name], check=False)
    run(["git", "tag", "-d", index_tag], check=False)

    print(f"✔ Applied stash {stash_ref} and restored staged/unstaged state")


def get_current_branch():
    return run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True)


def checkout_new_branch_with_alias(long_name, alias=None):
    original_branch = stash()
    try:
        run(["git", "checkout", "-b", long_name], capture_output=True)
    except subprocess.CalledProcessError as e:
        print(f"✘ Failed to create branch '{long_name}': {e.stderr.strip()}")
        stash_apply(original_branch)
        return

    if alias:
        add_alias(long_name, alias)
        print(f"✔ Created '{long_name}' with alias '{alias}'")
    else:
        print(f"✔ Created '{long_name}'")


def checkout_branch(long_name_or_alias):
    long_name = load_aliases().get(long_name_or_alias, long_name_or_alias)

    original_branch = stash()
    result = run(["git", "checkout", long_name], capture_output=True, check=False)
    if not result:
        print(f"✔ Switched to branch '{long_name}'")
        stash_apply(long_name)
    else:
        print(f"✘ Branch '{long_name}' does not exist.")
        stash_apply(original_branch)
