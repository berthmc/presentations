---
name: 840-generate-tests
description: >-
  Analyze code and generate comprehensive unit tests.
---

# Generate Tests

## Test Framework
- Project uses **pytest**.
- File locations: `tests/test_<module>.py`.
- Fixtures: `tests/conftest.py`.

## Test Generation
- Use AAA pattern (Arrange, Act, Assert).
- Ensure mock boundaries (e.g., Firestore, Gemini) are set up.
- Use `pytest-asyncio` for async tests.
- Parametrize inputs where applicable.
- Aim for Happy Path, Edge Case, and Error Case coverage.

## Execution
- Run tests using workspace-aware Docker exec commands.
  - E.g., `sudo docker compose exec backend pytest`
