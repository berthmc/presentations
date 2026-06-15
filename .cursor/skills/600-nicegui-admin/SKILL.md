---
name: 600-nicegui-admin
description: >-
  NiceGUI 3.x component patterns used in the admin frontend: pages, components, shared layout,
  and reactive state patterns.
---

# NiceGUI Admin Frontend Conventions

## Entry Points
- Use `ui.run()` only in the main entry point (e.g., `frontend_main.py`), not inside individual page definitions.

## Shared Layouts
- Extract common page shells into shared layout components (e.g., a shared navigation/header function that wraps page content).

## State Management
- Use NiceGUI's reactive state capabilities (e.g., `ui.refreshable` or bindings) where possible to avoid manual DOM updates.
