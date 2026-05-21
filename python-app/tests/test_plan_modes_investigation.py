"""Exhaustive investigation of TestSpec.expand() modes.

Every batch shape an operator can construct in the Test Runner UI:

  Mode      | Operator intent
  ----------|----------------------------------------------------------
  matrix    | Cross every caller with every target (M*N calls)
  paired    | Zip callers and targets 1:1 (min(M,N) calls)
  fan-out   | One caller calls every target (N calls)
  fan-in    | Every caller calls one target (M calls)

For each mode, we test every list-length permutation:
  - empty callers / empty targets
  - 1 × 1
  - 1 × N (single caller, many targets)
  - N × 1 (many callers, single target)
  - N × N (equal, common case)
  - N × M with N < M
  - N × M with N > M

This is the file you read when an operator says "I pasted 100 numbers
and only X actually ran" — every silent-drop / unexpected-behavior path
is reproduced here.
"""
from __future__ import annotations

import pytest

from noc_beam.testing.plan import TestSpec, expand


def make_spec(callers: list[str], targets: list[str], mode: str) -> TestSpec:
    return TestSpec(
        callers=callers,
        targets=targets,
        mode=mode,  # type: ignore[arg-type]
        pass_criterion="reachability",
        parallel=4,
        hold_seconds=0.0,
        timeout_seconds=1.0,
    )


def pairs_of(spec_calls) -> list[tuple[str, str]]:
    return [(c.caller_number, c.target_number) for c in spec_calls]


# =================================================================
# EMPTY EDGE CASES (apply to all modes)
# =================================================================
@pytest.mark.parametrize("mode", ["matrix", "paired", "fan-out", "fan-in"])
def test_empty_targets_yields_no_calls(mode: str) -> None:
    """No targets => no calls, regardless of mode."""
    assert expand(make_spec(["1001", "1002"], [], mode)) == []


@pytest.mark.parametrize("mode", ["matrix", "paired", "fan-out", "fan-in"])
def test_empty_callers_falls_back_to_wildcard(mode: str) -> None:
    """Empty callers list means 'use the active account' (wildcard `*`).

    Common workflow: paste 20 numbers in targets, leave callers blank.
    Pre-fix behaviour silently returned [] (no calls fired).
    """
    calls = expand(make_spec([], ["2001", "2002"], mode))
    if mode == "fan-in":
        # fan-in with empty callers => wildcard caller × 1 target = 1 call
        assert pairs_of(calls) == [("*", "2001")]
    else:
        # matrix/paired/fan-out with empty callers => wildcard × every target
        # paired now auto-promotes to fan-out for 1 caller × N targets
        assert pairs_of(calls) == [("*", "2001"), ("*", "2002")]


# =================================================================
# MATRIX MODE — Cartesian product
# =================================================================
def test_matrix_1x1() -> None:
    """1 caller, 1 target => 1 call."""
    pairs = pairs_of(expand(make_spec(["1001"], ["2001"], "matrix")))
    assert pairs == [("1001", "2001")]


def test_matrix_1xN_single_caller_many_targets() -> None:
    """1 caller × 3 targets => 3 calls (caller calls each target)."""
    pairs = pairs_of(expand(make_spec(["1001"], ["2001", "2002", "2003"], "matrix")))
    assert pairs == [("1001", "2001"), ("1001", "2002"), ("1001", "2003")]


def test_matrix_Nx1_many_callers_single_target() -> None:
    """3 callers × 1 target => 3 calls (each caller dials the same target)."""
    pairs = pairs_of(expand(make_spec(["1001", "1002", "1003"], ["2001"], "matrix")))
    assert pairs == [("1001", "2001"), ("1002", "2001"), ("1003", "2001")]


def test_matrix_NxN_equal_sized() -> None:
    """2 × 2 = 4 calls (full Cartesian)."""
    pairs = pairs_of(expand(make_spec(["1001", "1002"], ["2001", "2002"], "matrix")))
    assert pairs == [
        ("1001", "2001"), ("1001", "2002"),
        ("1002", "2001"), ("1002", "2002"),
    ]


def test_matrix_NxM_more_targets_than_callers() -> None:
    """2 callers × 5 targets = 10 calls."""
    callers = ["1001", "1002"]
    targets = [f"2{i:03d}" for i in range(5)]
    pairs = pairs_of(expand(make_spec(callers, targets, "matrix")))
    assert len(pairs) == 10
    # Each caller appears with each target exactly once
    assert set(pairs) == {(c, t) for c in callers for t in targets}


def test_matrix_NxM_more_callers_than_targets() -> None:
    """5 callers × 2 targets = 10 calls (no silent drop)."""
    callers = [f"1{i:03d}" for i in range(5)]
    targets = ["2001", "2002"]
    pairs = pairs_of(expand(make_spec(callers, targets, "matrix")))
    assert len(pairs) == 10
    assert set(pairs) == {(c, t) for c in callers for t in targets}


# =================================================================
# PAIRED MODE — zip 1:1 (with auto-promote when one side is single)
# =================================================================
def test_paired_1x1() -> None:
    """1:1 zip works straight."""
    pairs = pairs_of(expand(make_spec(["1001"], ["2001"], "paired")))
    assert pairs == [("1001", "2001")]


def test_paired_1xN_auto_promotes_to_fan_out() -> None:
    """THE PRODUCTION BUG fix: 1 caller × N targets used to silently
    drop N-1 targets via zip(). Now auto-promotes to fan-out so all
    targets actually get dialed."""
    pairs = pairs_of(expand(make_spec(["1001"], ["2001", "2002", "2003"], "paired")))
    assert pairs == [("1001", "2001"), ("1001", "2002"), ("1001", "2003")]


def test_paired_Nx1_auto_promotes_to_fan_in() -> None:
    """N callers × 1 target also auto-promotes (fan-in semantics)."""
    pairs = pairs_of(expand(make_spec(["1001", "1002", "1003"], ["2001"], "paired")))
    assert pairs == [("1001", "2001"), ("1002", "2001"), ("1003", "2001")]


def test_paired_NxN_equal_sized_is_real_zip() -> None:
    """When both lists have >1 entries with equal length, real 1:1 zip."""
    pairs = pairs_of(expand(make_spec(
        ["1001", "1002", "1003"],
        ["2001", "2002", "2003"],
        "paired",
    )))
    assert pairs == [("1001", "2001"), ("1002", "2002"), ("1003", "2003")]


def test_paired_NxM_with_both_multi_entries_uses_strict_false_zip() -> None:
    """3 callers × 5 targets in paired mode: only 3 pairs (zip behavior).

    NOTE: this is the ONE remaining silent-drop case in paired mode.
    Operator using paired with mismatched multi-entry lists gets only
    min(M,N) pairs. This is intentional (paired = strict 1:1), but
    document it loudly so we don't regress to silent N+M behavior.
    """
    callers = ["1001", "1002", "1003"]
    targets = ["2001", "2002", "2003", "2004", "2005"]
    pairs = pairs_of(expand(make_spec(callers, targets, "paired")))
    # Operator picked the wrong mode; only first 3 pairs survive.
    # For "every caller hits every target" use matrix mode.
    assert pairs == [("1001", "2001"), ("1002", "2002"), ("1003", "2003")]


def test_paired_NxM_more_callers_than_targets_drops_extra_callers() -> None:
    """5 callers × 3 targets in paired => only 3 pairs; last 2 callers
    silently dropped. Same warning as above — paired is strict-zip."""
    pairs = pairs_of(expand(make_spec(
        ["1001", "1002", "1003", "1004", "1005"],
        ["2001", "2002", "2003"],
        "paired",
    )))
    assert pairs == [("1001", "2001"), ("1002", "2002"), ("1003", "2003")]


# =================================================================
# FAN-OUT — first caller × every target
# =================================================================
def test_fan_out_1xN() -> None:
    """Standard fan-out: 1 caller dials all targets."""
    pairs = pairs_of(expand(make_spec(["1001"], ["2001", "2002", "2003"], "fan-out")))
    assert pairs == [("1001", "2001"), ("1001", "2002"), ("1001", "2003")]


def test_fan_out_NxN_only_first_caller_used() -> None:
    """In fan-out, callers[0] is used; subsequent callers ignored.
    Operator who wants every caller to dial every target should use matrix."""
    pairs = pairs_of(expand(make_spec(
        ["1001", "1002"],
        ["2001", "2002", "2003"],
        "fan-out",
    )))
    assert pairs == [("1001", "2001"), ("1001", "2002"), ("1001", "2003")]


def test_fan_out_1x1() -> None:
    """Trivial single call."""
    pairs = pairs_of(expand(make_spec(["1001"], ["2001"], "fan-out")))
    assert pairs == [("1001", "2001")]


def test_fan_out_empty_callers_uses_wildcard() -> None:
    """Empty callers => `*` (active account) dials all targets."""
    pairs = pairs_of(expand(make_spec([], ["2001", "2002"], "fan-out")))
    assert pairs == [("*", "2001"), ("*", "2002")]


# =================================================================
# FAN-IN — every caller × first target
# =================================================================
def test_fan_in_Nx1() -> None:
    """Standard fan-in: every caller dials one target.

    Use case: 10 different supplier accounts each call the same test
    number to compare per-supplier behaviour."""
    pairs = pairs_of(expand(make_spec(
        ["1001", "1002", "1003"],
        ["2001"],
        "fan-in",
    )))
    assert pairs == [("1001", "2001"), ("1002", "2001"), ("1003", "2001")]


def test_fan_in_NxN_only_first_target_used() -> None:
    """In fan-in, targets[0] is used; subsequent targets ignored."""
    pairs = pairs_of(expand(make_spec(
        ["1001", "1002"],
        ["2001", "2002", "2003"],
        "fan-in",
    )))
    assert pairs == [("1001", "2001"), ("1002", "2001")]


def test_fan_in_1x1() -> None:
    pairs = pairs_of(expand(make_spec(["1001"], ["2001"], "fan-in")))
    assert pairs == [("1001", "2001")]


# =================================================================
# CROSS-CHECK — paired auto-promote should produce EXACTLY the same
# output as fan-out / fan-in when caller-count or target-count is 1
# =================================================================
def test_paired_1xN_equals_fan_out_1xN() -> None:
    callers = ["1001"]
    targets = ["2001", "2002", "2003", "2004"]
    assert pairs_of(expand(make_spec(callers, targets, "paired"))) == \
           pairs_of(expand(make_spec(callers, targets, "fan-out")))


def test_paired_Nx1_equals_fan_in_Nx1() -> None:
    callers = ["1001", "1002", "1003", "1004"]
    targets = ["2001"]
    assert pairs_of(expand(make_spec(callers, targets, "paired"))) == \
           pairs_of(expand(make_spec(callers, targets, "fan-in")))


# =================================================================
# REAL-WORLD SCENARIOS (the operator's actual batch shapes)
# =================================================================
def test_real_world_one_supplier_dials_100_destinations() -> None:
    """Operator: pick one supplier, paste 100 destination numbers, click Run.

    With paired (UI default) + the auto-promote fix, all 100 fire.
    Without the fix, only the first would fire and 99 would vanish.
    """
    targets = [f"+1234567{i:03d}" for i in range(100)]
    calls = expand(make_spec(["U080"], targets, "paired"))
    assert len(calls) == 100
    assert all(c.caller_number == "U080" for c in calls)
    # Indices preserved (1..100)
    assert [c.index for c in calls] == list(range(1, 101))


def test_real_world_test_3_suppliers_against_same_destination() -> None:
    """Operator picks fan-in to compare suppliers on a known test number."""
    callers = ["U080", "U207", "U216"]
    calls = expand(make_spec(callers, ["+96171488860"], "fan-in"))
    assert len(calls) == 3
    assert all(c.target_number == "+96171488860" for c in calls)
    assert [c.caller_number for c in calls] == callers


def test_real_world_full_matrix_3_suppliers_x_10_destinations() -> None:
    """Operator wants exhaustive matrix: 3 suppliers × 10 destinations = 30 calls."""
    callers = ["U080", "U207", "U216"]
    targets = [f"+1234567{i:03d}" for i in range(10)]
    calls = expand(make_spec(callers, targets, "matrix"))
    assert len(calls) == 30
    counts_per_caller = {c: sum(1 for x in calls if x.caller_number == c) for c in callers}
    assert all(n == 10 for n in counts_per_caller.values())
