from __future__ import annotations

from noc_beam.audio.fas_evidence import FasEvidence, FasEvidenceAccumulator


def test_sticky_positive_survives_later_weaker_evidence():
    acc = FasEvidenceAccumulator()
    acc.add_many([
        FasEvidence(
            kind="post_answer_call_progress",
            source="tone_cadence",
            weight=5,
            confidence=0.9,
            message="ringback after answer",
            sticky=True,
        )
    ])
    acc.add_many([
        FasEvidence(
            kind="post_answer_call_progress",
            source="tone_cadence",
            weight=0,
            confidence=0.2,
            message="weak later signal",
            sticky=False,
        )
    ])

    assert acc.has_sticky_positive()
    assert "ringback after answer" in acc.reasons_text()
    assert "weak later signal" not in acc.reasons_text()
