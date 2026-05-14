# NOC_Beam Design System

Design system for **NOC_Beam** — a professional Windows desktop SIP softphone built with Python, PySide6 (Qt), and PJSIP. NOC_Beam is positioned as a modern, polished replacement for CounterPath **Eyebeam** for SIP/VoIP testing and internal company telephony.

This system captures the visual + interaction vocabulary of the app — dark technical chrome, an icon-rail + content + drawer composition, RX/TX color coding throughout — so future surfaces (in‑app screens, marketing pages, decks, docs) stay coherent with the engineering tool the user already knows.

## Sources

- **Codebase:** `mrbuttshooter/Eyebeam` on GitHub — branch `claude/eyebeam-sip-testing-j5qRA`
  Path: <https://github.com/mrbuttshooter/Eyebeam/tree/claude/eyebeam-sip-testing-j5qRA/python-app>
  Specifically the `src/noc_beam/ui/` package (PySide6 widgets) and `src/noc_beam/sip/trace.py` (color choices).
- No Figma file, no separate design tokens, no shipped stylesheet (`dark.qss` is referenced from `app.py` but absent from the repo). Visual treatment in this system is **synthesized** from the Qt widget structure plus the inline colors in `trace_view.py`. If you have the original `dark.qss`, drop it into the project and we will reconcile.

Browse the source repo to do better/deeper recreations: the widget files (`dialpad.py`, `call_widget.py`, `trace_view.py`, `main_window.py`, `account_dialog.py`, `settings_dialog.py`) are the highest‑signal references.

## Product summary

| | |
|---|---|
| **Name** | NOC_Beam (written with the underscore — it's a wordmark, not a typo) |
| **Category** | Desktop SIP softphone for testing & internal telephony |
| **Platform** | Windows 10/11 primary; Linux/macOS as dev targets |
| **Stack** | Python 3.11 · PySide6 · PJSIP (pjsua2) · PyInstaller single‑file `.exe` |
| **Audience** | NOC engineers, VoIP/SIP integrators, network ops teams |
| **Tone** | Plain, technical, no marketing fluff |
| **Differentiation vs. Eyebeam** | Modern Qt UI · dark theme · live SIP trace viewer · multi‑account · TLS+SRTP · single‑file portable executable |

## v2 design direction

The v1 UI kit reproduced the Eyebeam layout almost verbatim: a single window split into accounts rail + dialpad + tabs. That was honest but conservative. **v2 reorganises the app around an icon rail** so each destination is a focused view, and introduces a slide‑out drawer that surfaces the live SIP trace next to whatever else the user is doing.

```
┌────────────────────────────────────────────────────────────────┐
│  Wordmark   ●  active account   dial›  …                   ─ ▢ ✕
├────┬───────────────────────────────────────────┬───────────────┤
│ ☎  │                                           │  Live trace   │
│ ⌁  │              Active view                  │  ● LIVE       │
│ ⌚ │           (Calls · idle/active/multi      │               │
│ ⎘  │            · Trace · History · Accts     │   TX → INVITE │
│ ⚙  │            · Settings)                    │   RX ← 100    │
│    │                                           │   RX ← 180    │
│ ●  │                                           │   RX ← 200 OK │
│4/4 │                                           │               │
└────┴───────────────────────────────────────────┴───────────────┘
```

- **Icon rail** (left, 64px). Five destinations + a permanent registration‑status pill at the foot. The pill is the only persistent surface that shows "are my accounts registered" — it replaces v1's chrome‑hugging status bar.
- **Content** (centre). One destination at a time. Calls is the default; its header has a segmented control to toggle between idle / active / multi states so the user can verify each is correctly wired up.
- **Drawer** (right, 360px, optional). Houses the live SIP trace for the current call. Slides in/out at 240ms ease‑out. Default closed for idle, default open during a call.
- **Title bar** (top, 44px). Wordmark · active‑account chip · `⌘K` dial‑by‑URI bar · window controls. The dial bar is global and always focusable — `⌘K` from anywhere drops you in to type a SIP URI.

**Three incoming‑call surfaces.** A SIP INVITE arrives in one of three contexts, each with its own surface (see `ui_kits/noc_beam/incoming.html`):

1. **In‑app focus** — full‑window overlay with caller name, URI, history hint, and three actions: Accept / Accept & trace / Decline.
2. **Windows toast** — OS‑native notification in the bottom‑right when the app is minimised or blurred.
3. **Floating PiP** — always‑on‑top mini window (280×80) shown while on a call when the user collapses NOC_Beam to give another app focus.

**The Settings IA** is reorganised into four sub‑groups (SIP / Device / App / Advanced) with a tokenised setting‑row pattern: every row shows the human label, the underlying config key (e.g. `audio.input.gain_db`), the control, and a short help string. This makes the settings file copy‑pasteable into bug reports and lets power users find a key by its name.

## Content Fundamentals

NOC_Beam copy is **technical, terse, sentence‑case, and second‑person ("you") only when strictly necessary**. The audience is engineers — they want the label, not the explanation.

### Tone

- **Functional.** Every visible string is a label or a status. No taglines, no "let's", no marketing.
- **Plain English.** "Add account", not "Create a new account profile". "Hang up", not "End the active call session".
- **SIP/VoIP vocabulary is used directly.** REGISTER, INVITE, 401, SRTP, STUN, DTMF, codec, transport, registrar — engineers know these terms; do not gloss them.
- **No emoji.** Anywhere. The product is a network tool, not a chat app.
- **No exclamation marks.** Errors are stated, not yelled.

### Casing & grammar

- **Sentence case** for everything: toolbar actions ("Add account", "Edit account", "Remove account"), tab labels ("Call", "SIP trace"), button labels ("Answer", "Reject", "Hang up", "Hold", "Mute"), dialog titles ("SIP account", "Settings"), form labels ("Display name", "Auth user (if different)", "Outbound proxy (optional)"). Title Case is reserved for proper nouns only (PCMU, G.711, NOC_Beam itself).
- **Brand:** **NOC_Beam** — underscore preserved, two capitals. Never "NocBeam", "Noc Beam", or "noc_beam" in user‑facing copy. Lower‑case `noc_beam` is acceptable in code/package names.
- **Acronyms stay upper:** SIP, TLS, SRTP, DTMF, NAT, STUN, TURN, ICE, RFC, URI, RX, TX, NOC.
- **Numbers** are bare ("8000 Hz", "Codec priority 0=off, 255=max"), no spelling out.

### Voice — examples lifted from the source

```
Toolbar:      Add account · Edit account · Remove account · Settings
Status bar:   Starting…   SIP endpoint started   Settings applied
              [Alice] registration: 200 OK
              Endpoint error: failed to bind port 5060
Dialog title: SIP account   ·   Settings
Form label:   Auth user (if different)
              Outbound proxy (optional)
              STUN server (optional)
Placeholder:  Enter number or SIP URI
              Filter (e.g. INVITE, 401, alice@example.com)
Trace line:   [14:22:07.413] RX  sip:proxy.example.com:5060
              INVITE sip:alice@example.com SIP/2.0
Confirm:      Remove alice@example.com?
```

Notice: the ellipsis is a single character `…` not three dots; the registration log embeds the friendly name in brackets; placeholders cite real example values (`INVITE, 401, alice@example.com`) so engineers immediately recognize what goes there.

### What NOT to write

- ❌ "Welcome to NOC_Beam!" → ✅ (no welcome — open straight into the workspace)
- ❌ "Oops, something went wrong 😬" → ✅ "Endpoint error: failed to bind port 5060"
- ❌ "Click here to add your first account" → ✅ "Add account" (the button speaks for itself)
- ❌ "Awesome! Your call is connected." → ✅ "CONFIRMED (200 OK)"

## Visual Foundations

NOC_Beam's visual language is **dark technical chrome with two signal colors**: sky cyan for incoming/RX flow, warm pumpkin for outgoing/TX flow. Everything else is a neutral on a near‑black background.

### Mood

Imagine the SIP trace pane of a serious VoIP testing tool — terminal‑adjacent, monospace‑heavy, color used **only where it carries meaning** (direction, registration state, error). The aesthetic neighbors are: Dracula, GitHub Dark, the JetBrains "Darcula" theme, Wireshark on a dark color profile. Pleasant to look at for eight hours; not flashy.

### Colors

- **Backgrounds:** four steps from window chrome (`#0E1116`) up through main content (`#161B22`), panels (`#1F252E`), and raised/hover (`#2A323D`). All cool, slightly blue‑tinted — never warm grays, never pure `#000`.
- **Borders:** `#2A3340` for default, `#3B4654` for emphasized — kept very subtle; the UI relies on background steps more than on lines.
- **Text:** `#E6EDF3` primary · `#B7C0CC` secondary · `#7C8696` muted/tertiary. Pure white is never used — too harsh against the near‑black bg.
- **Signal pair (the brand colors):**
  - `#7FD3FF` "Beam Cyan" — RX, incoming calls, primary action, links, registered status, focus rings.
  - `#FFB86C` "Beam Amber" — TX, outgoing calls, secondary highlights, DTMF tones, warnings.
  These are the **only two saturated colors** that appear at any meaningful surface area. They were chosen in `trace_view.py` for the direction indicators and the whole system flows from that pair.
- **Semantic colors:** `#66D19E` success (registered, call active) · `#FF5C7A` danger (hang up, error, rejection) · `#F0C36D` warning · `#7FD3FF` info.
- **No gradients.** Anywhere. Flat fills only. The four background steps do the elevation work that gradients usually do.

### Type

- **UI / display:** Segoe UI on Windows (system native). Substitute **Inter** elsewhere — flagged.
- **Mono:** Cascadia Mono, explicitly set in `trace_view.py`. Used for the SIP trace, codec IDs, SIP URIs, and any wire content. Available as **Cascadia Code** on Google Fonts and used here.
- **Sizes:** 9pt mono in the trace (per source), ~13–14px for general UI, 18pt in the dial entry, 11–12px for status bar / secondary text. There is no display/marketing size — this is a tool, not a landing page.
- **Numerals:** tabular for any column of numbers (codec priorities, ports, latencies).

### Spacing & layout

- 4‑pixel base grid. The dialpad grid uses 6px gutters between keys (`grid.setSpacing(6)`).
- **Density is high.** Form rows pack tight — this is a power‑user tool, not a phone app. ~32px row height; settings rows use a fixed `key | value | help` 3‑column grid.
- **Composition.** v2 uses an **icon rail + content + optional drawer** layout (see "v2 design direction" above). v1's splitter is gone; the rail replaces the "narrow left list of accounts" and the drawer replaces "tabbed right pane with Call/Trace". The trace is now a contextual companion to whatever view the user is in, not a competing tab.

### Borders, corners, shadow, elevation

- **Corner radii:** 2px on most controls (inputs, buttons, list rows), 4px on the dialpad keys, 6px on dialogs and the dialpad entry field. Nothing pill‑shaped, nothing fully round. Hard, technical corners.
- **Shadows:** none, or so subtle they're invisible. Elevation is signaled by background step, not by drop shadow. The one exception is the active call widget which gets a 1px cyan border to lift it visually.
- **Borders:** 1px solid `#2A3340` is the default; `#3B4654` on hover; `#7FD3FF` on focus or active call.

### Backgrounds, imagery, illustration

- **No imagery, no illustrations, no photos, no gradients.** This is a CLI‑adjacent tool — backgrounds are solid fills from the four‑step neutral ramp. If a marketing surface is ever made, it should lean into terminal aesthetics (a literal SIP trace as the hero) rather than abstract product imagery.
- **No textures.** Flat throughout.

### Animation

Minimal and functional. **Full spec lives in [motion.md](motion.md); the preview card under "Motion" in the Design System tab demonstrates each primitive.**

Four categories, three durations, one curve:

- **Feedback** (80ms) — hover, focus, press. Press scale (0.97) reserved for keypads.
- **Transition** (160ms) — tab and segment swaps, toggle knob, slider knob.
- **Reveal** (240ms) — drawer slide, toast slide‑in, modal scale‑in.
- **Status** (looping) — `● LIVE` dot (1.4s), incoming‑call ring (1.6s × 2 offset).

House curve is `cubic-bezier(0.2, 0, 0, 1)`. The SIP trace itself **never animates** — new messages append without enter motion, since the wire didn't animate either. All loops honour `prefers-reduced-motion`.

No bounces. No springs. No parallax. No anything that draws attention away from a SIP message.

### Hover / press / focus

- **Hover:** background lifts by one step (`#1F252E` → `#2A323D`) — never an opacity change, never a color shift on the foreground.
- **Press:** background drops one step (`#161B22`) and the label nudges down 1px. Buttons feel mechanical.
- **Focus:** 1px solid `#7FD3FF` outline at 2px offset. Visible, never blurred or glowing.
- **Disabled:** 50% opacity, no other change.

### Transparency & blur

- **Not used.** No frosted glass. No translucent panels. Every surface is opaque. Qt's native blur would be inconsistent across Windows versions anyway, and the brand is "honest tool" not "modern OS demo".

### Cards & containers

- Cards do not have shadows. They are demarcated by a one‑step background lift plus a 1px border at `#2A3340`. Corner radius 4px. Internal padding 12–16px.

### Layout rules / fixed elements

- **Title bar** is fixed at the top (44px), carries wordmark, active‑account chip, global dial bar (`⌘K`), and window controls.
- **Icon rail** is fixed at the left (64px), non‑resizable. Five destinations + a registration‑status pill at the foot.
- **Drawer** (right, 360px) is the only resizable region. Slides in/out on demand.
- **No status bar at the bottom of the window.** v1's status bar was replaced by the rail's status pill and per‑surface inline state (e.g. the hero block on the Calls view).

## Accessibility

NOC_Beam runs on the on‑call NOC desk at 03:00 UTC. **Full commitment in [a11y.md](a11y.md).** Headlines:

- All text/signal pairs clear **WCAG 2.2 AA** at used size.
- Colour is never the only carrier of state. RX/TX are labelled in addition to coloured; registration state shows `REGISTERED` plus the dot.
- Every interactive surface is keyboard‑operable. Notable shortcuts: `⌘K` dial bar, `⌘1`–`⌘5` rail destinations, `↵`/`⌘↵` accept call (`⌘↵` accepts and opens trace), `Esc` decline/cancel, `M` mute, `H` hold, `End` hang up.
- The trace is **real selectable text**, never a canvas. Copy‑pasteable straight into a ticket.
- Dark by default. Light + high‑contrast modes are open work — flagged in `a11y.md`.

## Iconography

The source ships **no icons or visual assets** — the codebase references `assets/icon.ico` and `ui/resources/icon.ico` but they don't exist in the tree. Toolbar actions in `main_window.py` are created with text labels only (`QAction("Add account")`, etc.) — there is no `setIcon` call anywhere.

### Approach

- **Lucide** is used throughout this design system as the icon set — open‑source, MIT‑licensed, 1.5px stroke, technical/utility feel that matches the brand. Loaded from CDN: `https://unpkg.com/lucide-static@latest`.
- **Flagged as substitution.** If you have a preferred icon set or a `.ico` for the app, drop it into `assets/` and we'll switch over.
- **No emoji.** Reaffirming the content rule — emoji are not used as iconography either.
- **No unicode glyphs as icons** except in two tightly‑scoped cases observed in `call_widget.py`: `→` for outgoing call peers, `←` for incoming. Those are intentionally typographic, not iconic.
- **PNG vs SVG:** SVG only. The app would consume `.ico` for its window chrome, but the in‑app surface uses inline SVG (or web‑font icons in HTML mockups).

### Icon usage in this system

| Action | Icon (Lucide) |
|---|---|
| Add account | `user-plus` |
| Edit account | `pencil` |
| Remove account | `trash-2` |
| Settings | `settings` |
| Call | `phone` |
| Hang up | `phone-off` |
| Answer | `phone-incoming` |
| Reject | `phone-missed` |
| Hold | `pause` |
| Mute | `mic-off` |
| RX (trace) | `arrow-down-to-line` |
| TX (trace) | `arrow-up-from-line` |
| Filter | `filter` |
| Clear | `x` |

## Index

```
README.md                  ← you are here
SKILL.md                   ← agent skill manifest
motion.md                  ← motion spec (durations, curves, categories)
a11y.md                    ← accessibility commitment (contrast, kbd, SR, targets)
colors_and_type.css        ← CSS variables for color + type (base + semantic + motion)
fonts/                     ← webfonts (Inter, Cascadia Code) and notes
assets/
  logo-wordmark.svg          NOC_Beam wordmark (canonical, "The Trace")
  logo-mark.svg              square mark for app icons (canonical, beam line)
  explorations/              alternates from the wordmark + mark exploration
preview/                   ← cards rendered into the Design System tab
  palette-neutrals.html · palette-signal.html · palette-semantic.html
  type-display.html · type-body.html · type-mono.html
  spacing-radii.html · spacing-elevation.html
  components-buttons.html · components-inputs.html · components-dialpad.html
  components-list.html · components-tabs.html · components-statusbar.html
  components-trace.html
  iconography.html · logo.html
  logo-wordmark-exploration.html  ← A/B/C wordmark directions, light + dark
  logo-mark-exploration.html      ← 1/2/3 mark directions, light + dark
  motion.html                     ← motion primitives in motion
ui_kits/
  noc_beam/                 v2 UI kit — icon rail + content + drawer
    styles.css               shared component styles
    index.html               main shell + Calls view (idle/active/multi)
    incoming.html            incoming‑call surfaces (focus / toast / PiP)
    settings.html            Settings shell with Audio sub‑section open
    account-dialog.html      Add SIP account modal (tabbed, OPTIONS probe)
slides/
  index.html                 8-slide internal-deck template in the SIP-trace aesthetic
  deck-stage.js              slide-deck shell (scaling, nav, print-to-PDF)
```

## Caveats

- **`dark.qss` was not in the repo.** Color values were synthesized from the two hex codes in `trace_view.py` (`#7FD3FF`, `#FFB86C`) plus the README's "modern dark theme" framing. The full palette here is design judgement, not a recovered source.
- **v2 is a designed direction, not yet code.** The v1 click‑thru that aped Eyebeam's layout has been removed. v2 (icon rail + drawer) is mocked here as static HTML — when the PySide6 implementation lands, it should be reconciled against `ui_kits/noc_beam/*.html`.
- **Three wordmark + three mark directions are presented as options.** "The Trace" wordmark and "Beam line" mark are wired in as canonical (`assets/logo-wordmark.svg`, `assets/logo-mark.svg`); the alternates sit in `assets/explorations/` and `preview/logo-*-exploration.html`. **Tell me which you want and I'll promote it.**
- **Segoe UI is the intended Windows UI font** but is not webfontable. **Inter** is used as a near‑equivalent for the HTML system. Cascadia Mono is replaced with **Cascadia Code** (the same family, slightly different name, free on Google Fonts).
- **Light theme not yet implemented.** Color tokens assume dark. The wordmark/mark exploration cards include light treatments, but the UI kit does not. Flagged in `a11y.md`.
- **No marketing surfaces designed.** The brand has no website or landing page in the source; this system covers the in‑product UI plus an internal‑deck template only. Marketing surfaces can be derived from these foundations on request.
