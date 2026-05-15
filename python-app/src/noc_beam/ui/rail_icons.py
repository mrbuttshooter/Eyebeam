"""Inline 24x24 mono SVGs for the icon rail.

Lucide-shaped paths, drawn with `currentColor` so they pick up the
button's text colour at paint time. Kept small + inline so we don't
ship a third-party icon font and don't add a runtime SVG fetch.
"""
from __future__ import annotations

from PySide6.QtCore import QByteArray, QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer


_BASE = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
     stroke="currentColor" stroke-width="1.6"
     stroke-linecap="round" stroke-linejoin="round">{body}</svg>"""

_PATHS = {
    "calls": (
        '<path d="M5 4h3l2 5-2 1.5a12 12 0 0 0 5.5 5.5L15 14l5 2v3a2 2 0 0 1-2 2'
        ' A14 14 0 0 1 3 6 a2 2 0 0 1 2-2z"/>'
    ),
    "trace": (
        '<path d="M4 7h16"/><path d="M4 12h12"/><path d="M4 17h8"/>'
        '<circle cx="20" cy="17" r="1.5" fill="currentColor"/>'
    ),
    "accounts": (
        '<circle cx="12" cy="8" r="4"/>'
        '<path d="M4 21c0-4 4-7 8-7s8 3 8 7"/>'
    ),
    "history": (
        '<circle cx="12" cy="12" r="9"/>'
        '<path d="M12 7v5l3 2"/>'
    ),
    "settings": (
        '<circle cx="12" cy="12" r="3"/>'
        '<path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1'
        'a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1'
        'a1.7 1.7 0 0 0-1.5-1 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8'
        'l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1'
        'a1.7 1.7 0 0 0 1.5-1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8'
        'l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1'
        'a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8'
        'l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4'
        'h-.1a1.7 1.7 0 0 0-1.5 1z"/>'
    ),
    "diagnostics": (
        '<path d="M3 12h4l2-6 4 12 2-6h6"/>'
    ),
    "check": (
        '<path d="M5 12l5 5L20 7"/>'
    ),
    "close": (
        '<path d="M6 6l12 12M18 6L6 18"/>'
    ),
    "phone-down": (
        '<path d="M3 14a18 18 0 0 1 18 0v3a2 2 0 0 1-2 2h-2.5a1 1 0 0 1-1-1.2'
        'l.6-3a1 1 0 0 0-.6-1.1 12 12 0 0 0-7 0 1 1 0 0 0-.6 1.1l.6 3'
        'a1 1 0 0 1-1 1.2H5a2 2 0 0 1-2-2v-3z"/>'
    ),
}


def rail_icon(name: str, color: str = "#B7C0CC", px: int = 22) -> QIcon:
    """Render a named rail icon to a QIcon at `px` size with `color` stroke."""
    body = _PATHS.get(name)
    if body is None:
        return QIcon()
    svg = _BASE.format(body=body).replace("currentColor", color)
    pix = QPixmap(QSize(px, px))
    pix.fill(Qt.GlobalColor.transparent)
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    renderer.render(painter)
    painter.end()
    return QIcon(pix)


def rail_icon_pair(name: str, px: int = 22) -> QIcon:
    """Build a QIcon with both Normal (muted) and Selected (cyan) states."""
    icon = rail_icon(name, color="#B7C0CC", px=px)
    on = rail_icon(name, color="#7FD3FF", px=px).pixmap(px, px)
    icon.addPixmap(on, QIcon.Mode.Selected)
    icon.addPixmap(on, QIcon.Mode.Active)
    return icon
