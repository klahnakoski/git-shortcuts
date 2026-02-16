# Quick Start Guide

## Installation on Mac

### Method 1: Development Installation (Recommended)

```bash
# Navigate to the project directory
cd /path/to/mo-git

# Install in development mode
pip3 install -e .

# Verify installation
hit --help
```

This installs the `hit` command system-wide while keeping it linked to your source code. Any changes you make to the code will be immediately reflected.

### Method 2: System-wide Installation

```bash
# Navigate to the project directory
cd /path/to/mo-git

# Install
pip3 install .

# Verify installation
hit --help
```

### Method 3: Use the Installation Script

```bash
cd /path/to/mo-git
chmod +x install.sh
./install.sh
```

## First Steps

### 1. Create a new branch with an alias

```bash
hit checkout -b feature/user-authentication --as ua
```

### 2. Make some changes and switch branches

```bash
# Make changes to files (staged and unstaged)
# The stash will automatically preserve your work

hit checkout main
```

Your changes are stashed and will be restored when you return:

```bash
hit checkout ua  # Use the alias!
```

### 3. Merge with automatic conflict resolution

```bash
hit checkout main
hit merge ua
```

If there are conflicts:
- Original files keep "ours" version
- `.ua` suffixed files contain "theirs" version
- Compare and merge manually as needed

## Uninstalling

```bash
pip3 uninstall mo-git
```

## Troubleshooting

### Command not found after installation

Make sure pip's bin directory is in your PATH:

```bash
# Add to ~/.zshrc or ~/.bashrc
export PATH="$HOME/Library/Python/3.x/bin:$PATH"
```

Or use the full path:

```bash
python3 -m mo_git.cli --help
```

### Permission errors

Use `--user` flag:

```bash
pip3 install --user -e .
```

