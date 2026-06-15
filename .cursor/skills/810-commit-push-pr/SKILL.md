---
name: 810-commit-push-pr
description: >-
  Commit changes, push to remote, and open a Pull Request.
---

# Commit, Push, and Open PR

When the user says `/commit-push-pr`, execute this workflow using **PowerShell** syntax.

## 1. Pre-flight Checks

```powershell
git status
git branch --show-current
```

- If working tree is clean → stop: "No changes to commit."
- Default working branch is **`dev`**. If on `main`, create or switch to `dev` before committing.

## 2. Security Check Gate

When the security-auditor MCP is available on port 3001, invoke **`check_code_quality`** on each changed `*.py` file. Pass **`file_path`** as `/project/cms/src/...` (see `900-security-mcp-paths.mdc`). If MCP is unavailable, state that and continue.

## 3. Quality Check (optional)

Ask the user if they want lint/tests before committing.

```powershell
# Lint (host venv)
ruff check src/ tests/

# Tests inside Docker (preferred)
sudo docker compose exec backend python -m pytest tests/ -v --tb=short
```

## 4. Analyze Changes & Commit

```powershell
git diff HEAD
```

Generate a concise **conventional commit** message (`feat:`, `fix:`, `refactor:`, `docs:`, `chore:`, `test:`, `style:`). Display for user confirmation, then:

```powershell
git add -A
git commit -m "<approved-message>"
```

## 5. Push & PR

```powershell
git push
# If no upstream: git push -u origin dev
gh pr create --fill --base main
```

- If PR already exists: `gh pr view --json url`
- Never force-push without explicit user approval.
- If push rejected: `git pull --rebase` then retry.
