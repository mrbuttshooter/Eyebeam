"""FAS inference worker thread.

A single QThread reads audio snapshots from FasAudioRouter, runs the
feature pipeline + ONNX models, synthesises a verdict via the rules
engine, and emits the result on sip_events().call_fas_verdict for Qt
to deliver on the main thread.

Schedule: per active call, score at t=3s, 8s, 13s, then every 10s.
Never downgrade past a deterministic positive signal (ringback /
fingerprint match).

Chunk 2 status: skeleton only. The actual feature extraction and ONNX
inference land in Chunk 3; here we wire the threading + Qt-signal path
and produce a placeholder "INCONCLUSIVE" verdict so downstream UI
(Chunk 5) can be developed against the same shape.
"""
from __future__ import annotations

import logging
import time

from PySide6.QtCore import QMutex, QMutexLocker, QThread, QWaitCondition

from noc_beam.audio.fas_router import fas_router
from noc_beam.sip.events import sip_events

log = logging.getLogger(__name__)

# Score-time schedule in seconds after a call enters CONFIRMED.
SCORE_TIMES_S = [3.0, 8.0, 13.0]
SCORE_INTERVAL_S = 10.0

# Verdict severity rank for monotonic locking. Higher = more severe.
# Once a verdict at rank N is committed, the badge never displays a
# rank < N for the rest of the call. Prevents the flicker (Suspicious
# -> Inconclusive -> Likely FAS) that erodes operator trust.
_SEVERITY = {
    "": 0,
    "ANALYZING": 0,
    "INCONCLUSIVE": 1,
    "LIKELY_REAL": 2,
    "SUSPICIOUS": 3,
    "LIKELY_FAS": 4,
}

# Per-verdict minimum confidence required to surface it on the live
# badge. Below this we keep showing the previously-committed verdict
# (or "Analyzing" if nothing committed yet). Gates can be liberal
# because the monotonic-severity lock already prevents downward
# flicker; the gate just filters out the lowest-noise readings.
# Calibrated against real echo-test traffic where SUSPICIOUS (silence)
# lands at ~0.30 and LIKELY_FAS (ringback+fingerprint) lands at 0.50+.
_MIN_CONFIDENCE_TO_SURFACE = {
    "INCONCLUSIVE": 0.0,
    "LIKELY_REAL": 0.30,
    "SUSPICIOUS": 0.25,
    "LIKELY_FAS": 0.40,
}


class _CallScoreState:
    __slots__ = ("started_at", "next_score_idx", "last_score_at", "last_verdict",
                 "last_confidence", "last_reasons", "deterministic_positive",
                 "committed_severity")

    def __init__(self) -> None:
        self.started_at = time.monotonic()
        self.next_score_idx = 0
        self.last_score_at = 0.0
        self.last_verdict = "INCONCLUSIVE"
        self.last_confidence = 0.0
        self.last_reasons = ""
        self.deterministic_positive = False  # ringback/fingerprint locked-in
        # Monotonic verdict surface (agents' consensus): once a verdict is
        # committed it never downgrades in severity. Stored as the severity
        # rank to make comparisons trivial.
        self.committed_severity = 0  # 0=none, 1=INCONCLUSIVE, 2=LIKELY_REAL, 3=SUSPICIOUS, 4=LIKELY_FAS

    def due(self, now: float) -> bool:
        elapsed = now - self.started_at
        if self.next_score_idx < len(SCORE_TIMES_S):
            return elapsed >= SCORE_TIMES_S[self.next_score_idx]
        return (now - self.last_score_at) >= SCORE_INTERVAL_S

    def mark_scored(self, now: float) -> None:
        if self.next_score_idx < len(SCORE_TIMES_S):
            self.next_score_idx += 1
        self.last_score_at = now


class FasInferenceWorker(QThread):
    """Single worker that scores every active call on a schedule.

    Owns its ONNX sessions (single-shot lazy load) and per-call state.
    """

    POLL_INTERVAL_MS = 250

    def __init__(self, parent=None) -> None:  # noqa: ANN001
        super().__init__(parent)
        self._stop = False
        self._states: dict[int, _CallScoreState] = {}
        self._cond_mutex = QMutex()
        self._cond = QWaitCondition()

    # ------------------------------------------------------------------
    # Qt main thread API
    # ------------------------------------------------------------------
    def track(self, call_id: int) -> None:
        """Start scoring a call. Called when the call enters CONFIRMED."""
        if call_id not in self._states:
            self._states[call_id] = _CallScoreState()
        # Wake worker so it picks up the new call immediately
        with QMutexLocker(self._cond_mutex):
            self._cond.wakeAll()

    def untrack(self, call_id: int) -> None:
        """Stop scoring a call. Called on DISCONNECTED."""
        self._states.pop(call_id, None)

    def request_stop(self) -> None:
        self._stop = True
        with QMutexLocker(self._cond_mutex):
            self._cond.wakeAll()

    # ------------------------------------------------------------------
    # Worker loop
    # ------------------------------------------------------------------
    def run(self) -> None:  # noqa: D401
        log.info("FasInferenceWorker started")
        try:
            while not self._stop:
                now = time.monotonic()
                # Snapshot the keys -- can't mutate dict mid-iteration.
                for call_id in list(self._states.keys()):
                    state = self._states.get(call_id)
                    if state is None:
                        continue
                    if not state.due(now):
                        continue
                    self._score_one(call_id, state)
                    state.mark_scored(now)

                # Sleep until next poll or wake
                with QMutexLocker(self._cond_mutex):
                    self._cond.wait(self._cond_mutex, self.POLL_INTERVAL_MS)
        finally:
            log.info("FasInferenceWorker stopped")

    # ------------------------------------------------------------------
    # Per-call scoring
    # ------------------------------------------------------------------
    def _sensitivity(self) -> str:
        # Read settings lazily; if anything fails fall back to balanced.
        try:
            from noc_beam.config.store import load_settings

            cfg = load_settings()
            return getattr(getattr(cfg, "fas", None), "sensitivity", "balanced") or "balanced"
        except Exception:
            return "balanced"

    def _score_one(self, call_id: int, state: _CallScoreState) -> None:
        from noc_beam.audio.fas_features import extract_features
        from noc_beam.audio.fas_fingerprint import fingerprint_clip, fingerprint_memory
        from noc_beam.audio.fas_models import aasist_detector, panns_classifier, silero_vad
        from noc_beam.audio.fas_rules import synthesise

        from noc_beam.audio.fas_tap import FAS_SAMPLE_RATE

        router = fas_router()
        clip = router.snapshot(call_id, seconds=4.0)
        total_samples = router.total_samples(call_id)
        active = router.active_calls()
        log.info(
            "FAS score tick call=%s total_samples=%d clip=%d active_calls=%s",
            call_id, total_samples, clip.size, active,
        )

        # Need at least 1 second of audio to attempt a verdict. The
        # AudioMediaRecorder writes WAV at the bridge's native rate
        # (16 kHz on this PJSIP build); FAS_SAMPLE_RATE mirrors that.
        min_samples = FAS_SAMPLE_RATE
        if clip.size == 0 or total_samples < min_samples:
            verdict_obj = None
            verdict, confidence, reasons = "ANALYZING", 0.0, "warming up"
        else:
            # Pass the router's native rate (matches the port's negotiated
            # codec rate). Feature extractors and model wrappers handle
            # resampling to their expected rates internally.
            features = extract_features(clip, sample_rate=FAS_SAMPLE_RATE)

            # ONNX models -- each returns None if unavailable; rules
            # engine tolerates None for every signal independently.
            silero_p = silero_vad().score(clip, sample_rate=FAS_SAMPLE_RATE)
            aasist_p = aasist_detector().score(clip, sample_rate=FAS_SAMPLE_RATE)
            panns_out = panns_classifier().score(clip, sample_rate=FAS_SAMPLE_RATE)

            # Fingerprint matching scoped by account_id when available.
            meta = router.meta(call_id)
            account_id = meta.get("account_id", "")
            supplier = meta.get("supplier", "")
            fp = fingerprint_clip(clip, sample_rate=FAS_SAMPLE_RATE)
            fp_sim = 0.0
            if fp:
                fp_sim, _entry = fingerprint_memory().match(
                    fp, call_id=call_id, account_id=account_id, supplier=supplier,
                )
                fingerprint_memory().add(
                    fp, call_id=call_id, account_id=account_id, supplier=supplier,
                )

            verdict_obj = synthesise(
                features=features,
                silero_speech_prob=silero_p,
                aasist_spoof_prob=aasist_p,
                panns=panns_out,
                fingerprint_sim=fp_sim,
                sensitivity=self._sensitivity(),
            )
            verdict = verdict_obj.verdict
            confidence = verdict_obj.confidence
            reasons = verdict_obj.reasons_text()

            # Lock in deterministic positives so the next score interval
            # doesn't downgrade past a fingerprint / ringback trigger.
            if "matches a previous call" in reasons or "ringback tone" in reasons:
                state.deterministic_positive = True

        # ----- Confidence gate ---------------------------------------
        # If the raw verdict doesn't clear its confidence floor, fall
        # back to whatever we last committed. New calls with no prior
        # commit show "ANALYZING" until something clears.
        min_conf = _MIN_CONFIDENCE_TO_SURFACE.get(verdict, 0.0)
        if confidence < min_conf and state.committed_severity == 0:
            verdict, confidence, reasons = "ANALYZING", 0.0, "gathering evidence"
        elif confidence < min_conf:
            # Stay with previously committed verdict, don't expose
            # the low-confidence reading.
            verdict = state.last_verdict
            confidence = state.last_confidence
            reasons = state.last_reasons

        # ----- Monotonic severity lock -------------------------------
        # Once a verdict at severity N is committed, never display
        # anything below N for the rest of the call. Prevents the
        # flicker pattern that erodes operator trust.
        new_sev = _SEVERITY.get(verdict, 0)
        if new_sev < state.committed_severity:
            verdict = state.last_verdict
            confidence = max(confidence, state.last_confidence)
            reasons = state.last_reasons
        else:
            state.committed_severity = max(state.committed_severity, new_sev)

        if state.deterministic_positive and _SEVERITY.get(verdict, 0) < _SEVERITY["SUSPICIOUS"]:
            # Belt-and-suspenders: deterministic-positive signals
            # (ringback, fingerprint reuse) lock in at SUSPICIOUS minimum.
            verdict = state.last_verdict
            confidence = state.last_confidence
            reasons = state.last_reasons

        state.last_verdict = verdict
        state.last_confidence = confidence
        state.last_reasons = reasons

        log.info(
            "FAS verdict call=%s final=%s conf=%.2f committed_sev=%d reasons=%s",
            call_id, verdict, confidence, state.committed_severity, reasons,
        )

        try:
            sip_events().call_fas_verdict.emit(call_id, verdict, confidence, reasons)
        except Exception:
            log.exception("Failed to emit call_fas_verdict for call %s", call_id)


_worker: FasInferenceWorker | None = None


def fas_worker() -> FasInferenceWorker:
    global _worker
    if _worker is None:
        _worker = FasInferenceWorker()
    return _worker


def shutdown_fas_worker() -> None:
    """Stop and join the worker, if one was started."""
    global _worker
    if _worker is None:
        return
    _worker.request_stop()
    if not _worker.wait(3000):
        log.warning("FasInferenceWorker did not stop within 3s; terminating")
        _worker.terminate()
        _worker.wait(1000)
    _worker = None
