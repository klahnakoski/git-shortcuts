# Agents

These guidelines apply to all agents working in this repo.

## Core Rules

- Exit early; keep nesting shallow.
- Do not write defensive code; let errors surface.
- Use regex when multiple `.find()` calls or index math would be needed.
- Prefer guard clauses over if/else pyramids.
- Do not add type annotations.

## Practical Limits

- Max nesting: 2-3 levels.
- Return/continue/break as soon as the outcome is known.
- Validate only at external boundaries (user input, I/O, APIs).

## Regex Guidance

Use regex for:
- Marker-based parsing (conflict markers, delimiters).
- Multiple substring extractions from the same content.

Avoid regex for:
- Single substring checks (`.find()` / `in`).
- Simple splits (`.split()`).
- Case-insensitive comparisons (`.lower()`).

## Reminder

Make the happy path obvious; make the sad path exit fast.
