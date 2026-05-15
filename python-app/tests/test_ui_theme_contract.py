from noc_beam.ui.theme import REQUIRED_THEME_SELECTORS, load_theme_qss


def test_all_themes_define_required_redesign_selectors():
    themes = [
        ("light", False),
        ("dark", False),
        ("light", True),
    ]

    for theme, high_contrast in themes:
        qss = load_theme_qss(theme=theme, high_contrast=high_contrast)
        assert qss
        for selector in REQUIRED_THEME_SELECTORS:
            assert selector in qss, f"{selector} missing from {theme} hc={high_contrast}"


def test_all_themes_include_visible_focus_states():
    for theme, high_contrast in [("light", False), ("dark", False), ("light", True)]:
        qss = load_theme_qss(theme=theme, high_contrast=high_contrast)
        assert ":focus" in qss
        assert "FocusRing" in qss or "focus" in qss.lower()
