"""Log-mel spectrogram, pure numpy.

Avoids librosa (~80 MB bundle, drags scipy + numba) by hand-rolling the
~6 operations needed for AASIST / PANNs feature input:
    1. Pre-emphasis (optional, off by default for AASIST)
    2. Framing with Hann window
    3. Magnitude FFT
    4. Power spectrum
    5. Mel filterbank application
    6. Log compression (dB or natural log)

The mel filterbank is HTK-style triangular bins. For PANNs CNN14 we expose
n_mels=64 mode at 32 kHz; for AASIST we expose n_mels=80 mode at 16 kHz.
Both consumers call mel_spectrogram with appropriate kwargs.
"""
from __future__ import annotations

import numpy as np


def _hz_to_mel(hz: np.ndarray | float) -> np.ndarray | float:
    return 2595.0 * np.log10(1.0 + np.asarray(hz) / 700.0)


def _mel_to_hz(mel: np.ndarray | float) -> np.ndarray | float:
    return 700.0 * (10.0 ** (np.asarray(mel) / 2595.0) - 1.0)


def mel_filterbank(
    *,
    sample_rate: int,
    n_fft: int,
    n_mels: int,
    fmin: float = 0.0,
    fmax: float | None = None,
) -> np.ndarray:
    """Return an (n_mels, n_fft//2 + 1) HTK-style triangular filterbank."""
    if fmax is None:
        fmax = sample_rate / 2.0
    mel_min = _hz_to_mel(fmin)
    mel_max = _hz_to_mel(fmax)
    mel_pts = np.linspace(mel_min, mel_max, n_mels + 2)
    hz_pts = _mel_to_hz(mel_pts)
    bin_pts = np.floor((n_fft + 1) * hz_pts / sample_rate).astype(int)
    bin_pts = np.clip(bin_pts, 0, n_fft // 2)
    fb = np.zeros((n_mels, n_fft // 2 + 1), dtype=np.float32)
    for m in range(n_mels):
        lo, mid, hi = bin_pts[m], bin_pts[m + 1], bin_pts[m + 2]
        if mid > lo:
            fb[m, lo:mid] = (np.arange(lo, mid) - lo) / max(mid - lo, 1)
        if hi > mid:
            fb[m, mid:hi] = (hi - np.arange(mid, hi)) / max(hi - mid, 1)
    return fb


def mel_spectrogram(
    audio: np.ndarray,
    *,
    sample_rate: int = 16000,
    n_fft: int = 512,
    hop_length: int = 160,
    n_mels: int = 64,
    fmin: float = 0.0,
    fmax: float | None = None,
    log_offset: float = 1e-10,
    return_db: bool = True,
) -> np.ndarray:
    """Return log-mel spectrogram of shape (n_mels, n_frames), float32.

    audio: 1-D int16 or float array. Will be converted to float32 / 32768
           if int16 to put it in [-1, 1).
    """
    if audio.dtype == np.int16:
        x = audio.astype(np.float32) / 32768.0
    else:
        x = audio.astype(np.float32, copy=False)
    if x.size < n_fft:
        # Pad with zeros so framing produces at least one frame.
        x = np.pad(x, (0, n_fft - x.size))

    window = np.hanning(n_fft).astype(np.float32)
    n_frames = 1 + (x.size - n_fft) // hop_length
    if n_frames < 1:
        n_frames = 1
    # Frame the signal -- shape (n_frames, n_fft).
    frames = np.lib.stride_tricks.as_strided(
        x,
        shape=(n_frames, n_fft),
        strides=(x.strides[0] * hop_length, x.strides[0]),
        writeable=False,
    ).copy()
    frames *= window
    # rfft -> shape (n_frames, n_fft//2 + 1) complex
    spec = np.fft.rfft(frames, axis=1)
    power = (spec.real ** 2 + spec.imag ** 2).astype(np.float32)
    # Mel filterbank
    fb = mel_filterbank(
        sample_rate=sample_rate, n_fft=n_fft, n_mels=n_mels, fmin=fmin, fmax=fmax
    )
    mel = power @ fb.T  # (n_frames, n_mels)
    if return_db:
        out = 10.0 * np.log10(np.maximum(mel, log_offset))
    else:
        out = np.log(np.maximum(mel, log_offset))
    return out.T.astype(np.float32)  # (n_mels, n_frames)
