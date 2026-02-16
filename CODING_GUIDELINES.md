# Coding Guidelines

## Core Principles

### 1. Exit Early, Minimize Indentation

**Always exit loops and functions early** to keep code flat and readable. Avoid deep nesting.

#### ✅ GOOD - Exit Early
```python
def process_items(items):
    if not items:
        return
    
    for item in items:
        if not item.is_valid():
            continue
        
        if item.needs_special_handling():
            handle_special(item)
            continue
        
        process_normal(item)
```

#### ❌ BAD - Deep Nesting
```python
def process_items(items):
    if items:
        for item in items:
            if item.is_valid():
                if not item.needs_special_handling():
                    process_normal(item)
                else:
                    handle_special(item)
```

### 2. No Defensive Code

**Don't write defensive code.** Trust your callers. If bad input causes an error, let it fail loudly.

#### ✅ GOOD - Trust Your Callers
```python
def stash_apply(long_name):
    stashes = run(["git", "stash", "list"], capture_output=True)
    if not stashes:
        return
    
    stash_prefix = "-".join([STASH_PREFIX, long_name])
    
    for line in stashes.splitlines():
        if stash_prefix in line:
            stash_ref = line.split(":")[0]
            # ... apply the stash
            break
```

#### ❌ BAD - Defensive Checks
```python
def stash_apply(long_name):
    # Don't do this - unnecessary defensive checks
    if long_name is None:
        raise ValueError("long_name cannot be None")
    if not isinstance(long_name, str):
        raise TypeError("long_name must be a string")
    if len(long_name) == 0:
        raise ValueError("long_name cannot be empty")
    
    stashes = run(["git", "stash", "list"], capture_output=True)
    # ...
```

### 3. Guard Clauses Over If-Else Pyramids

Use guard clauses at the start of functions to handle edge cases and invalid states.

#### ✅ GOOD - Guard Clauses
```python
def merge(branch):
    conflicted = conflicted_paths()
    if not conflicted:
        print("✓ Merge completed with no conflicts.")
        return 0
    
    stage3 = conflicted_stage3_blobs()
    wrote, skipped = [], []
    
    for path in conflicted:
        blob_sha = stage3.get(path)
        if not blob_sha:
            skipped.append((path, "no stage-3 blob found"))
            continue
        
        # ... process the path
```

#### ❌ BAD - If-Else Pyramid
```python
def merge(branch):
    conflicted = conflicted_paths()
    if conflicted:
        stage3 = conflicted_stage3_blobs()
        wrote, skipped = [], []
        
        for path in conflicted:
            blob_sha = stage3.get(path)
            if blob_sha:
                # ... process the path (deeply nested)
            else:
                skipped.append((path, "no stage-3 blob found"))
    else:
        print("✓ Merge completed with no conflicts.")
        return 0
```

## Practical Rules

1. **Maximum nesting depth: 2-3 levels** - If you need more, refactor
2. **Return/continue/break early** - As soon as you know the outcome
3. **Fail fast** - Let exceptions bubble up naturally
4. **No null checks everywhere** - Only check at boundaries
5. **Positive conditions first** - Check for success, not failure

## Examples from This Codebase

### Good: Early Exit in Loop
```python
for line in stashes.splitlines():
    if stash_prefix in line:
        stash_ref = line.split(":")[0]
        # ... process this stash
        break
```

### Good: Guard Clause in Function
```python
def stash():
    status = run(["git", "status", "--porcelain"], capture_output=True)
    if not status:
        print("Nothing to stash.")
        return None
    
    # ... continue with stashing
```

### Good: Skip Invalid Items Early
```python
for filepath in staged_files_output.splitlines():
    if not filepath.strip():
        continue
    
    # ... process valid filepath
```

## When to Break These Rules

- **Public APIs**: Consider validation at public boundaries
- **User input**: Validate external/untrusted input
- **System boundaries**: Check file operations, network calls
- **Internal code**: Trust your own code

## Remember

> "Make the happy path obvious. Make the sad path disappear quickly."

Write code that reads top-to-bottom, left-to-right, with minimal indentation. The reader should understand the flow without mental stack management.

