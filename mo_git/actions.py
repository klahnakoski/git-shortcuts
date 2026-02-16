import subprocess
from datetime import datetime

from mo_git.aliases import load_aliases, add_alias
from mo_git.utils import run

STASH_PREFIX = "stash"




def stash():
    # Check if anything to stash
    status = run(["git", "status", "--porcelain"], capture_output=True)
    if not status:
        print("Nothing to stash.")
        return None

    # Create unique label
    branch = get_current_branch()
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    tag_name = "-".join(STASH_PREFIX, branch, timestamp)

    # Push stash with message
    run(["git", "stash", "push", "-u", "-m", tag_name])

    # Get most recent stash ref
    stash_ref = run(["git", "stash", "list"], capture_output=True).splitlines()[0].split(":")[0]

    # Create tag pointing to stash
    run(["git", "tag", tag_name, stash_ref])

    print(f"✔ Stashed as {stash_ref} and tagged as {tag_name}")
    return tag_name


def stash_pop(long_name):
    # Restore stash if it was created
    stashes = run(["git", "stash", "list"], capture_output=True)
    for line in stashes.splitlines():
        if line.startswith("-".join(STASH_PREFIX, long_name)):
            stash_ref = line.split(":")[0]
            run(["git", "stash", "pop", stash_ref])
            break


def get_current_branch():
    return run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True)


def checkout_new_branch_with_alias(long_name, alias):
    stash()
    run(["git", "checkout", "-b", long_name])
    add_alias(long_name, alias)
    print(f"✔ Created '{long_name}' and alias '{alias}'")


def checkout_branch(long_name_or_alias):
    long_name = load_aliases().get(long_name_or_alias, long_name_or_alias)

    stash()
    result = run(["git", "checkout", long_name], capture_output=True)
    if result:
        print(f"✔ Switched to branch '{long_name}'")
    else:
        print(f"✘ Branch '{long_name}' does not exist.")
