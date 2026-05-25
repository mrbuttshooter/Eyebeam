from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6.QtCore")

from noc_beam.sip.call_manager import CallManager, CallRecord, CallState  # noqa: E402
from noc_beam.ui.phone_shell import PhoneShell  # noqa: E402


class _DummyRinger:
    def stop(self) -> None:
        pass


class _FailureToneSpy:
    def __init__(self) -> None:
        self.played: list[int | None] = []

    def play_for_code(self, code: int | None) -> None:
        self.played.append(code)


class _DummyEndpoint:
    def find_call(self, _call_id: int):
        return None


class _ShellHarness:
    _on_call_state = PhoneShell._on_call_state
    _on_call_ended = PhoneShell._on_call_ended

    def __init__(self) -> None:
        self.calls = CallManager()
        self.ringer = _DummyRinger()
        self.failure_tone = _FailureToneSpy()
        self._final_call_results: dict[int, tuple[int, bool]] = {}
        self._last_snapshots = {}
        self._selected_call_id = None
        # Added by CANCEL-fix commit e4603e1: PhoneShell tracks which
        # calls reached CONFIRMED so it knows whether to play the
        # answered-then-disconnected vs failure-tone path. The test
        # harness needs the attribute to exist (any iterable works).
        self._fas_confirmed_call_ids: set[int] = set()
        self._pending_fas_media: dict[int, object] = {}
        self._test_runner_call_ids: set[int] = set()

    def _maybe_write_cdr(self, _call_id: int) -> None:
        pass

    # Added by CANCEL-fix commit e4603e1: PhoneShell._on_call_state now
    # calls _note_fas_call_state + _is_test_runner_call on every state
    # change so the FAS engine can correlate evidence with call
    # lifecycle. The test harness only stubs the methods it needs;
    # provide no-ops so the cached-failure-tone test still exercises
    # _on_call_state cleanly without depending on FAS / runner state.
    def _note_fas_call_state(self, _call_id: int, _state) -> None:
        pass

    def _is_test_runner_call(self, _call_id: int) -> bool:
        return False


def test_failure_tone_uses_cached_final_code_after_call_record_removed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "noc_beam.ui.phone_shell.SipEndpoint.instance",
        staticmethod(lambda: _DummyEndpoint()),
    )
    shell = _ShellHarness()
    shell.calls.register(
        CallRecord(call_id=22, account_id="acc", state=CallState.CALLING)
    )

    shell._on_call_state("acc", 22, "DISCONNECTED", 503, "Service Unavailable")
    assert shell.calls.get(22) is None

    shell._on_call_ended(22)

    assert shell.failure_tone.played == [503]
