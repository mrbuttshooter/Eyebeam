"""Live FAS pipeline demo with real ONNX models.

Generates synthetic audio for each FAS scenario, runs it through the actual
feature extraction + Silero VAD + PANNs CNN14 + Chromaprint + rules engine,
and prints the verdict the live engine would emit on a real call.

Run with pytest -s to surface the verdicts:
    pytest tests/test_fas_live_demo.py -s

Skipped automatically if the ONNX models are not present on disk -- this is
a demo / diagnostic, not a CI gate.
"""
from __future__ import annotations

import numpy as np
import pytest

from noc_beam.audio.fas_features import extract_features
from noc_beam.audio.fas_fingerprint import fingerprint_clip, fingerprint_memory
from noc_beam.audio.fas_models import panns_classifier, silero_vad
from noc_beam.audio.fas_rules import signals_summary, synthesise

SR = 16000


def _silence(s: float) -> np.ndarray:
    return np.zeros(int(SR * s), dtype=np.int16)


def _tone(freq: float, s: float, db: float = -10.0) -> np.ndarray:
    n = int(SR * s)
    t = np.arange(n) / SR
    a = 10.0 ** (db / 20.0)
    return (np.sin(2 * np.pi * freq * t) * a * 32767).astype(np.int16)


def _speech_like(s: float, segments: int = 8, seed: int = 0) -> np.ndarray:
    n = int(SR * s)
    rng = np.random.default_rng(seed)
    out = np.zeros(n, dtype=np.float32)
    seg_len = n // (segments * 2)
    pos = 0
    for _ in range(segments):
        out[pos:pos + seg_len] = rng.standard_normal(seg_len).astype(np.float32) * 0.25
        pos += seg_len * 2
        if pos >= n:
            break
    return (out * 32767).astype(np.int16)


def _music_like(s: float) -> np.ndarray:
    n = int(SR * s)
    t = np.arange(n) / SR
    chord = (
        0.18 * np.sin(2 * np.pi * 261.6 * t)
        + 0.18 * np.sin(2 * np.pi * 329.6 * t)
        + 0.18 * np.sin(2 * np.pi * 392.0 * t)
    )
    vibrato = 1.0 + 0.05 * np.sin(2 * np.pi * 5.0 * t)
    return (chord * vibrato * 32767).astype(np.int16)


def _ringback() -> np.ndarray:
    return _tone(440.0, 3.0, db=-12.0)


def _recording_loop() -> np.ndarray:
    clip = _speech_like(1.5, segments=4, seed=42)
    return np.concatenate([clip, clip, clip[:int(SR * 0.5)]])


def _score_and_print(name: str, clip: np.ndarray) -> dict:
    features = extract_features(clip, sample_rate=SR)
    silero_p = silero_vad().score(clip, SR)
    panns_out = panns_classifier().score(clip, SR)
    fp = fingerprint_clip(clip, SR)
    fp_sim = 0.0
    if fp:
        fp_sim, _ = fingerprint_memory().match(
            fp, call_id=hash(name) & 0xFFFF, account_id="demo", supplier="",
        )
        fingerprint_memory().add(
            fp, call_id=hash(name) & 0xFFFF, account_id="demo", supplier="",
        )
    v = synthesise(
        features=features,
        silero_speech_prob=silero_p,
        aasist_spoof_prob=None,
        panns=panns_out,
        fingerprint_sim=fp_sim,
        sensitivity="balanced",
    )
    summary = signals_summary(
        features=features, silero_speech_prob=silero_p,
        aasist_spoof_prob=None, panns=panns_out, fingerprint_sim=fp_sim,
    )
    print(f"\n=== {name} ===")
    print(f"  VERDICT:    {v.verdict:<14} confidence={v.confidence:.0%}  score={v.score:+d}")
    for r in v.reasons:
        print(f"    - {r}")
    print(f"  signals:")
    for k, val in summary.items():
        print(f"    {k:<22} = {val}")
    return {"verdict": v.verdict, "confidence": v.confidence}


def test_fas_live_demo_runs_every_scenario():
    """Run all FAS scenarios through the real pipeline. Print verdicts."""
    # Skip cleanly if models aren't bundled in this checkout.
    if not silero_vad().available:
        pytest.skip("silero_vad ONNX not present; run build/fetch_fas_models.py")

    print("\n\n--- FAS pipeline live demo ---")
    print(f"silero_vad available:  {silero_vad().available}")
    print(f"panns_cnn14 available: {panns_classifier().available}")

    results = {}
    results["real"] = _score_and_print("REAL CALL  - speech-like waveform",   _speech_like(4.0))
    results["silence"] = _score_and_print("FAS A      - pure silence",             _silence(4.0))
    results["ringback"] = _score_and_print("FAS B      - sustained 440 Hz tone",    _ringback())
    results["music_1"] = _score_and_print("FAS C      - musical hold (call 1)",    _music_like(4.0))
    results["music_2"] = _score_and_print("FAS C'     - same musical hold (call 2)", _music_like(4.0))
    results["loop_1"] = _score_and_print("FAS D      - recorded loop (call 1)",   _recording_loop())
    results["loop_2"] = _score_and_print("FAS D'     - same recorded loop (call 2)", _recording_loop())

    # Lightweight assertions: the verdicts the pipeline should agree with.
    # The repeats (call 2) MUST be SUSPICIOUS or LIKELY_FAS because the
    # fingerprint match alone scores +3.
    assert results["music_2"]["verdict"] in ("SUSPICIOUS", "LIKELY_FAS"), (
        f"Repeated music expected to trigger fingerprint reuse, got "
        f"{results['music_2']['verdict']}"
    )
    assert results["loop_2"]["verdict"] in ("SUSPICIOUS", "LIKELY_FAS"), (
        f"Repeated loop expected to trigger fingerprint reuse, got "
        f"{results['loop_2']['verdict']}"
    )
    # Silence + ringback should both flag at the SUSPICIOUS+ level.
    assert results["silence"]["verdict"] in ("SUSPICIOUS", "LIKELY_FAS")
    assert results["ringback"]["verdict"] in ("SUSPICIOUS", "LIKELY_FAS")
