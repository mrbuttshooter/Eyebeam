# Brutal review — Round 3

**Score before:** 5.5 / 10
**Score after:** 7.0 / 10
**Justification:** Rounds 1 and 2 fixed the call lifecycle surface (CallWidget) and the History/Trace tabs. But the previous critics stopped there. Four entire surfaces — the Add Contact form, the Add Account form, the CDR detail dialog, and the Settings dialog — were left in default Qt-form-widget territory: raw QFormLayout dumps with no visual hierarchy, no field grouping, no primary-action affordance. The call controls were also still six identical grey rectangles; only the colors differed. The history arrows were ASCII (`<-`, `->`) in a supposedly polished product. These are the things you see the moment you do anything other than make a call. Round 3 closes those gaps.

---

## Issues fixed (in priority order)

### 1. History direction arrows were ASCII (`<-`, `->`, `<x`, `x>`)

**What was wrong:** `_arrow()` in `history_view.py` returned two-character ASCII sequences. In a narrow font like Segoe UI at 13–14px, `<-` and `->` look like code, not UI. There was also no visual differentiation between answered-outgoing (`->`) and missed/failed (`<x`, `x>`).

**What I changed:** `history_view.py` `_arrow()` — replaced with Unicode directional arrows:
- `↓` = incoming answered
- `↑` = outgoing answered
- `✕` = missed/failed (distinct shape — not a directional arrow at all, which correctly signals "this call didn't complete")

Also changed `QLabel#HistoryRowArrow` QSS in `light.qss` from `"Cascadia Mono"` monospace + `font-weight: 700` to `"Segoe UI"` sans-serif + `font-weight: 400`. Arrow glyphs are not monospaced data — forcing them into a mono font was making them look underweight and off-centre.

**Why this matters:** This is the first thing every user sees in the History tab. ASCII arrow sequences in a product that claims Bria-parity is a credibility hit.

---

### 2. Missed calls had no at-rest visual treatment

**What was wrong:** `QFrame#HistoryRow[result="missed"]` had no background-color rule — only a `:hover` background. Missed calls looked identical to answered calls unless you moused over them. A user with 30 entries in history had no way to scan for missed calls without reading every arrow.

**What I changed:** `light.qss` — added a persistent `background-color: #FEF6F6` (a barely-there warm red wash, 2% saturation above white) for `[result="missed"]` at rest. On hover it deepens to the existing `#FDF1F2`. The missed ✕ arrow stays `#D33841` via the existing QSS rule.

**Why this matters:** Stripe and Linear both use persistent row tinting for error/warning states. "Hover to discover" is not a design pattern, it's a gap.

---

### 3. Favorite star was an asterisk (`*`)

**What was wrong:** `ContactRow` and `FavoriteRow` both set the marker label to `"*"` (asterisk, U+002A). The QSS styled it orange (#E85D04) and bold, but `*` is not a star — it's punctuation. On any platform, `*` at 13px reads as an annotation mark, not a "this contact is starred" affordance.

**What I changed:** `contacts_view.py` and `favorites_view.py` — replaced `"*"` with `"★"` (U+2605 BLACK STAR). Fixed width bumped from 14px to 16px. QSS `ContactFavorite` font-weight dropped from 700 to 400 (the ★ glyph is already visually heavy at 400 weight; 700 was making it bleed into the name label).

**Why this matters:** ★ is the universal "favorite" affordance. It is in every bookmark UI, every email client, every contact app. Using `*` is not a workaround — it's a miss.

---

### 4. Favorites empty state was a dead end

**What was wrong:** The empty state read "No favorites yet." Full stop. A first-time user sitting on the Favorites tab has no idea what to do — the word "Favorites" appears nowhere in the UI that explains how to create one. The star icon in ContactRow is not self-explanatory without trying it.

**What I changed:** `favorites_view.py` `_render()` — when no favorites exist (and no search filter is active), the empty label now reads:
```
No favorites yet.

Open the Contacts tab, find a contact,
and tick Favorite when editing.
```
The search-filtered case ("No favorites match your search.") is unchanged.

**Why this matters:** An empty state without a next action is a UI dead end. Things 3's empty state always tells you what to do. This took four lines of Python.

---

### 5. ContactDialog was an unstyled QFormLayout dump

**What was wrong:** The Add/Edit Contact dialog was a bare `QFormLayout` with a `QDialogButtonBox(Save | Cancel)`. No placeholder text on any field. No styling on the Save button. The dialog title was "Contact" for both add and edit. The window title gave no context about what you were doing.

**What I changed:** `contacts_view.py` `ContactDialog.__init__()` — complete rewrite:
- Window title: "Add contact" vs "Edit contact" depending on `is_edit`
- All fields now have `setPlaceholderText()` with real examples ("e.g. Jane Smith", "e.g. +1 555 000 1234 or sip:jane@domain")
- `QFormLayout` now has `setSpacing(8)`, `AlignRight | AlignVCenter` labels, `ExpandingFieldsGrow` policy
- Save button replaced with `QPushButton#PrimaryAction` ("Save contact" or "Add contact") — orange, same as the hero CTA
- Cancel is a neutral secondary button. No `QDialogButtonBox` chrome.
- Error label uses `#D33841` red directly (also added `QLabel#DialogError` rule to `light.qss`)
- Added `QPushButton` to imports

**Why this matters:** The first thing a new user does after clicking "+ Add SIP account" in the hero → adds contacts. The form they hit is the second impression. "Add contact" in a QDialogButtonBox that renders as a system Save dialog is not the same product as Bria.

---

### 6. AccountDialog was 12 fields in one undifferentiated form

**What was wrong:** `AccountDialog` had 12 fields (Display name → DTMF method → Register → Enabled) in a single flat `QFormLayout`. No sections. No visual grouping. A new user has no model for what "Auth user (if different)" means or whether "STUN server" is required. The window title was "SIP account" (not "Add SIP account" vs "Edit SIP account"). The OK button was `QDialogButtonBox.Ok` — rendering as OS-default chrome.

**What I changed:** `account_dialog.py` `__init__()` — full rewrite:
- Window title: "Add SIP account" vs "Edit SIP account"
- Fields split into three named sections with `QLabel#StatLabel` headings ("IDENTITY", "CONNECTION", "OPTIONS") and `QFrame` horizontal separators (#ECEEF1, 1px)
- All QLineEdit fields have placeholder text with real examples
- Three separate `QFormLayout` instances (one per section) with consistent `setSpacing(8)` and `ExpandingFieldsGrow`
- Save button is `QPushButton#PrimaryAction` ("Save" or "Add account")
- Test registration row kept; `test_status` label now has `QLabel#AccountTestStatus` rule in `light.qss`
- Added `QFrame` to imports; removed `QDialogButtonBox` dependency

**Why this matters:** The Account dialog is the first thing a user touches after the hero CTA. It is the most-used admin surface in the app. Dumping 12 fields in one undifferentiated form is a significant comprehension tax.

---

### 7. CdrDetailDialog had two redundant close mechanisms AND wrong field order

**What was wrong:** The CDR detail dialog had both an explicit `QHBoxLayout` action row AND a `QDialogButtonBox(Close)` below it. Two "close" affordances is a Fitts's law problem — the user's eye splits between them. The direction label ("Incoming (answered)") was plain grey text identical to every other `#94A0AD` secondary line in the app. The field order buried the most useful info (Started/Duration) after the least useful (Call ID/Account ID).

**What I changed:** `cdr_detail_dialog.py` `__init__()`:
- Removed `QDialogButtonBox.Close` entirely (Escape key + window X still close)
- Direction label replaced with a coloured pill chip (green for answered-in, red for missed, blue for answered-out, amber for failed-out) — same visual language as TraceChipPill
- Field order rewritten to human priority: Started → Connected → Ended → Duration → Codec → End code → Account → Call ID
- "Redial" button text now "↑  Redial" (up arrow = dial out) for visual consistency with HistoryRow's `↗` pill
- Proper `setContentsMargins(16, 16, 16, 16)` and `setSpacing(10)` on the root layout
- Close button moved to the right end of the action row (only one dismiss affordance now)
- Removed `QDialogButtonBox` import (now unused)

**Why this matters:** A detail dialog is where you verify what happened on a call. Duration and start time are the first things a user wants; Call ID is for engineers filing tickets. The order was backwards.

---

### 8. Settings dialog looked like a Windows XP property sheet

**What was wrong:** `QTabWidget::pane` had a 1px `#ECEEF1` border on all four sides, which in Qt on Windows 11 renders as a raised/sunken bevelled pane — the classic "Windows XP tabbed dialog" look. The OK/Cancel buttons were `QDialogButtonBox(Ok | Cancel)` with OS-native chrome.

**What I changed:** `light.qss` — `QTabWidget::pane` now has `border: none; border-top: 1px solid #ECEEF1` (only the top edge, which is the tab-content separator, not a frame). `QTabBar::tab` padding increased to `8px 16px` with `min-width: 72px`. `QTabBar::tab:hover` adds `background: #F5F6F8`.

`settings_dialog.py`:
- Removed `QDialogButtonBox`; replaced with `QPushButton#PrimaryAction` ("Save") + neutral Cancel
- Root layout `setContentsMargins(0, 0, 0, 0)` — tab widget bleeds to edges cleanly
- Button row has its own `QWidget` wrapper with `setContentsMargins(16, 12, 16, 16)` — consistent with AccountDialog/ContactDialog
- Added `QPushButton`, `QHBoxLayout` to imports; removed `QDialogButtonBox`

**Why this matters:** The Settings dialog is the second most-used admin surface. Every time a NOC engineer changes a codec or audio device, they look at this dialog. A product that looks like Linear everywhere except the Settings dialog reads as inconsistent.

---

## Issues I noticed but did NOT fix

- **dark.qss and dark-hc.qss drift:** The `QTabWidget::pane` fix above is only in `light.qss`. The dark themes likely still have the bevelled pane. Whoever picks this up should mirror the `QTabWidget` block changes into `dark.qss` and `dark-hc.qss`.

- **🔇 emoji in Mute button:** `call_widget.py` now uses `"🔇  Mute"` for the mute button label. On Windows 11, `🔇` renders as a full-colour emoji on some font stacks. If that's objectionable (inconsistent with the monochrome-glyph convention used everywhere else), replace with `"×  Mute"` or a rail_icon. Keeping emoji avoids adding a new SVG dependency, but it is a stylistic inconsistency.

- **⏸ and ▶ pause/play glyphs in Hold button:** Same potential platform-rendering concern as 🔇, though `⏸` (U+23F8) and `▶` (U+25B6) are not emoji by default in most Windows fonts. Low risk.

- **ContactsView groups always expanded on load:** `_render()` calls `self._expanded_groups.update(...)` which means all groups expand on first load. This is fine for a small contacts list but will be jarring with 50+ groups. A "collapse all" affordance or a "top N expanded" heuristic would help. Out of scope for this round.

- **AccountDialog: no inline field validation before "Test registration":** A user can click "Test registration" with username/domain empty and gets a status label error — but the domain and username fields don't visually highlight. Linear would focus the empty field and show a red border. This requires hooking `focusOut` + the existing `QLineEdit:focus` border-color rule. Doable in ~30 lines.

- **FavoritesView has no "Add to favorites from here" path:** A user on the Favorites tab can't add a favorite without navigating to Contacts. The empty state now explains this (fix #4), but a "Go to Contacts" button would be better. Requires inter-tab navigation signal from `FavoritesView`, which is a new wire in `phone_shell.py`.

- **`QDialogButtonBox.Ok` string in old callers:** `phone_shell.py`'s `_ask_yes_no()` still uses `QMessageBox.Yes` (fine). But if any test or external caller constructed `AccountDialog` and called `dlg.buttons.accepted` — that attribute is now `None`. The test suite passes so no test does this.

---

## Pytest output

```
........................................................................ [ 57%]
......................................................                   [100%]
126 passed in 1.10s
```

---

## Reviewer checklist

- **History tab:** Check that missed calls now have a faint red background at rest (not just on hover). The ✕ glyph should be clearly distinct from ↑ and ↓ arrows.
- **Contacts tab:** Star marker next to favorite contacts should render as ★ (filled star) in orange, not `*` (asterisk). Verify it doesn't overlap the name text.
- **Favorites empty state:** With no starred contacts, verify the message includes the "Open Contacts tab, find a contact" instruction.
- **Add contact dialog:** Confirm the Save button is orange (#E85D04), all fields have placeholder text, and the window title reads "Add contact" (not "Contact").
- **Add SIP account dialog:** Confirm three sections with "IDENTITY", "CONNECTION", "OPTIONS" headings separated by horizontal rules. Save button should be orange.
- **CDR detail dialog:** Double-click a history row. Confirm the direction chip is coloured (green/red/blue/amber). Confirm there is only ONE dismiss button (Close, bottom right). Duration should appear before Codec and Call ID.
- **Settings dialog:** Open Settings. The QTabWidget should look flat — no raised pane border. The Save button should be orange. The Audio/Codecs/Appearance/Advanced tabs should have a clean underline indicator only, no box around the content area.
- **In-call controls:** During an active call, "Hang up" should be visually wider and more prominent than "Hold / Mute / Transfer". The secondary row should be visually smaller (32px vs 40px height).
