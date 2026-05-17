"""In-app FAS pipeline demo.

Invoked via:  python -m noc_beam --fas-demo

Runs the SAME code path the live engine uses during a real call:
    extract_features -> Silero VAD -> PANNs CNN14 -> Chromaprint -> rules

against 7 synthetic audio scenarios that mimic the FAS patterns the
engine is designed to catch. Prints each verdict, confidence, and the
signals that fired -- so the operator can sanity-check the engine
without placing real calls.
"""
from __future__ import annotations

import numpy as np

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


def _score(name: str, clip: np.ndarray) -> tuple[str, float]:
    features = extract_features(clip, sample_rate=SR)
    silero_p = silero_vad().score(clip, SR)
    panns_out = panns_classifier().score(clip, SR)
    fp = fingerprint_clip(clip, SR)
    fp_sim = 0.0
    cid = hash(name) & 0xFFFF
    if fp:
        fp_sim, _ = fingerprint_memory().match(
            fp, call_id=cid, account_id="demo", supplier="",
        )
        fingerprint_memory().add(
            fp, call_id=cid, account_id="demo", supplier="",
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
    print(f"  VERDICT:  {v.verdict:<14}  confidence={v.confidence:.0%}  score={v.score:+d}")
    for r in v.reasons:
        print(f"    - {r}")
    print(f"  signals:")
    for k, val in summary.items():
        print(f"    {k:<22} = {val}")
    return v.verdict, v.confidence


def run_fas_demo() -> int:
    print("=" * 60)
    print("NOC_Beam FAS pipeline self-test")
    print("=" * 60)
    print(f"  silero_vad available:  {silero_vad().available}")
    print(f"  panns_cnn14 available: {panns_classifier().available}")

    scenarios = [
        ("REAL CALL   - speech-like waveform",        _speech_like(4.0)),
        ("FAS A       - pure silence after answer",   _silence(4.0)),
        ("FAS B       - sustained 440 Hz ringback",   _ringback()),
        ("FAS C       - music-like hold (call 1)",    _music_like(4.0)),
        ("FAS C'      - SAME music (call 2 — repeat)", _music_like(4.0)),
        ("FAS D       - looped recording (call 1)",   _recording_loop()),
        ("FAS D'      - SAME loop (call 2 — repeat)", _recording_loop()),
    ]
    results = [(name, *_score(name, clip)) for name, clip in scenarios]

    print()
    print("=" * 60)
    print(" Summary")
    print("=" * 60)
    print(f" {'Scenario':<46} {'Verdict':<14} {'Conf':>6}")
    print("-" * 70)
    for name, verdict, conf in results:
        print(f" {name:<46} {verdict:<14} {conf:>5.0%}")
    return 0
