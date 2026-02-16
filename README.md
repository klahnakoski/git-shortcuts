# More GIT

Some git shortcuts for better workflow management.

## Installation

### Development Installation (Recommended)

Install in editable mode so changes to the code are immediately reflected:

```bash
# Clone the repository
git clone https://github.com/klahnakoski/mo-git.git
cd mo-git

# Install in development mode
pip install -e .
```

This creates a `hit` command available system-wide.

### Regular Installation

```bash
pip install mo-git
```

### Verify Installation

```bash
hit --help
```

## Usage

### Safe checkout

Quickly checkout a branch without worrying about losing work. This is especially useful when you have a lot of uncommitted changes, and you want to switch to another branch to work on something else, but you don't want to lose your changes.

```commandline
hit checkout <branch>
```

### Merge without conflicts

Quickly merge a branch without worrying about conflicts.  Conflicted files will be added to the repo with the foreign branch name appended to the filename.  You can resolve conflicts later by comparing the files and selecting the changes you want to keep.

```commandline
hit merge <branch>
```

### Alias branch names

Corporate repositories often have long branch names that are difficult to remember and type. You can create aliases for these branch names to make it easier to work with them.

Create a new branch with an alias:

```commandline
hit checkout -b feature/user-authentication --as ua
```

Or create from a specific base branch:

```commandline
hit checkout -b hotfix/security-patch --as hsp --from main
```

Then checkout using the alias:

```commandline
hit checkout ua
```

## Features

- **Smart Stashing**: Automatically stashes changes when switching branches, including untracked files
- **Staged/Unstaged Preservation**: Restores files to their exact staged/unstaged state after switching
- **Conflict Resolution**: Creates `.branch-name` copies of conflicted files for easy comparison
- **Branch Aliases**: Short aliases for long branch names
- **Flexible Syntax**: Arguments can be in any order (e.g., `--as alias --from base -b name`)

## Examples

```bash
# Create branch without alias
hit checkout -b feature/new-feature

# Create branch with alias
hit checkout -b feature/user-authentication --as ua

# Create from specific base branch
hit checkout -b hotfix/critical --from production

# All options together (any order)
hit checkout -b feature/api-v2 --as api2 --from develop
hit checkout --as api2 --from develop -b feature/api-v2

# Switch to existing branch
hit checkout main
hit checkout ua  # using alias

# Merge with automatic conflict resolution
hit merge feature/new-api
```


