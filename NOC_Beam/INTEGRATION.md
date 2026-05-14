# NOC_Beam Design System — local working copy + integration plan

## What this folder is

The full v2 design system from Claude Design, extracted to
`/home/user/Eyebeam/NOC_Beam/` so we can work against it locally without
re-fetching the zip. The originals stay untouched here; engineering ports
into `python-app/src/noc_beam/ui/resources/` happen elsewhere.

```
NOC_Beam/
├── README.md            v2 spec overview
├── a11y.md              accessibility commitment (WCAG 2.2 AA)
├── motion.md            motion spec (80/160/240ms, one curve, four categories)
├── colors_and_type.css  tokens (color, type, spacing, radii, motion)
├── assets/              wordmark + mark canonical SVGs
│   └── explorations/    A/B/C wordmark + 1/2/3 mark alternatives
├── fonts/               webfont notes
├── preview/             token cards for the design-system tab
│   ├── component-states.html
│   ├── high-contrast.html
│   ├── logo-{wordmark,mark}-exploration.html
│   ├── logo-size-test.html
│   └── motion.html
├── slides/              internal-deck template
└── ui_kits/noc_beam/    11 high-fidelity HTML surfaces
    ├── index.html               main shell + Calls
    ├── accounts.html            ← new destination
    ├── history.html             ← new destination
    ├── contacts.html            ← new destination
    ├── voicemail.html           ← new destination
    ├── conference.html          ← new destination
    ├── incoming.html            in-app focus + toast + PiP
    ├── trace.html               trace as destination
    ├── account-dialog.html      modal with OPTIONS probe
    ├── settings.html            shell
    ├── settings-codecs.html     codec list
    ├── settings-network.html    network/NAT
    └── styles.css               shared component styles
```

## Brutal-honesty review vs the v1 brief

**What v2 nailed (most of the asks):**

| Brief item | v2 status |
|---|---|
| Left icon rail + content + right drawer | ✓ implemented exactly |
| Right-side in-call controls panel | ✓ live trace lives in the drawer |
| Trace view as a destination | ✓ separate `trace.html` + drawer surfacing |
| Accounts as own destination | ✓ `accounts.html` |
| History with proper IA | ✓ `history.html` (cols + filters + redial) |
| Settings sub-sections | ✓ split into Audio/Codecs/Network/Advanced |
| Account dialog grouping | ✓ tabbed + OPTIONS probe panel |
| Three incoming-call surfaces | ✓ focus / toast / PiP |
| Multi-call screen | ✓ `index.html` has idle/active/multi states |
| Real wordmark + mark exploration | ✓ 3+3 options, 16/24/32px size test |
| Motion spec | ✓ `motion.md` — 80/160/240ms, one curve, reduced-motion |
| Accessibility commitment | ✓ `a11y.md` — WCAG 2.2 AA, kbd map, screen-reader rules |
| High-contrast mode | ✓ both `forced-colors: active` and explicit `.hc` class |
| Drop the "Place call from" combo | ✓ replaced by title-bar active-account chip + ⌘K |
| Drop letter sub-labels from dialpad | partial — they appear in `index.html` but smaller and less prominent |
| Real .props with sizes/states for every interactive thing | partial — `component-states.html` covers most |

**What v2 missed or got wrong:**

1. **Contacts, Voicemail, Conference surfaces.** I flagged these in the
   v1 review as consumer-softphone drift; v2 kept them as first-class
   destinations. For a NOC tool these are out of scope — drop the rail
   icons and don't build them.
2. **Light theme still open.** Documented as TODO; not blocking but
   should land before claiming "modern dark theme" is solved.
3. **No mockup of the call-quality / MOS surface.** The drawer surfaces
   the trace but not the live MOS bar / RTCP-XR stats that the engine
   already emits (`sip/quality.py`).
4. **No mockup of the SIP trace export / persistent-log surface.** The
   trace destination should expose the rotating log file and a
   "Copy as ticket attachment" affordance from `a11y.md`. The HTML kit
   shows neither.
5. **The OPTIONS probe panel** in the account dialog is below the fold
   per Claude Design's own caveat. Acceptable for a screenshot,
   non-negotiable in code — the diagnostic panel must always be visible
   when the form is active.
6. **No mockup of the Headset HID badge** referenced in `a11y.md` /
   shortcuts. Engineering already detects headsets (`audio/headset.py`);
   needs a status-bar / title-bar slot.
7. **No NOC-tool primitives we discussed**: ICE/STUN diagnostics panel,
   TLS cert inspector, REGISTER timing graph, codec negotiation matrix,
   scriptable/headless mode docs. v2 still framed as "modern softphone."

## NOC-tool focus filter

The user's concern is that the product drifts toward Eyebeam-replacement
instead of staying a NOC testing tool. Apply this filter to v2:

**Keep (NOC-essential):**
- Icon rail + content + drawer composition
- Title bar with active-account chip + ⌘K dial bar
- Trace as both destination and drawer
- Accounts, History, Settings as destinations
- Incoming-call focus surface (toast/PiP optional)
- Account dialog with OPTIONS probe
- The whole tokens + motion + a11y foundation

**Defer or kill (consumer-softphone drift):**
- Contacts destination — kill for now. Add later only if NOC ops actually
  need a shared phonebook.
- Voicemail destination — kill. NOC tool doesn't transcribe voicemail.
- Conference destination — defer. Multi-call already lives in Calls;
  conference is a Phase 4 concern at earliest.
- Floating PiP — defer. The in-app focus surface + Windows toast cover
  the same need at lower cost.

**Add (missing NOC primitives):**
- A "Diagnostics" rail destination grouping: OPTIONS-probe results,
  ICE/STUN candidates, TLS cert chain, REGISTER timing graph, RTCP-XR
  voice metrics. These are first-class NOC tool features that v2 doesn't
  model.
- A "Headset" badge in the title bar showing connected HID model + state.

## Integration plan (ranked by leverage)

### Phase A — port the tokens (~30 min, no risk)

The token set is mostly already in `python-app/src/noc_beam/ui/resources/`.
Reconcile against v2:

1. `tokens.css` ← copy v2's `colors_and_type.css` verbatim (motion +
   high-contrast blocks are new).
2. `dark.qss` ← extend with motion tokens documented inline (Qt has no
   CSS variables; bake values directly), and verify the `.hc` overrides
   could be applied via a sibling `dark-hc.qss` later.
3. `style.md` ← cross-reference the new v2 fields (rail dimensions, drawer
   width, title-bar height).

### Phase B — pick wordmark + mark (~10 min, blocks brand surfaces)

Look at `preview/logo-{wordmark,mark}-exploration.html` and
`preview/logo-size-test.html`. Three of each on offer. Pick winners; copy
chosen SVG into `python-app/src/noc_beam/ui/resources/`. Generate an
`.ico` (multi-size 16/24/32/48/64/128/256) for the Windows tray.

### Phase C — restructure MainWindow (~half day to a day)

The big one. v2's icon rail + content + drawer replaces v1's `QSplitter`
+ tab-based right pane. Concrete moves in `python-app/src/noc_beam/ui/`:

1. **New `title_bar.py`** — wordmark + active-account chip + ⌘K dial bar
   + window controls. Custom-painted frameless if the design demands it,
   otherwise standard chrome with the bar embedded inside `QMainWindow`.
2. **New `rail.py`** — vertical 64px `QFrame` with 5 destinations + a
   registration-status pill at the foot. Each destination is a
   `QToolButton` with icon over label, `checkable=True`, exclusive group.
3. **`main_window.py`** restructured to use `QStackedWidget` for the
   content area, driven by the rail's `currentChanged`. Existing widgets
   (`CallWidget`, `HistoryView`, `TraceView`, `AccountList`-becomes-an-
   AccountsView, `SettingsDialog`-becomes-SettingsView) get re-parented
   into the stack.
4. **New `trace_drawer.py`** — 360px wide right-side `QFrame` that slides
   in/out via `QPropertyAnimation` (`QPropertyAnimation` on
   `maximumWidth`, 240ms ease-out). Hosts the existing `TraceView` minus
   its toolbar (which moves to the trace *destination*).
5. **Delete** the bottom `QStatusBar`. State moves into the rail's status
   pill + per-view inline state (e.g. registration counts in the Accounts
   view header).
6. **Skip** the rail destinations for Contacts, Voicemail, Conference.
   Drop those rail buttons and don't build the views.

### Phase D — port motion (~half day)

Animations spec'd in `motion.md`. Three primitives to wire in PySide6:

1. **Hover/focus/press transitions** — implement via QSS `:hover` /
   `:focus` background swaps; the 80ms duration is mostly cosmetic and Qt
   doesn't animate QSS properties anyway, so this is a no-op in practice
   except for any QPropertyAnimation we explicitly drive.
2. **Drawer slide** — `QPropertyAnimation(drawer, b"maximumWidth")` from
   `0 → 360px`, 240ms, custom easing curve matching
   `cubic-bezier(0.2, 0, 0, 1)`. Qt has `QEasingCurve` presets but the
   exact bezier needs a custom curve.
3. **Status dot pulse** (`● LIVE`) — `QPropertyAnimation(opacity_effect)`
   loop, 1400ms, ease-in-out. Gated on `prefers-reduced-motion` (Qt has
   no direct equivalent; we can poll `QStyleHints.colorScheme()` or
   expose a settings toggle).

The incoming-call ring is a special case — used only on the incoming
modal, drawn via a custom `QWidget.paintEvent` with a `QTimer` driving
the expansion/opacity.

### Phase E — add a Diagnostics destination (~1–2 days, NOC focus)

The v2 design didn't model this; we add it. New view in the rail with:
- OPTIONS probe panel (already prototyped in the account dialog)
- ICE/STUN candidate table (per active account)
- TLS cert chain viewer (when transport=tls)
- REGISTER timing graph (RTT per attempt, rolling 30 days)
- RTCP-XR voice metrics per active call

This pulls data we already collect (`sip/quality.py`) plus a few new
pjsua2 calls (`call.getInfo()`, account transport info). Visual treatment
follows the same v2 patterns: code-key + label + value rows.

### Phase F — high-contrast mode (~half day)

Port the `html.hc { ... }` block from `colors_and_type.css` into a
`dark-hc.qss`. Settings toggle wires `QApplication.instance().setStyleSheet()`
between `dark.qss` and `dark-hc.qss`. Honour `forced-colors` only if we
detect Windows High Contrast (no clean Qt API; can poll
`QGuiApplication.styleHints()`).

## Wordmark / mark — pick winners

Open these three files in a browser and look at all sizes:
- `preview/logo-wordmark-exploration.html` (A / B / C)
- `preview/logo-mark-exploration.html` (1 / 2 / 3)
- `preview/logo-size-test.html` (everything at 16/24/32 px tray scale)

Decision criteria:
- **Mark must read at 16×16 mono.** This is the Windows tray constraint.
  If it blurs into a smudge or another app's logo, kill it.
- **Wordmark must read at title-bar height (~20 px).** v2 puts it in the
  44 px title bar at 18 px tall; if the underscore disappears at that
  size, the brand promise breaks.
- **Both must work in mono** for forced-colors and high-contrast.

I'll mark a recommendation in a follow-up after looking at the actual
renderings.

## What I'm explicitly NOT doing

- No "let's discuss" calls for design v3 features. v2 is enough material
  for 1–2 weeks of focused engineering. Anything new can wait.
- No code edits in this folder. This is the design canon; engineering
  changes happen under `python-app/`.
- No Contacts / Voicemail / Conference engineering. Aborting these now
  saves time and re-aligns the product with NOC-tool positioning.

## Verification

After each Phase lands, the smoke test is the same: build (locally via
`python-app/build/build_windows.ps1` or CI), run on a Windows machine,
verify the surface matches its `ui_kits/noc_beam/*.html` counterpart
side-by-side. Pixel-perfect isn't the bar — "behaviorally identical and
visually within tolerance" is.
