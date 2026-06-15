"""MD3 theme tokens for NiceGUI admin-style UI."""

from nicegui import ui

MD3_PALETTE = {
    "primary": "#3751ff",
    "on_primary": "#ffffff",
    "secondary": "#4f46e5",
    "surface": "#eef2ff",
    "surface_container": "#ffffff",
    "on_surface": "#0f172a",
    "on_surface_variant": "#475569",
    "outline": "#e2e8f0",
    "error": "#dc2626",
}


def apply_md3_theme() -> None:
    """Apply MD3-inspired Quasar theme variables."""
    ui.colors(
        primary=MD3_PALETTE["primary"],
        secondary=MD3_PALETTE["secondary"],
        accent=MD3_PALETTE["secondary"],
        positive="#16a34a",
        negative=MD3_PALETTE["error"],
        info=MD3_PALETTE["primary"],
        warning="#f59e0b",
    )
    ui.add_head_html(
        """
        <style>
          body { background: #eef2ff; color: #0f172a; font-family: Inter, system-ui, sans-serif; }
          .md3-card { border-radius: 16px; box-shadow: 0 1px 3px rgba(15,23,42,.12); background: #fff; }
          .md3-title { font-family: 'IBM Plex Serif', Georgia, serif; font-weight: 700; }
        </style>
        """
    )
