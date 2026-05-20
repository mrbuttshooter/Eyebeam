from __future__ import annotations

from noc_beam.config.store import AccountConfig
from noc_beam.ui.phone_shell import PhoneShell


def test_genband_prefix_uses_dial_prefix_plus_supplier_id() -> None:
    cfg = AccountConfig(
        id="a",
        switch_type="genband",
        dial_prefix="000",
        routing_format="",
    )

    assert PhoneShell._genband_supplier_prefix(cfg, "080") == "000080"


def test_genband_prefix_keeps_legacy_routing_template() -> None:
    cfg = AccountConfig(
        id="a",
        switch_type="genband",
        dial_prefix="",
        routing_format="000{id}",
    )

    assert PhoneShell._genband_supplier_prefix(cfg, "080") == "000080"


def test_genband_prefix_accepts_dial_prefix_template() -> None:
    cfg = AccountConfig(
        id="a",
        switch_type="genband",
        dial_prefix="000{ID}",
        routing_format="",
    )

    assert PhoneShell._genband_supplier_prefix(cfg, "080") == "000080"
