from __future__ import annotations

import pytest

from noc_beam.testing import plan


def make_spec(
    callers: list[str],
    targets: list[str],
    mode: str,
    parallel: int = 4,
) -> plan.TestSpec:
    return plan.TestSpec(
        callers=callers,
        targets=targets,
        mode=mode,  # type: ignore[arg-type]
        pass_criterion="reachability",
        parallel=parallel,
        hold_seconds=5.0,
        timeout_seconds=30.0,
    )


def test_matrix_expands_in_caller_major_order() -> None:
    spec = make_spec(
        callers=["1001", "1002", "1003"],
        targets=["2001", "2002", "2003", "2004"],
        mode="matrix",
    )

    assert plan.expand(spec) == [
        plan.TestCall(1, "1001", "2001"),
        plan.TestCall(2, "1001", "2002"),
        plan.TestCall(3, "1001", "2003"),
        plan.TestCall(4, "1001", "2004"),
        plan.TestCall(5, "1002", "2001"),
        plan.TestCall(6, "1002", "2002"),
        plan.TestCall(7, "1002", "2003"),
        plan.TestCall(8, "1002", "2004"),
        plan.TestCall(9, "1003", "2001"),
        plan.TestCall(10, "1003", "2002"),
        plan.TestCall(11, "1003", "2003"),
        plan.TestCall(12, "1003", "2004"),
    ]


def test_paired_mismatched_lengths_uses_shorter_side() -> None:
    spec = make_spec(
        callers=["1001", "1002", "1003"],
        targets=["2001", "2002"],
        mode="paired",
    )

    assert plan.expand(spec) == [
        plan.TestCall(1, "1001", "2001"),
        plan.TestCall(2, "1002", "2002"),
    ]


def test_fan_out_uses_first_caller_for_all_targets() -> None:
    spec = make_spec(
        callers=["1001"],
        targets=["2001", "2002", "2003", "2004", "2005"],
        mode="fan-out",
    )

    assert plan.expand(spec) == [
        plan.TestCall(1, "1001", "2001"),
        plan.TestCall(2, "1001", "2002"),
        plan.TestCall(3, "1001", "2003"),
        plan.TestCall(4, "1001", "2004"),
        plan.TestCall(5, "1001", "2005"),
    ]


def test_fan_in_uses_first_target_for_all_callers() -> None:
    spec = make_spec(
        callers=["1001", "1002", "1003", "1004", "1005"],
        targets=["2001"],
        mode="fan-in",
    )

    assert plan.expand(spec) == [
        plan.TestCall(1, "1001", "2001"),
        plan.TestCall(2, "1002", "2001"),
        plan.TestCall(3, "1003", "2001"),
        plan.TestCall(4, "1004", "2001"),
        plan.TestCall(5, "1005", "2001"),
    ]


def test_normalise_lines_strips_drops_blanks_and_preserves_duplicates() -> None:
    assert plan.normalise_lines(" 1001 \n\n1002\n  \n1001\t\n") == [
        "1001",
        "1002",
        "1001",
    ]


@pytest.mark.parametrize("mode", ["matrix", "paired", "fan-out", "fan-in"])
def test_empty_targets_returns_no_calls(mode: str) -> None:
    """Empty targets => no calls; an empty targets list has no destinations
    to dial regardless of how many callers."""
    assert plan.expand(make_spec(["1001"], [], mode)) == []


@pytest.mark.parametrize("mode", ["matrix", "paired", "fan-out", "fan-in"])
def test_empty_callers_uses_wildcard_active_account(mode: str) -> None:
    """Empty callers => wildcard `*` (active account). This is the common
    'paste targets, leave callers blank, click Run' workflow — before the
    fix this silently returned [] and no calls fired. Now the wildcard
    caller dials every target via the currently-selected account."""
    calls = plan.expand(make_spec([], ["2001"], mode))
    assert len(calls) == 1
    assert calls[0].caller_number == "*"
    assert calls[0].target_number == "2001"


def test_unknown_mode_raises_even_when_inputs_are_empty() -> None:
    spec = make_spec([], [], "unknown")

    with pytest.raises(ValueError):
        plan.expand(spec)


@pytest.mark.parametrize(
    ("requested_parallel", "expected_parallel"),
    [
        (-3, 1),
        (0, 1),
        (1, 1),
        (8, 8),
        (16, 16),
        (17, 16),
    ],
)
def test_parallel_is_clamped_to_one_through_sixteen(
    requested_parallel: int,
    expected_parallel: int,
) -> None:
    spec = make_spec(["1001"], ["2001"], "paired", parallel=requested_parallel)

    assert spec.parallel == expected_parallel


# ---------------------------------------------------------------------------
# times multiplier (non-fas-sweep modes)
# ---------------------------------------------------------------------------


def _make_spec_with_times(
    callers: list[str],
    targets: list[str],
    mode: str,
    times: int,
) -> plan.TestSpec:
    return plan.TestSpec(
        callers=callers,
        targets=targets,
        mode=mode,  # type: ignore[arg-type]
        pass_criterion="reachability",
        parallel=4,
        hold_seconds=5.0,
        timeout_seconds=30.0,
        times=times,
    )


@pytest.mark.parametrize("mode", ["matrix", "paired", "fan-out", "fan-in"])
def test_times_multiplies_call_count(mode: str) -> None:
    """times=N repeats every (caller, target) pair N times. So 1 caller x
    1 target x times=3 -> 3 TestCall rows with ids 1, 2, 3."""
    spec = _make_spec_with_times(["1001"], ["2001"], mode, times=3)
    calls = plan.expand(spec)
    assert len(calls) == 3
    assert [c.index for c in calls] == [1, 2, 3]
    assert all(c.caller_number == "1001" for c in calls)
    assert all(c.target_number == "2001" for c in calls)


def test_times_multiplies_matrix_pairs() -> None:
    """2 callers x 3 targets x times=4 -> 24 calls."""
    spec = _make_spec_with_times(
        callers=["1001", "1002"],
        targets=["2001", "2002", "2003"],
        mode="matrix",
        times=4,
    )
    calls = plan.expand(spec)
    assert len(calls) == 24
    # First pair (1001, 2001) repeats 4 times consecutively.
    first_four = calls[:4]
    assert all(c.caller_number == "1001" and c.target_number == "2001" for c in first_four)


@pytest.mark.parametrize(
    ("requested_times", "expected_times"),
    [(-3, 1), (0, 1), (1, 1), (25, 25), (50, 50), (51, 50), (1000, 50)],
)
def test_times_is_clamped_to_one_through_fifty(
    requested_times: int, expected_times: int
) -> None:
    spec = _make_spec_with_times(["1001"], ["2001"], "paired", times=requested_times)
    assert spec.times == expected_times


# ---------------------------------------------------------------------------
# fas-sweep mode + tries_per_pair
# ---------------------------------------------------------------------------


def test_fas_sweep_uses_matrix_shape_times_tries_per_pair() -> None:
    """fas-sweep is matrix-shaped (every caller x every target) and each
    pair repeats tries_per_pair times."""
    spec = plan.TestSpec(
        callers=["1001", "1002"],
        targets=["2001", "2002"],
        mode="fas-sweep",
        pass_criterion="reachability",
        parallel=4,
        hold_seconds=5.0,
        timeout_seconds=30.0,
        tries_per_pair=3,
    )
    calls = plan.expand(spec)
    # 2 callers * 2 targets * 3 tries = 12 calls
    assert len(calls) == 12
    # First pair (1001, 2001) repeats 3 times consecutively.
    first_three = calls[:3]
    assert all(c.caller_number == "1001" and c.target_number == "2001" for c in first_three)


def test_fas_sweep_ignores_times_field_uses_tries_per_pair() -> None:
    """In fas-sweep mode, `times` is ignored; only `tries_per_pair`
    multiplies the matrix."""
    spec = plan.TestSpec(
        callers=["1001"],
        targets=["2001"],
        mode="fas-sweep",
        pass_criterion="reachability",
        parallel=4,
        hold_seconds=5.0,
        timeout_seconds=30.0,
        times=10,            # should NOT multiply for fas-sweep
        tries_per_pair=2,
    )
    calls = plan.expand(spec)
    assert len(calls) == 2


def test_unknown_mode_still_raises_after_fas_sweep_added() -> None:
    spec = plan.TestSpec(
        callers=[],
        targets=[],
        mode="unknown",  # type: ignore[arg-type]
        pass_criterion="reachability",
        parallel=4,
        hold_seconds=5.0,
        timeout_seconds=30.0,
    )
    with pytest.raises(ValueError):
        plan.expand(spec)


@pytest.mark.parametrize(
    ("requested", "expected"),
    [(-1, 1), (0, 1), (1, 1), (4, 4), (50, 50), (51, 50)],
)
def test_tries_per_pair_is_clamped_to_one_through_fifty(
    requested: int, expected: int
) -> None:
    spec = plan.TestSpec(
        callers=["1001"],
        targets=["2001"],
        mode="fas-sweep",
        pass_criterion="reachability",
        parallel=4,
        hold_seconds=5.0,
        timeout_seconds=30.0,
        tries_per_pair=requested,
    )
    assert spec.tries_per_pair == expected


def test_jitter_fields_default_to_30_and_120_seconds() -> None:
    spec = plan.TestSpec(
        callers=["1001"],
        targets=["2001"],
        mode="fas-sweep",
        pass_criterion="reachability",
        parallel=4,
        hold_seconds=5.0,
        timeout_seconds=30.0,
    )
    assert spec.jitter_low_s == 30.0
    assert spec.jitter_high_s == 120.0


def test_jitter_high_clamped_to_at_least_jitter_low() -> None:
    """If the caller passes jitter_high < jitter_low (operator typo),
    bump high up to low so the runtime jitter rng never errors with
    high < low."""
    spec = plan.TestSpec(
        callers=["1001"],
        targets=["2001"],
        mode="fas-sweep",
        pass_criterion="reachability",
        parallel=4,
        hold_seconds=5.0,
        timeout_seconds=30.0,
        jitter_low_s=60.0,
        jitter_high_s=10.0,
    )
    assert spec.jitter_low_s == 60.0
    assert spec.jitter_high_s == 60.0
