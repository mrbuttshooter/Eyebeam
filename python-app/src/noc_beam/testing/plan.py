from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

TestMode = Literal["matrix", "paired", "fan-out", "fan-in"]
PassCriterion = Literal["reachability", "full-call"]


@dataclass
class TestSpec:
    callers: list[str]
    targets: list[str]
    mode: TestMode
    pass_criterion: PassCriterion
    parallel: int
    hold_seconds: float
    timeout_seconds: float

    def __post_init__(self) -> None:
        self.parallel = min(max(self.parallel, 1), 16)
        self.hold_seconds = max(self.hold_seconds, 0.0)
        self.timeout_seconds = max(self.timeout_seconds, 0.1)


@dataclass(frozen=True)
class TestCall:
    index: int
    caller_number: str
    target_number: str


def normalise_lines(text: str) -> list[str]:
    return [line for raw_line in text.splitlines() if (line := raw_line.strip())]


def expand(spec: TestSpec) -> list[TestCall]:
    if spec.mode not in ("matrix", "paired", "fan-out", "fan-in"):
        raise ValueError(f"Unknown test plan mode: {spec.mode}")

    if not spec.targets:
        return []
    # Empty callers list -> treat as a single wildcard caller so the
    # runner's _resolve_account falls through to "use the active
    # account". The common demo workflow is "paste 20 numbers into
    # targets, leave callers blank, click Run" -- previously this
    # silently returned [] (no calls).
    callers = spec.callers if spec.callers else ["*"]

    pairs: list[tuple[str, str]]
    if spec.mode == "matrix":
        pairs = [(caller, target) for caller in callers for target in spec.targets]
    elif spec.mode == "paired":
        # Paired mode is a strict 1:1 zip — but historically (and per
        # operator mental model) "I have ONE caller and many targets,
        # call all of them from that caller" is the most common batch
        # shape. zip() of a 1-element list with N targets silently
        # drops N-1 targets, which is a footgun: operator pastes 100
        # numbers, clicks Run, sees only 1 call fire, the other 99
        # vanish without a trace.
        #
        # Defensive: when callers has exactly 1 entry but targets has
        # more, promote to fan-out semantics (that single caller is
        # used for every target). Same for the inverse (1 target,
        # many callers => fan-in). Otherwise zip as before.
        if len(callers) == 1 and len(spec.targets) > 1:
            pairs = [(callers[0], target) for target in spec.targets]
        elif len(spec.targets) == 1 and len(callers) > 1:
            pairs = [(caller, spec.targets[0]) for caller in callers]
        else:
            pairs = list(zip(callers, spec.targets, strict=False))
    elif spec.mode == "fan-out":
        pairs = [(callers[0], target) for target in spec.targets]
    else:
        pairs = [(caller, spec.targets[0]) for caller in callers]

    return [
        TestCall(index=index, caller_number=caller, target_number=target)
        for index, (caller, target) in enumerate(pairs, start=1)
    ]
