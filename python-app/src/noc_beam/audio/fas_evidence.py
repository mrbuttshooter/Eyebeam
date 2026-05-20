"""Structured evidence for False Answer Supervision decisions."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class FasEvidence:
    """One explainable signal contributing to a FAS verdict."""

    kind: str
    source: str
    weight: int = 0
    confidence: float = 0.0
    message: str = ""
    value: float | str | None = None
    threshold: float | str | None = None
    sticky: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def reason_text(self) -> str:
        return self.message or self.kind.replace("_", " ")


class FasEvidenceAccumulator:
    """Per-call rolling evidence memory.

    Sticky evidence survives later weaker snapshots so deterministic
    signals like post-answer ringback or fingerprint reuse cannot be
    hidden by a later inconclusive window.
    """

    def __init__(self) -> None:
        self._items: dict[str, tuple[FasEvidence, float]] = {}

    def add_many(self, evidence: list[FasEvidence]) -> None:
        now = time.monotonic()
        for item in evidence:
            key = self._key(item)
            current = self._items.get(key)
            if current is None:
                self._items[key] = (item, now)
                continue
            old, old_seen = current
            if old.sticky and not item.sticky:
                continue
            if item.confidence >= old.confidence or item.sticky:
                self._items[key] = (item, now)
            else:
                self._items[key] = (old, old_seen)

    def items(self, *, max_age_s: float = 30.0) -> list[FasEvidence]:
        now = time.monotonic()
        out: list[FasEvidence] = []
        for item, seen_at in self._items.values():
            if item.sticky or now - seen_at <= max_age_s:
                out.append(item)
        return out

    def has_sticky_positive(self) -> bool:
        return any(item.sticky and item.weight > 0 for item in self.items())

    def reasons_text(self) -> str:
        seen: set[str] = set()
        reasons: list[str] = []
        for item in sorted(self.items(), key=lambda e: (not e.sticky, -e.confidence, e.kind)):
            text = item.reason_text()
            if text and text not in seen:
                reasons.append(text)
                seen.add(text)
        return "; ".join(reasons)

    @staticmethod
    def _key(item: FasEvidence) -> str:
        scope = item.metadata.get("scope", "")
        return f"{item.source}:{item.kind}:{scope}"
