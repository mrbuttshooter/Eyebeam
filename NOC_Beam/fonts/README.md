# Fonts

NOC_Beam's intended runtime fonts:

| Role | Intended | Used in this design system | Notes |
|---|---|---|---|
| UI / display | **Segoe UI** (Windows native) | **Inter** (Google Fonts) | ⚠️ substitution — Segoe UI is not webfontable. Visually closest free alternative. If you ship a NOC_Beam web property, license a more accurate substitute or fall back to system UI. |
| Mono / trace | **Cascadia Mono** (set explicitly in `src/noc_beam/ui/trace_view.py` line ~30) | **Cascadia Code** (Google Fonts) | Same family by Microsoft — Cascadia Code is the public superset of Cascadia Mono (adds ligatures, otherwise identical). |

Both fonts are pulled in via the `@import` at the top of `colors_and_type.css`. No local font files are stored in this repo — change to a self-hosted `@font-face` setup if offline-rendering of design artifacts becomes necessary.

## Ask

If the team has a licensed Segoe UI alternative (e.g. **Segoe UI Variable** for Windows 11 work, or an internal corporate font), drop the WOFF2 files into this folder and we'll wire them up.
