"""Stylesheet swap helper.

light.qss is the single source of truth for the entire app's design
language. Dark mode is derived programmatically by substituting a
fixed color map (LIGHT_TO_DARK below). Keeps the two themes from
drifting visually -- changing a colour in light.qss automatically
flows to dark via the map.

dark-hc.qss is still a hand-written high-contrast override (yellow
focus, pure black, full white text). Loaded as-is when the
high_contrast toggle is on.
"""
from __future__ import annotations

import logging
import re
from importlib import resources

from PySide6.QtWidgets import QApplication

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Light -> Dark colour map. Keys are exact hex strings as they appear in
# light.qss (case-sensitive uppercase). Add new entries as new colours
# enter light.qss; missing keys stay as-is (visible by eyeballing the
# resulting dark output).
#
# Buckets:
#   surfaces  - whites/very-light greys become deep darks
#   borders   - light greys become mid darks
#   text      - dark greys become near-whites
#   accents   - brand colours either kept or slightly shifted for dark bg
# ---------------------------------------------------------------------------
LIGHT_TO_DARK: dict[str, str] = {
    # ===== Surface hierarchy =====
    # CORE RULE: keep all idle surfaces at the SAME base color (#1B2129).
    # Light mode uses subtle gradients between #FFFFFF, #F6F7F9, #FAFBFC
    # etc. but in dark mode those gradients look like recessed/pressed
    # states. Unify them; only hover/selected gets a distinct (lighter)
    # color so interactivity stays visible.
    #
    # Light bg variants    ->  Dark unified base    Role
    # #FFFFFF, #F6F7F9...  ->  #1B2129              all idle surfaces
    # #F5F6F8 (hover)      ->  #262E3A              hover/pressed (lighter)
    "#FFFFFF": "#1B2129",
    "#FAFBFC": "#1B2129",
    "#FAFAFA": "#1B2129",
    "#F9FAFB": "#1B2129",
    "#F7F8FA": "#1B2129",
    "#F6F8FA": "#1B2129",
    "#F6F7F9": "#1B2129",  # unified — same as cards (no recessed look)
    # Hover / pressed / selected -- LIGHTER than the base, but only by
    # a few RGB points so the edge of the hovered region doesn't form
    # a hard visible line against the panel. The orange-tinted accent
    # highlights (#FFF5ED -> #2C2B22, see below) carry the "this row
    # is selected" signal with more chroma.
    "#F5F6F8": "#1F252E",
    "#F4F6F9": "#1F252E",
    "#F1F3F5": "#1F252E",
    "#EEF0F2": "#1F252E",
    "#EDEFF2": "#1F252E",
    "#ECEFF2": "#1F252E",
    # Row-hover (the gray operator picked for light mode after the
    # "still white" feedback). In dark mode it needs to map to a
    # clearly-visible cyan-tinted shade -- without an entry here the
    # programmatic-substitution leaves it as #E8ECF1, which paints
    # near-white in dark mode and reads as a glitch on hover.
    "#E8ECF1": "#253A5B",

    # ===== Status-tinted row backgrounds =====
    # Map to the SAME base as primary surface. In light mode missed/failed
    # rows get a soft pink/orange tint that pops them out of the list. In
    # dark mode that same tint reads as garish red bars -- the row text
    # and the SIP-code badge already carry the colour signal, the row bg
    # doesn't need to. Just blend with the base.
    "#FDF6F6": "#1B2129",
    "#FDEDED": "#1B2129",
    "#FDF1F2": "#1B2129",
    "#FCE7E9": "#1B2129",
    "#FDECEE": "#1B2129",
    "#FFEBEC": "#1B2129",
    "#FEF6F6": "#1B2129",
    "#FFFBF5": "#1B2129",
    "#FFF3E1": "#1B2129",
    "#FFF7E6": "#1B2129",
    "#FFF7F0": "#1B2129",
    "#FFF4EB": "#1B2129",
    "#FFF3CD": "#1B2129",
    "#FFF4DB": "#1B2129",
    "#FEEEE3": "#1B2129",
    # Accent (orange) soft -- used for selection highlights
    "#FFE0CC": "#3A2410",
    "#FFD7BD": "#3A2410",
    "#FFE2C9": "#3A2410",
    "#FFF5ED": "#2C2B22",
    # Green soft
    "#E8F7EE": "#1A2E22",
    "#DFF7E8": "#1A2E22",
    "#A9E7BC": "#2A5238",
    # Blue / info soft
    "#E8F2FA": "#1F2C38",
    "#EAF0F6": "#1F2C38",
    "#E5F2FA": "#1F2C38",
    "#DCEEFC": "#22344A",

    # ===== Borders -- very subtle on dark =====
    # On dark backgrounds even a faint border becomes a hard "line"
    # because the contrast ratio against #1B2129 spikes fast.
    # Keep the LIST dividers nearly invisible (#222831), promote only
    # to a clear border when the element really needs one (inputs).
    "#ECEEF1": "#222831",  # list dividers, soft separators -- nearly invisible
    "#E0E3E7": "#222831",
    "#E1E4E8": "#222831",
    "#DDE3E8": "#222831",
    "#D8DEE4": "#252B36",
    "#D1D5DB": "#2B323D",  # input borders, slightly more visible
    "#D0D7DE": "#2B323D",
    "#C9CDD3": "#2B323D",
    "#C2C9D2": "#2B323D",
    "#B7C0CB": "#3B4654",
    "#D2A8AB": "#3B2A2D",  # danger row border (also subtle)
    "#94A0AD": "#3B4654",  # hover border
    "#B8DDF2": "#1A4F73",  # info border light
    "#6FB8E8": "#2A8DC4",  # info border

    # ===== Text (dark -> light) =====
    "#1F2328": "#E5E9F0",
    "#1F2933": "#E5E9F0",
    "#0F172A": "#E5E9F0",
    "#4B5563": "#9DA5B0",
    "#57606A": "#9DA5B0",
    "#6B7280": "#7C8696",
    "#8C959F": "#6B7280",

    # ===== Brand accents (orange) — push brighter on dark bg =====
    "#E85D04": "#FF8A2A",
    "#FF7A1A": "#FF8A2A",
    "#FF7314": "#FF8A2A",
    "#E25A0E": "#FF7A1A",
    "#C24B00": "#E85D04",
    "#C84E0A": "#E85D04",
    "#C97C0E": "#E0931F",
    "#E08A1A": "#E0931F",
    "#6B4A0A": "#F2D27A",
    "#8A5A00": "#F2D27A",
    "#E0B872": "#F2D27A",
    "#F2D27A": "#F2D27A",  # keep

    # ===== Semantic green (success / answered) =====
    "#116329": "#46CF74",
    "#1A7F37": "#46CF74",
    "#1FA64C": "#46CF74",
    "#2DA44E": "#46CF74",
    "#2EBD5C": "#46CF74",
    "#46CF74": "#46CF74",  # keep

    # ===== Semantic red (danger / missed) =====
    "#9F1D28": "#FF8DA0",
    "#A02129": "#FF8DA0",
    "#B22D35": "#FF8DA0",
    "#B32D2E": "#FF8DA0",
    "#D33841": "#FF5C7A",
    "#E55260": "#FF5C7A",
    "#E5A4A8": "#FF8DA0",
    "#F2B8BE": "#FF8DA0",
    "#F2C0C4": "#FF8DA0",
    "#E0BFC2": "#FF8DA0",

    # ===== Semantic blue (info / link) =====
    "#0969DA": "#7FD3FF",
    "#145C8A": "#7FD3FF",
    "#1A6FA0": "#7FD3FF",
    "#2A8DC4": "#7FD3FF",
}


def _to_dark(qss: str) -> str:
    """Convert a light QSS to its dark variant via the colour map.

    Uses a single pass with a regex so each hex literal is touched at
    most once -- naive sequential replace() would re-substitute the
    output of an earlier swap.
    """
    if not qss:
        return qss
    pat = re.compile(r"#[0-9A-Fa-f]{6}\b")

    def _repl(m: re.Match) -> str:
        hex_val = m.group(0).upper()
        return LIGHT_TO_DARK.get(hex_val, m.group(0))

    return pat.sub(_repl, qss)

REQUIRED_THEME_SELECTORS = (
    "QLabel#StatusPill",
    "QLabel#SipCodeBadge",
    "QLabel#MetricChip",
    "QToolButton#IconActionButton",
    "QFrame#FormSection",
    "QLabel#SectionHeader",
    "QFrame#FooterActionBar",
    "QPushButton#PrimaryAction",
    "QPushButton#SecondaryAction",
    "QWidget:focus",
)


def _load(name: str) -> str:
    try:
        return resources.files("noc_beam.ui.resources").joinpath(name).read_text(
            encoding="utf-8"
        )
    except Exception:
        log.warning("Could not load stylesheet %s", name, exc_info=True)
        return ""


def _substitute_assets(qss: str) -> str:
    """Replace __ASSET__ placeholders in QSS with absolute file paths
    to the bundled SVGs. Qt's QSS only accepts file URLs / paths in
    image: url(...); referencing them by name from importlib.resources
    doesn't work at runtime."""
    if not qss:
        return qss
    try:
        res_root = resources.files("noc_beam.ui.resources")
        for placeholder, asset in (
            ("__ARROW_DOWN__", "arrow-down.svg"),
            ("__ARROW_UP__", "arrow-up.svg"),
            ("__ARROW_DOWN_LIGHT__", "arrow-down-light.svg"),
            ("__ARROW_UP_LIGHT__", "arrow-up-light.svg"),
        ):
            try:
                p = str(res_root.joinpath(asset)).replace("\\", "/")
                qss = qss.replace(placeholder, p)
            except Exception:
                continue
    except Exception:
        log.warning("Asset path substitution failed", exc_info=True)
    return qss


_DARK_OVERRIDES = """
/* ===== Dark-mode-only overrides (appended after color substitution) =====
   Things that can't be expressed as a simple light->dark colour swap.
   Currently empty -- the earlier "kill all row hovers in dark mode"
   override was removed once the operator explicitly asked for the
   gray (light) / cyan-tinted-dark (dark) hover treatment everywhere.
   The light->dark color substitution (LIGHT_TO_DARK with the new
   #E8ECF1 -> #253A5B entry) now handles row hover consistently.
*/
"""


def load_theme_qss(*, theme: str = "light", high_contrast: bool = False) -> str:
    """Returns the QSS text for the chosen theme, or '' on failure.

    Architecture: light.qss is the single source of truth. Dark mode
    is derived programmatically via LIGHT_TO_DARK colour map -- so
    changing a colour in light.qss automatically flows to dark, and
    we can never have the two designs drift apart again.
    """
    if high_contrast:
        qss = _load("dark-hc.qss")
        return _substitute_assets(qss)

    qss = _load("light.qss")
    # Use a light-mode arrow on dark backgrounds so the chevrons stay
    # visible. Done BEFORE color substitution so the placeholder
    # token (not a hex) gets replaced.
    if theme == "dark":
        qss = qss.replace("__ARROW_DOWN__", "__ARROW_DOWN_LIGHT__")
        qss = qss.replace("__ARROW_UP__", "__ARROW_UP_LIGHT__")
        qss = _to_dark(qss)
        qss = qss + _DARK_OVERRIDES
    return _substitute_assets(qss)


def apply_theme(app: QApplication, high_contrast: bool = False, *, theme: str = "light") -> None:
    qss = load_theme_qss(theme=theme, high_contrast=high_contrast)
    log.info("apply_theme: theme=%s hc=%s qss_len=%d head=%s",
             theme, high_contrast, len(qss or ""),
             (qss or "")[:120].replace("\n", "\\n"))
    if qss:
        app.setStyleSheet(qss)
        log.info("apply_theme: QApplication.setStyleSheet applied (%d chars)", len(qss))
