"""FAS verdict synthesis.

Takes the per-signal scores (features + model outputs + fingerprint match)
and emits a final verdict + confidence + human-readable reason list.

Verdicts:
    LIKELY_REAL   - confident the answer is a live human
    INCONCLUSIVE  - insufficient data
    SUSPICIOUS    - some FAS signals fired, not enough for high confidence
    LIKELY_FAS    - strong evidence of False Answer Supervision

Score weights (per signal):
    fingerprint_reuse  : +3  (very high signal -- exact repeat across calls)
    ringback_after_200 : +3  (deterministic via Goertzel)
    silence            : +2
    recording_aasist   : +2
    music_on_hold      : +1
    generic_ivr        : +1
    speech_present_real: -3  (positive evidence of real call)
    vad_speech_high    : -2

Thresholds (balanced preset):
    score >=  5  -> LIKELY_FAS
    score >=  2  -> SUSPICIOUS
    score <= -3 with no positive FAS signals -> LIKELY_REAL
    otherwise INCONCLUSIVE
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from noc_beam.audio.fas_features import FeatureBundle


# Per-signal weights (balanced preset). The "aggressive" / "conservative"
# presets scale the thresholds, not these.
WEIGHT_FINGERPRINT_REUSE = 3
WEIGHT_RINGBACK = 3
WEIGHT_SILENCE = 2
WEIGHT_RECORDING_AASIST = 2
WEIGHT_MOH = 1
WEIGHT_GENERIC_IVR = 1
WEIGHT_REAL_SPEECH = -3
WEIGHT_VAD_HIGH = -2

# Verdict thresholds per sensitivity preset.
PRESETS: dict[str, dict[str, float]] = {
    "conservative": {"fas": 6, "suspicious": 3},
    "balanced":     {"fas": 5, "suspicious": 2},
    "aggressive":   {"fas": 4, "suspicious": 1},
}


@dataclass
class FasVerdict:
    verdict: str
    confidence: float            # 0..1
    score: int                   # signed integer; negative = real-call evidence
    reasons: list[str] = field(default_factory=list)

    def reasons_text(self) -> str:
        return "; ".join(self.reasons) if self.reasons else ""


def synthesise(
    *,
    features: FeatureBundle,
    silero_speech_prob: float | None,
    aasist_spoof_prob: float | None,
    panns: dict[str, float] | None,
    fingerprint_sim: float,         # 0..1, similarity to closest prior FP
    fingerprint_threshold: float = 0.90,
    sensitivity: str = "balanced",
) -> FasVerdict:
    """Map a bag of signals to a single verdict + confidence."""
    thresholds = PRESETS.get(sensitivity, PRESETS["balanced"])
    score = 0
    reasons: list[str] = []
    deterministic_positive = False

    # ----- Positive FAS evidence -----
    if fingerprint_sim >= fingerprint_threshold:
        score += WEIGHT_FINGERPRINT_REUSE
        reasons.append(f"audio matches a previous call ({fingerprint_sim:.0%})")
        deterministic_positive = True

    # Goertzel scores on real PSTN tones tend to land 0.15..0.35 because
    # the input passes through G.711 + multiple carrier hops before
    # reaching us; the threshold is set against that range, not the
    # 0.7+ a synthetic clean sine would produce.
    if features.ringback_score >= 0.15:
        score += WEIGHT_RINGBACK
        reasons.append(
            f"ringback tone after answer ({features.ringback_freq_hz:.0f} Hz)"
        )
        deterministic_positive = True

    if features.silence_score >= 0.70:
        score += WEIGHT_SILENCE
        reasons.append(f"silence ({features.silence_score:.0%} of window)")

    if aasist_spoof_prob is not None and aasist_spoof_prob >= 0.70:
        score += WEIGHT_RECORDING_AASIST
        reasons.append(f"audio detected as recorded/synthetic ({aasist_spoof_prob:.0%})")

    if panns is not None:
        if panns.get("music", 0.0) >= 0.50 and panns.get("speech", 0.0) < 0.30:
            score += WEIGHT_MOH
            reasons.append(f"music on hold ({panns['music']:.0%})")
        if panns.get("ringing", 0.0) >= 0.50:
            score += WEIGHT_GENERIC_IVR
            reasons.append(f"telephony tone classified ({panns['ringing']:.0%})")

    # ----- Negative (real-call) evidence -----
    if silero_speech_prob is not None and silero_speech_prob >= 0.60:
        score += WEIGHT_VAD_HIGH
        reasons.append(f"continuous speech detected ({silero_speech_prob:.0%})")

    # Require Silero corroboration before crediting "live conversation":
    # random noise bursts also produce many short energy runs with low
    # stability. Without VAD the rule mis-fires on canned recordings.
    if (
        features.speech_run_count >= 3
        and features.energy_stability < 0.5
        and features.silence_score < 0.3
        and silero_speech_prob is not None
        and silero_speech_prob >= 0.40
    ):
        score += WEIGHT_REAL_SPEECH
        reasons.append("varied speech pattern (live conversation)")

    # ----- Verdict mapping -----
    if score >= thresholds["fas"]:
        verdict = "LIKELY_FAS"
    elif score >= thresholds["suspicious"]:
        verdict = "SUSPICIOUS"
    elif score <= -3 and not deterministic_positive:
        verdict = "LIKELY_REAL"
    else:
        verdict = "INCONCLUSIVE"

    # Confidence: distance from "INCONCLUSIVE" centre, capped at 1.0.
    # Deterministic positives (ringback / fingerprint) pin confidence high.
    if deterministic_positive and verdict == "LIKELY_FAS":
        confidence = min(1.0, 0.75 + 0.05 * (score - thresholds["fas"]))
    elif verdict == "LIKELY_FAS":
        confidence = min(1.0, 0.50 + 0.10 * (score - thresholds["fas"]))
    elif verdict == "SUSPICIOUS":
        confidence = min(0.65, 0.30 + 0.10 * (score - thresholds["suspicious"]))
    elif verdict == "LIKELY_REAL":
        confidence = min(0.90, 0.50 + 0.05 * (-score - 3))
    else:
        confidence = 0.15

    return FasVerdict(
        verdict=verdict,
        confidence=round(confidence, 3),
        score=score,
        reasons=reasons,
    )


def signals_summary(
    *,
    features: FeatureBundle,
    silero_speech_prob: float | None,
    aasist_spoof_prob: float | None,
    panns: dict[str, float] | None,
    fingerprint_sim: float,
) -> dict[str, Any]:
    """Diagnostic dump for CDR Detail. Not used in verdict logic."""
    return {
        "silence_score": round(features.silence_score, 3),
        "ringback_score": round(features.ringback_score, 3),
        "ringback_freq_hz": round(features.ringback_freq_hz, 1),
        "energy_stability": round(features.energy_stability, 3),
        "speech_run_count": features.speech_run_count,
        "rms_db": round(features.rms_db, 1),
        "silero_speech_prob": (round(silero_speech_prob, 3)
                               if silero_speech_prob is not None else None),
        "aasist_spoof_prob": (round(aasist_spoof_prob, 3)
                              if aasist_spoof_prob is not None else None),
        "panns": ({k: round(v, 3) for k, v in panns.items()}
                  if panns is not None else None),
        "fingerprint_sim": round(fingerprint_sim, 3),
    }
