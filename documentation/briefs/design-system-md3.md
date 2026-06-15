# Material Design 3 — Sibling brands

This repo serves **two MD3 “sibling” brands** from one component layer. Static sites and the NiceGUI admin share token naming; admin palette wiring lives under `src/cms/frontend/shared/`.

**Related layout docs**

| Document | Scope |
|----------|--------|
| [`SITE_LAYOUT_AND_CSS.md`](SITE_LAYOUT_AND_CSS.md) | Global HTML regions, stylesheet chain, layout patterns, cross-site UX rules |
| [`SITE_LAYOUT_AND_CSS_MARKETS.md`](SITE_LAYOUT_AND_CSS_MARKETS.md) | Clear Signals hubs, live widgets, financial article editorial layout |

---

## Brands and entry CSS

| Brand | Domain feel | Body class | Token file |
|-------|-------------|------------|------------|
| **TheCloudArchitect** (tech) | Electric indigo + cyan accents | `body.site-tech` | `website/public/css/md3-tokens-tech.css` (`:root`) |
| **Clear Signals** (markets) | Terminal navy + bull/bear semantics | `body.site-markets` | `website/public/css/md3-tokens-markets.css` |

**Entry stylesheet:** `website/public/css/seo-theme.css` imports (in order):

1. `md3-tokens-tech.css`
2. `md3-base.css` — fonts (Inter + IBM Plex Serif display), spacing, reset, ticker carousel
3. `md3-tokens-markets.css` — overrides on `body.site-markets`
4. `md3-components.css` — chrome, article layout, MD3 components

**Page-level additions (not in the entry chain):**

| Stylesheet | When loaded |
|------------|-------------|
| `md3-homepage.css` | `homepage.html` |
| `md3-financial.css` | `financial_article.html` |

Deploy copies live under each domain’s `css/` folder; edit **`website/public/css/`** first, then sync.

---

## Semantic tokens (markets)

- `--md-sys-color-bull` — positive / risk-on accents  
- `--md-sys-color-bear` — negative / risk-off accents  
- `--md-sys-color-neutral-signal` — neutral / range-bound accents  

Use these instead of hard-coded greens/reds in **new** templates and CSS. Some legacy rules in `md3-financial.css` still use fixed hex — migrate when touching those selectors.

Tech brand also defines bull/bear/neutral on `:root` for shared components; markets overrides intensify terminal styling on `body.site-markets`.

---

## Dark mode

- `html[data-theme="dark"]` toggles dark palettes.
- Inline head script reads `localStorage.cms_theme` (`dark` | `light`) before first paint when the user has chosen explicitly; otherwise system preference applies until toggled.
- Header **theme toggle** (`#theme-toggle-btn`) persists choice to `localStorage`.
- NiceGUI admin mirrors via `app.storage.user['md3_dark']` + `ui.dark_mode()` (`src/cms/frontend/shared/theme.py`).

Test homepage widgets and financial badges in both modes (`md3-homepage.css`, `md3-tokens-markets.css` dark blocks).

---

## Typography

| Token | Use |
|-------|-----|
| `--font-family` | Inter — UI, body prose, tables |
| `--font-family-display` | IBM Plex Serif — hero titles, article H1 display |
| `--font-family-mono` | Tickers, numeric TA readouts |

Article templates apply display font to `.article-title`, `.home-hero h1`, `.md3-article-display` via `md3-base.css` / brand token files.

---

## Key components (static site)

| Class / pattern | Role |
|-----------------|------|
| `.md3-top-app-bar` + `.is-scrolled` | Elevated header on scroll |
| `.md3-card-elevated` / `.md3-card-outlined` / `.md3-card-filled-tonal` | Surfaces |
| `.md3-chip-assist` + `.pill--{type}` | Content-type pills |
| `.md3-chip-filter` | Homepage content-type filters |
| `.md3-share-fab` | Copy-link FAB on tech/generic articles |
| `.md3-toc-rail` + mobile `<dialog>` clone | TOC navigation (financial + tech) |
| `.md3-reading-progress` | Article reading progress bar |
| `.md3-skeleton` / `.md3-widget-skeleton` | Loading placeholders (markets widgets) |
| `.hs-tickers-carousel` | Horizontal, swipeable ticker strip (with `prefers-reduced-motion` fallback) |
| `.md3-icon-btn` + `.md3-menu-surface` | Theme toggle, language menu |
| `.md3-fab--extended` | Mobile “Launch ClearSignal Screener” CTA |

Full region map and block order: [`SITE_LAYOUT_AND_CSS.md`](SITE_LAYOUT_AND_CSS.md) §3.

---

## NiceGUI admin

- `src/cms/frontend/shared/theme.py` — `MD3AdminPalette` + `apply_admin_theme(brand=..., dark=...)`.
- `src/cms/frontend/shared/md3_layout.py` — `md3_admin_shell()`, `md3_page_column()` (header, drawer, brand select, dark toggle).

Admin UX should stay aligned with static-site token names (`--md-sys-color-primary`, etc.) even though markup differs.

---

## UX guidelines (implementation)

1. **Tokens first** — `--md-sys-*` and legacy `--color-*` aliases; no new raw hex in templates unless paired with a token fallback for dark mode.
2. **Icons** — Material Symbols (`material-symbols-outlined`) for simple actions; reserve inline SVG for brand marks (X, LinkedIn) where already established.
3. **Touch targets** — ≥ 48dp for primary actions (nav links, FAB, share, filters); use `:focus-visible` rings from `md3-base.css` / component classes.
4. **Motion** — honour `prefers-reduced-motion` for ticker marquee, skeleton shimmer, reading progress, and drawer transitions.
5. **Layout widths** — hubs/home `1200px`; article grid `--max-width-content` with `16rem` TOC at `≥1024px`.
6. **Markets editorial** — Key Takeaways above body; disclaimer extracted to sidebar (`markets_layout.py`); see markets layout doc.
7. **Live widgets** — SSR structure + skeletons + deferred hydration; avoid empty containers that reflow on fetch.
8. **Publishing** — after template/CSS changes, re-render via Cloud Run + drain (see `.cursor/publish-to-gcp.md` / `700-publish-gcp` skill); do not `gsutil rsync` HTML from a laptop as the primary path.

---

## Migration checklist

1. Prefer **CSS variables** (`--md-sys-*` / legacy `--color-*` aliases) over raw hex in templates.  
2. Prefer **Material Symbols** over new inline SVG for simple icons.  
3. Move page-specific CSS from template `<style>` blocks into `md3-homepage.css` or `md3-financial.css` when editing those pages.  
4. Touch targets **≥ 48dp** for primary actions; use `:focus-visible` rings (see `md3-base.css` / component classes).  
5. Respect **`prefers-reduced-motion`** for shimmer, ticker scroll, and progress animations.  
6. After template/CSS changes, follow **`.cursor/publish-to-gcp.md`** — Cloud Run re-render + drain — not root `gsutil rsync`.

---

## QA breakpoints

Smoke layouts at **390px**, **768px**, and **1280px** width on:

- Homepage (both domains where applicable)  
- One long article + financial article  
- NiceGUI `/tech` and `/admin/publish-queue`

Target **Lighthouse accessibility ≥ 95** on homepage + one article per domain when materially changing UI.

Also verify **dark mode** and **language menu** on mobile after chrome changes.
