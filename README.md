# Git Shortcuts

Some Git shortcuts for better workflow management.

## Installation

You must have git installed and available in your PATH to use this tool.

### Install virtual environment

You may want a standalone virtual environment for this tool, or you can install it globally.  To create a virtual environment off your home directory, run:

```commandline
python -m venv ~/.venv
source ~/.venv/bin/activate
```
### Install git-shortcuts

```bash
pip install git-shortcuts
```
### Add to PATH

If you installed globally, the `gscut` command should already be available. If you installed in a virtual environment, you need to add the virtual environment's `bin` directory to your PATH. For example, if you created a virtual environment at `~/.venv`, you can add the following line to your shell profile (e.g., `~/.bashrc` or `~/.zshrc`):

```commandline

```


### Verify Installation

```bash
gscut --help
```

## Usage

### Safe checkout

Quickly checkout a branch without worrying about losing work. This is especially useful when you have a lot of uncommitted changes, and you want to switch to another branch to work on something else, but you don't want to lose your changes.

```commandline
gscut checkout <branch>
```

### Merge without conflicts

Quickly merge a branch without worrying about conflicts.  Conflicted files will be added to the repo with the foreign branch name appended to the filename.  You can resolve conflicts later by comparing the files and selecting the changes you want to keep.

```commandline
gscut merge <branch>
```

### Alias branch names

Corporate repositories often have long branch names that are difficult to remember and type. You can create aliases for these branch names to make it easier to work with them.

Create a new branch with an alias:

```commandline
gscut checkout -b feature/user-authentication --as ua
```

Or create from a specific base branch:

```commandline
gscut checkout -b hotfix/security-patch --as hsp --from main
```

Create an alias for an existing branch:

```commandline
gscut alias <branch name> --as <short name>
```

Or create an alias for the current branch:

```commandline
gscut alias --as <short name>
```

Then checkout using the alias:

```commandline
gscut checkout ua
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
gscut checkout -b feature/new-feature

# Create branch with alias
gscut checkout -b feature/user-authentication --as ua

# Create from specific base branch
gscut checkout -b hotfix/critical --from production

# All options together (any order)
gscut checkout -b feature/api-v2 --as api2 --from develop
gscut checkout --as api2 --from develop -b feature/api-v2

# Switch to existing branch
gscut checkout main
gscut checkout ua  # using alias

# Merge with automatic conflict resolution
gscut merge feature/new-api

# Create alias for existing branch
gscut alias feature/very-long-branch-name --as vlbn

# Create alias for current branch
gscut alias --as cb
```


## Development Installation

Install in editable mode so changes to the code are immediately reflected:

```bash
# Clone the repository
git clone https://github.com/klahnakoski/git-shortcuts.git
cd git-shortcuts

# Install in development mode
pip install -r tests/requirements.txt
pip install -r packaging/requirements.txt
pip-compile packaging/requirements.txt -o packaging/requirements.txt


pip install -e .
```

This creates a `gscut` command available system-wide.
