from __future__ import annotations

import numpy as np

from noc_beam.audio.fas_tones import detect_call_progress_tone

SR = 16000


def _tone(freq_hz: float, seconds: float, amp_db: float = -10.0) -> np.ndarray:
    n = int(SR * seconds)
    t = np.arange(n) / SR
    amp = 10.0 ** (amp_db / 20.0)
    return (np.sin(2 * np.pi * freq_hz * t) * amp * 32767).astype(np.int16)


def _silence(seconds: float) -> np.ndarray:
    return np.zeros(int(SR * seconds), dtype=np.int16)


def test_detects_etsi_ringback_cadence():
    clip = np.concatenate([_tone(425.0, 1.0), _silence(3.0)])
    tone = detect_call_progress_tone(clip, SR)
    assert tone.label == "RINGBACK"
    assert tone.score >= 0.35
    assert "1s" in tone.cadence


def test_detects_sit_sequence():
    clip = np.concatenate([
        _tone(950.0, 0.35),
        _tone(1400.0, 0.35),
        _tone(1800.0, 0.35),
        _silence(0.5),
    ])
    tone = detect_call_progress_tone(clip, SR)
    assert tone.label == "SIT_NO_SERVICE"
    assert tone.score >= 0.40


def test_speech_like_noise_does_not_detect_tone():
    rng = np.random.default_rng(42)
    clip = (rng.standard_normal(int(SR * 2.0)) * 0.2 * 32767).astype(np.int16)
    tone = detect_call_progress_tone(clip, SR)
    assert tone.label == ""
