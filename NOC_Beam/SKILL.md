---
name: noc-beam-design
description: Use this skill to generate well-branded interfaces and assets for NOC_Beam — a Windows desktop SIP softphone built on PySide6 + PJSIP, positioned as a modern replacement for CounterPath Eyebeam. Contains essential design guidelines, colors, type, fonts, assets, and a click-through UI kit that recreates the main window. Use for production code, prototypes, mockups, marketing surfaces, decks, and documentation.
user-invocable: true
---

Read the `README.md` file within this skill, and explore the other available files (`colors_and_type.css`, `assets/`, `preview/`, `ui_kits/noc_beam_app/`).

NOC_Beam is a technical tool — its visual language is dark Qt chrome with two signal colors (Beam Cyan `#7FD3FF` for RX/primary/registered, Beam Amber `#FFB86C` for TX/secondary). Cascadia Code mono is used for any SIP/wire content; Inter substitutes for Segoe UI for general UI. No gradients, no shadows, no emoji, no marketing-speak — labels and statuses only.

If creating visual artifacts (slides, mocks, throwaway prototypes, etc), copy assets out and create static HTML files for the user to view. Reuse the JSX components in `ui_kits/noc_beam_app/components.jsx` and `dialogs.jsx` — they are pixel-accurate to the source widgets in `src/noc_beam/ui/`. Import `colors_and_type.css` for all tokens.

If working on production code (Python/PySide6), read the rules in the README's **Visual Foundations** and **Content Fundamentals** sections to become an expert in designing with this brand. The token values in `colors_and_type.css` translate 1:1 to a Qt `dark.qss` stylesheet.

If the user invokes this skill without any other guidance, ask them what they want to build or design, ask some questions (target audience, surface type, whether it's in-product or marketing, whether real PJSIP integration is required), and act as an expert designer who outputs HTML artifacts _or_ production code, depending on the need.
