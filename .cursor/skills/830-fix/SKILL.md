---
name: 830-fix
description: >-
  Apply automated fixes to code (linting, formatting, simple refactors).
---

# Auto-Fix Workflow

## Apply Safe Fixes
- Run `ruff check --fix <target>`
- Run `black <target>` (if configured)
- Run `isort <target>` (if configured)

## Apply Code Corrections
- Fix missing type hints.
- Replace `os.path` with `pathlib`.
- Remove unused imports.

## Verification
- Run tests and ensure code still compiles/runs.
