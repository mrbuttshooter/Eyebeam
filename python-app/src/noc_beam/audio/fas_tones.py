"""Call-progress tone and cadence detection for FAS evidence."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from noc_beam.audio.fas_features import goertzel_magnitude


@dataclass(frozen=True)
class ToneDetection:
    label: str = ""
    score: float = 0.0
    freq_hz: float = 0.0
    cadence: str = ""


def detect_call_progress_tone(samples: np.ndarray, sample_rate: int) -> ToneDetection:
    """Detect common PSTN call-progress tones in an answered audio window.

    Scores are intentionally conservative: frequency purity alone is not
    enough. Cadence or a well-known multi-frequency sequence is required
    before returning high-confidence labels.
    """
    if samples.size < int(sample_rate * 0.5):
        return ToneDetection()

    frame_ms = 100
    frame_n = max(int(sample_rate * frame_ms / 1000), 320)
    frames = [
        samples[start:start + frame_n]
        for start in range(0, samples.size - frame_n + 1, frame_n)
    ]
    if not frames:
        return ToneDetection()

    mags = {
        freq: np.array([goertzel_magnitude(frame, sample_rate, freq) for frame in frames])
        for freq in (350.0, 425.0, 440.0, 480.0, 620.0, 950.0, 1100.0, 1400.0, 1800.0, 2100.0)
    }

    # SIT / no-service announcements: three ordered tones near
    # 950/1400/1800 Hz. Use presence in order; exact cadence varies by network.
    sit_score = _sit_score(mags[950.0], mags[1400.0], mags[1800.0])
    if sit_score >= 0.40:
        return ToneDetection("SIT_NO_SERVICE", sit_score, 1400.0, "950/1400/1800 sequence")

    # Fax CNG/CED should be a separate machine signal, not FAS by itself.
    cng_score = _cadence_score(mags[1100.0], expected_on_s=0.5, expected_off_s=3.0)
    if cng_score >= 0.35:
        return ToneDetection("FAX_CNG", cng_score, 1100.0, "0.5s on / 3s off")
    ced_score = _sustained_score(mags[2100.0])
    if ced_score >= 0.45:
        return ToneDetection("FAX_CED", ced_score, 2100.0, "sustained")

    # ETSI / much of international ringback: 425 Hz, 1s on / 4s off.
    etsi_ring = _cadence_score(mags[425.0], expected_on_s=1.0, expected_off_s=4.0)
    if etsi_ring >= 0.35:
        return ToneDetection("RINGBACK", etsi_ring, 425.0, "1s on / 4s off")

    # North America style ringback is 440+480 Hz, 2s on / 4s off.
    na_ring_signal = np.minimum(mags[440.0], mags[480.0])
    na_ring = _cadence_score(na_ring_signal, expected_on_s=2.0, expected_off_s=4.0)
    if na_ring >= 0.35:
        return ToneDetection("RINGBACK", na_ring, 460.0, "2s on / 4s off")

    # Busy/reorder/congestion tones. These often appear as single 425 Hz
    # internationally or 480+620 Hz in North America.
    busy_425 = _cadence_score(mags[425.0], expected_on_s=0.5, expected_off_s=0.5)
    reorder_425 = _cadence_score(mags[425.0], expected_on_s=0.25, expected_off_s=0.25)
    na_busy_signal = np.minimum(mags[480.0], mags[620.0])
    busy_na = _cadence_score(na_busy_signal, expected_on_s=0.5, expected_off_s=0.5)
    reorder_na = _cadence_score(na_busy_signal, expected_on_s=0.25, expected_off_s=0.25)
    best_busy = max(busy_425, reorder_425, busy_na, reorder_na)
    if best_busy >= 0.35:
        cadence = "0.25s on/off" if max(reorder_425, reorder_na) >= max(busy_425, busy_na) else "0.5s on/off"
        freq = 425.0 if max(busy_425, reorder_425) >= max(busy_na, reorder_na) else 550.0
        return ToneDetection("BUSY_OR_REORDER", best_busy, freq, cadence)

    # Sustained pure tone after answer is weaker, but still useful
    # corroborating evidence for fake ringback/static call-progress media.
    sustained_candidates = [(freq, _sustained_score(mags[freq])) for freq in (425.0, 440.0, 480.0, 620.0)]
    freq, score = max(sustained_candidates, key=lambda item: item[1])
    if score >= 0.45:
        return ToneDetection("CALL_PROGRESS_TONE", score, freq, "sustained")

    return ToneDetection()


def _active_runs(signal: np.ndarray, threshold: float = 0.10) -> list[tuple[int, int, bool]]:
    if signal.size == 0:
        return []
    active = signal > threshold
    runs: list[tuple[int, int, bool]] = []
    start = 0
    state = bool(active[0])
    for i in range(1, active.size):
        if bool(active[i]) != state:
            runs.append((start, i, state))
            start = i
            state = bool(active[i])
    runs.append((start, active.size, state))
    return runs


def _cadence_score(signal: np.ndarray, *, expected_on_s: float, expected_off_s: float) -> float:
    runs = _active_runs(signal)
    if not runs:
        return 0.0
    frame_s = 0.1
    active_frac = float(np.mean(signal > 0.10))
    if active_frac <= 0.02:
        return 0.0
    on_scores: list[float] = []
    off_scores: list[float] = []
    for start, end, is_on in runs:
        duration = (end - start) * frame_s
        expected = expected_on_s if is_on else expected_off_s
        if expected <= 0:
            continue
        score = max(0.0, 1.0 - abs(duration - expected) / max(expected, 0.25))
        if is_on:
            on_scores.append(score)
        else:
            off_scores.append(score)
    on_fit = max(on_scores) if on_scores else 0.0
    off_fit = max(off_scores) if off_scores else 0.0
    # goertzel_magnitude on clean int16 telephony tones normalises near 0.20,
    # not 1.0. Treat 0.18+ as a full-strength tone for cadence scoring.
    purity = float(np.clip(signal.max() / 0.18, 0.0, 1.0))
    # Short clips may contain only the "on" part. Let them contribute,
    # but require off cadence for the highest scores.
    cadence_fit = (on_fit * 0.65) + (off_fit * 0.35)
    return float(min(1.0, purity * active_frac * 2.0 * cadence_fit))


def _sustained_score(signal: np.ndarray) -> float:
    if signal.size == 0:
        return 0.0
    active_frac = float(np.mean(signal > 0.10))
    if active_frac < 0.45:
        return 0.0
    purity = float(np.clip(signal.max() / 0.18, 0.0, 1.0))
    return float(min(1.0, purity * active_frac))


def _sit_score(freq_950: np.ndarray, freq_1400: np.ndarray, freq_1800: np.ndarray) -> float:
    threshold = 0.10
    try:
        i950 = int(np.argmax(freq_950 > threshold))
        i1400 = int(np.argmax(freq_1400 > threshold))
        i1800 = int(np.argmax(freq_1800 > threshold))
    except ValueError:
        return 0.0
    if not (freq_950[i950] > threshold and freq_1400[i1400] > threshold and freq_1800[i1800] > threshold):
        return 0.0
    if not (i950 <= i1400 <= i1800):
        return 0.0
    strength = min(float(freq_950.max()), float(freq_1400.max()), float(freq_1800.max()))
    strength = float(np.clip(strength / 0.18, 0.0, 1.0))
    coverage = (
        float(np.mean(freq_950 > threshold))
        + float(np.mean(freq_1400 > threshold))
        + float(np.mean(freq_1800 > threshold))
    )
    return float(min(1.0, strength * coverage))
