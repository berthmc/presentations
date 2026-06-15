---
name: 800-code-review
description: >-
  Analyze code for redundancy, bad practices, and improvement opportunities using
  automated security/quality scanning (MCP) and AI analysis.
---

# Code Review and Quality Analysis

## Automated Security & Quality Scanning
For Python file reviews, ALWAYS use the MCP Security Scanner first.
- The project uses the **security-auditor MCP server** (e.g. on port 3001).
- Call `check_code_quality` and `scan_python_security`.
- Note container paths vs host paths (refer to the `900-security-mcp-paths` rule).

## Analysis Categories
- **Redundant Code Detection**: Duplicate code patterns, unused code, orphan files, over-abstraction.
- **Code Smells**: Long functions, God classes, naming issues.
- **Python Anti-Patterns**: Mutable defaults, bare except, string concat in loops.
- **Async Issues**: Blocking calls, sequential awaits.
