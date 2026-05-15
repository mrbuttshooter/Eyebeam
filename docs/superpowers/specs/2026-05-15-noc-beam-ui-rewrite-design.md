# NOC_Beam Full UI Rewrite Design

Date: 2026-05-15

## Goal

Redesign NOC_Beam from a polished prototype into a premium Windows desktop SIP softphone and NOC operator console. The rewrite changes the visual shell and UI widgets across the product while preserving the working SIP, account, storage, history, and test-runner internals.

The target quality bar is a strict 9/10 implementation: consistent, dense, accessible, and credible under a boss demo and under real NOC use.

## Scope

In scope:

- Main shell layout and navigation
- Dial page and active-call state
- Contacts and Favorites pages
- History page
- Trace page
- Settings dialog
- Account dialog
- Test Runner window
- Shared UI components and theme tokens
- Light, dark, and high-contrast themes
- Screenshot and packaged `.exe` smoke verification

Out of scope:

- Rewriting the SIP engine
- Changing account persistence format unless the UI exposes an existing bug
- Replacing the call placement/register logic
- Replacing contacts/history/test-runner data models
- Adding new product modules beyond existing pages and dialogs
- Changing CSV output semantics

## Rewrite Boundary

This is a full visual UI rewrite, not a full product rewrite. Existing backend behavior remains the source of truth. New widgets must call existing services and models rather than duplicating SIP/account/call-state logic.

The rewrite may replace UI classes when that produces cleaner boundaries, but it must not break these flows:

- Add account, save account, restart app, account remains saved
- Test Register shows useful success/failure state
- Place call from Dial
- Redial/callback from History
- Open Contacts and Favorites
- Open Trace and inspect SIP events
- Run Test Runner, cancel a run, export CSV

## Visual System

The app uses one design system across light, dark, and high-contrast themes.

Global rules:

- Slightly wider default shell than today, while remaining compact desktop software
- 4px spacing grid
- 4-6px corner radius
- 1px borders as the main structure
- Minimal shadows, used only for window-level separation or modal elevation
- Segoe UI / Inter-style font stack
- 12-13px body text
- 11px metadata
- 14-15px section headings
- Tabular numerals for phone numbers, SIP codes, ports, times, RTT, durations, and counts

Semantic colors:

- Orange: NOC_Beam brand and active navigation only
- Green: registered, call, pass, `200`
- Amber: ringing, pending, `180`
- Red: fail, missed, error
- Blue: trace direction/info metadata
- Gray: idle, disabled, secondary text, neutral borders

No state may rely on color alone. SIP/result states must include text, code, icon, or shape.

## Shared Components

The rewrite should introduce shared UI patterns before rebuilding individual screens:

- `StatusPill`: registration, account health, pass/fail/running summaries
- `SipCodeBadge`: fixed-width SIP code and reason treatment
- `OperatorToolbar`: compact row for filters, modes, and actions
- `DenseListRow`: aligned row shell for Contacts, Favorites, and History
- `FormSection`: titled form group with fixed label column and flexible control column
- `IconActionButton`: 28px compact icon button with tooltip/focus state
- `MetricChip`: small count/RTT/duration/parallelism chips
- `TraceDirectionTag`: TX/RX direction tag with accessible label
- `FooterActionBar`: consistent Save/Cancel/Reset/Export footer treatment

These can be implemented as Qt helper functions or small widgets depending on existing code boundaries. The important requirement is consistency, not abstraction for its own sake.

## Main Shell

The shell becomes a compact Windows operator panel.

Requirements:

- Header shows NOC_Beam mark, active account selector, registration status, and menu/settings access.
- Account and audio health live in one compact top status strip.
- Bottom navigation remains, but is flatter, denser, and no taller than 48px.
- Active navigation uses restrained orange.
- All other operational states use semantic colors.
- The shell may be slightly wider by default so Trace, History, and Test Runner have readable columns.
- No decorative background imagery, glassmorphism, oversized cards, or mobile-app styling.

## Dial And Active Call

Dial remains the first screen and must feel immediately usable.

Requirements:

- SIP/number input is prominent and supports numbers and SIP URIs.
- Green Call button is strong but not oversized.
- Dialpad stays visible, compact, and secondary.
- Mic, speaker, hold, transfer, and hangup controls use consistent icon button styling.
- Recent calls show 4-6 dense rows with direction, party, SIP/result badge, time, and callback action.
- Active-call state emphasizes remote party, call status, timer, compact controls, and a strong red hangup button.
- The page must avoid giant empty areas and giant mobile-style keypad cells.

## Contacts

Contacts become a dense, aligned operator list.

Requirements:

- Compact search/filter toolbar.
- Grouped list with restrained group headers.
- Initial/avatar marks sized around 28-32px.
- Name, SIP URI/number, favorite state, and call action aligned to a strict grid.
- Add/edit contact dialog uses the same `FormSection` pattern as Settings and Accounts.
- Empty states are quiet and practical, with a next action.

## Favorites

Favorites share the Contacts row system.

Requirements:

- Fixed star column.
- Same row alignment as Contacts.
- Quick-call action aligned to the same right-side action column.
- Empty state is not cute or illustrative. It states that no favorites exist and points the user to Contacts.

## History

History must support fast scanning.

Requirements:

- Compact toolbar for search/filter/date controls.
- Rows grouped by Today, Yesterday, and older dates.
- Consistent direction icons for inbound, outbound, missed, and failed.
- SIP/result badges align in one column.
- Missed/failed rows are visible at rest without being visually loud.
- Callback action is always in the same right-side column.
- Target density is 7-9 visible rows in the default shell.

## Trace

Trace is the credibility page for NOC engineers. It must look and behave like an operational diagnostic tool, not a raw text dump.

Requirements:

- Table-like layout with columns for time, direction, method/status, endpoint, and latency/size when available.
- Events grouped by Call-ID with compact expandable headers.
- Group headers include result/status badge and expand/collapse affordance.
- TX/RX tags use subtle blue/green labels.
- SIP methods and response codes use badges.
- Long SIP URIs and Call-IDs truncate safely, preferably middle-truncated, with tooltip or detail access.
- Monospace is used only for SIP tokens, IPs, ports, and IDs.
- No horizontal clipping in normal use.
- Dense row separators and careful alignment must make incident review possible under pressure.

## Settings Dialog

Settings become a flat desktop configuration surface.

Requirements:

- Split layout with a left section rail.
- Section rail rows are compact and flat, not chunky cards.
- Fixed label column and flexible control column.
- Sections include Audio, Codecs, Appearance, and Advanced.
- Audio meters are thin and not overly bright.
- Footer has consistent Save, Cancel, and Reset behavior where applicable.
- Keyboard focus is visible and ordered logically.

## Account Dialog

Account setup must look like serious desktop admin software.

Requirements:

- Same split/form visual system as Settings.
- Clear groups for Identity, Server, Authentication, and Registration.
- Required fields have inline validation, focus movement, and clear error text.
- Test Register remains visible and understandable.
- Test Register result appears near the registration controls or footer, not as disconnected text.
- Save/Cancel footer is consistent with Settings.
- The dialog must preserve existing account-save behavior.

## Test Runner

The Test Runner must feel like an operations workflow.

Requirements:

- Utility window wider than the softphone shell.
- Callers and Targets paste boxes aligned side by side.
- Mode, Pass, Parallel, Hold, and Timeout controls in a compact toolbar.
- Green Run button includes live call count.
- Results grid uses dense rows and tabular numerals.
- PASS, FAIL, and RUNNING badges are visually strong.
- SIP code, RTT, duration, time, and notes columns are scan-friendly.
- Footer summary counters align left.
- Cancel and Export CSV align right.
- CSV format and backend behavior remain unchanged.

## Themes

Light, dark, and high-contrast themes must be updated together.

Theme requirements:

- All shared components have explicit light, dark, and high-contrast states.
- Focus rings are visible in every theme.
- Disabled controls are readable in every theme.
- High-contrast mode prioritizes clarity over brand polish.
- No page may ship with styling only in `light.qss`.

## Accessibility

Accessibility is part of the definition of done.

Requirements:

- Keyboard navigation across shell, dialogs, tables, and Test Runner.
- Visible focus state for every interactive control.
- Button and tab text cannot clip at normal Windows scaling.
- Meaning is never color-only.
- Tables/lists retain readable contrast in all themes.
- Common dialogs have sensible initial focus.
- Destructive actions are visually distinct and text-labeled.

## Verification

Before the rewrite is considered complete:

- Pytest suite passes.
- Screenshot pass covers Dial, Active Call, Contacts, Favorites, History, Trace, Settings, Account, and Test Runner.
- Screenshot pass is repeated for light, dark, and high-contrast themes.
- Account save/restart smoke test passes in Python source app.
- Test Register path gives useful status in Python source app.
- Test Runner can run in stub mode and export CSV.
- Packaged `.exe` launches.
- Packaged `.exe` can add and persist an account.
- Packaged `.exe` screenshots match the accepted design direction closely enough to avoid theme drift.

## Implementation Strategy

The selected approach is a full UI rewrite with preserved internals.

Recommended implementation order:

1. Define shared theme tokens and reusable component patterns.
2. Rebuild the shell and navigation around the new design system.
3. Rebuild Dial and Active Call because they set the first impression.
4. Rebuild Contacts, Favorites, and History using one shared row system.
5. Rebuild Trace as the primary NOC credibility surface.
6. Rebuild Settings and Account dialogs using shared form sections.
7. Rebuild Test Runner window using the operator table system.
8. Apply and verify light, dark, and high-contrast themes together.
9. Run source-app and packaged `.exe` smoke tests.

Each stage should be verified before moving to the next stage. Avoid large unverified rewrites that make regressions hard to isolate.
