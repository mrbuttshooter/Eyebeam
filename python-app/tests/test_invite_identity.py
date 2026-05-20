from __future__ import annotations

from noc_beam.config.store import AccountConfig
from noc_beam.sip.endpoint import SipEndpoint


def test_invite_local_uri_carries_display_name_as_from_display() -> None:
    cfg = AccountConfig(
        id="a",
        display_name="96171488860",
        username="U080",
        domain="208.87.170.99",
    )

    assert SipEndpoint._format_invite_local_uri(cfg) == (
        '"96171488860" <sip:U080@208.87.170.99>'
    )


def test_invite_local_uri_omits_when_no_display_name() -> None:
    cfg = AccountConfig(id="a", username="U080", domain="208.87.170.99")

    assert SipEndpoint._format_invite_local_uri(cfg) == ""


def test_invite_local_uri_keeps_transport_and_port() -> None:
    cfg = AccountConfig(
        id="a",
        display_name='961714"88860',
        username="U080",
        domain="sip.example.test",
        transport="tcp",
        port=5070,
    )

    assert SipEndpoint._format_invite_local_uri(cfg) == (
        '"96171488860" <sip:U080@sip.example.test:5070;transport=tcp>'
    )
