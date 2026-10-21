"""Offline reference-spectrum attenuation.

This is NOT an AI source separator or physical ANC.
Designed as a lightweight, auditable baseline for controlled WAV experiments.
"""
from __future__ import annotations

from math import gcd
from pathlib import Path
from typing import Callable, Sequence

import numpy as np
import soundfile as sf
from scipy.signal import istft, resample_poly, stft

FFT_SIZE = 2048
HOP_SIZE = 512
MAX_SECONDS = 120.0
EPS = 1e-10


def read_audio(path: str | Path) -> tuple[np.ndarray, int]:
    """Return (frames, channels) float32 audio and sample rate."""
    audio, rate = sf.read(str(path), dtype="float32", always_2d=True)
    if audio.shape[0] == 0:
        raise ValueError("音声が空です。")
    return audio, int(rate)


def _stft(signal: np.ndarray, rate: int) -> np.ndarray:
    if signal.size < FFT_SIZE:
        signal = np.pad(signal, (0, FFT_SIZE - signal.size))
    _, _, data = stft(
        signal, fs=rate, nperseg=FFT_SIZE,
        noverlap=FFT_SIZE - HOP_SIZE,
        boundary="zeros", padded=True,
    )
    return data


def _profile(reference: np.ndarray, rate: int) -> np.ndarray:
    if reference.shape[0] < int(rate * 0.2):
        raise ValueError("登録音は0.2秒以上必要です。")
    mono = reference.mean(axis=1)
    spectrum = np.abs(_stft(mono, rate)).astype(np.float64)
    energy = np.linalg.norm(spectrum, axis=0)
    if energy.max(initial=0.0) < 1e-7:
        raise ValueError("登録音がほぼ無音です。")
    active = energy >= max(np.percentile(energy, 50), energy.max() * 0.15)
    shape = spectrum[:, active].mean(axis=1)
    # Suppress extremely weak bins to avoid a broad noisy mask.
    shape[shape < shape.max() * 0.025] = 0.0
    return shape


def _resample(reference: np.ndarray, old: int, new: int) -> np.ndarray:
    if old == new:
        return reference
    g = gcd(old, new)
    return resample_poly(reference, new // g, old // g, axis=0).astype(np.float32)


def suppress(
    audio: np.ndarray,
    rate: int,
    references: Sequence[tuple[np.ndarray, int]],
    strength: float = 0.8,
    threshold: float = 0.48,
    report: Callable[[str], None] | None = None,
) -> np.ndarray:
    """Gated spectral attenuation for one or more enrolled sounds.

    strength in [0, 1], threshold in [0.1, 0.95].
    Preserves channel count and frame count.
    """
    if audio.ndim != 2 or audio.shape[1] not in (1, 2):
        raise ValueError("モノラルまたはステレオ音声を指定してください。")
    if rate <= 0 or not (0.0 <= strength <= 1.0) or not (0.1 <= threshold <= 0.95):
        raise ValueError("音声形式またはパラメータが不正です。")
    if audio.shape[0] / rate > MAX_SECONDS:
        raise ValueError(f"現在の試作版では{int(MAX_SECONDS)}秒以内の音声を選んでください。")
    if not references:
        raise ValueError("登録音を1つ以上選んでください。")
    if strength == 0.0:
        return audio.copy()

    profiles = []
    for reference, ref_rate in references:
        if reference.ndim != 2:
            raise ValueError("登録音の形式が不正です。")
        profile = _profile(_resample(reference, ref_rate, rate), rate)
        profiles.append(profile)

    # Each enrolled sound has its own similarity detector and spectral mask.
    detectors = []
    masks = []
    for profile in profiles:
        detector = np.power(profile, 0.65)
        detector /= max(np.linalg.norm(detector), EPS)
        detectors.append(detector)
        masks.append(np.power(profile / max(float(profile.max()), EPS), 1.25))

    output = np.zeros_like(audio, dtype=np.float32)
    for channel in range(audio.shape[1]):
        if report:
            report(f"チャンネル {channel + 1}/{audio.shape[1]} を処理中")
        freq = _stft(audio[:, channel], rate)
        magnitude = np.abs(freq).astype(np.float64)
        scaled = np.power(magnitude, 0.65)
        norm = np.maximum(np.linalg.norm(scaled, axis=0), EPS)

        removal = np.zeros_like(magnitude, dtype=np.float32)
        for detector, mask in zip(detectors, masks):
            similarity = np.asarray((detector @ scaled) / norm)
            # A soft decision over a 0.15-wide similarity interval.
            activation = np.clip((similarity - threshold) / 0.15, 0.0, 1.0)
            removal = np.maximum(
                removal, (mask[:, None] * activation[None, :]).astype(np.float32)
            )
        gain = 1.0 - strength * removal
        _, reconstructed = istft(
            freq * gain,
            fs=rate,
            nperseg=FFT_SIZE,
            noverlap=FFT_SIZE - HOP_SIZE,
            input_onesided=True,
            boundary=True,
        )
        output[:, channel] = reconstructed[: audio.shape[0]]
    return np.clip(output, -1.0, 1.0)


def process_file(
    source: str | Path,
    target_files: Sequence[str | Path],
    destination: str | Path,
    strength: float = 0.8,
    threshold: float = 0.48,
    report: Callable[[str], None] | None = None,
) -> None:
    source = Path(source).resolve()
    destination = Path(destination).resolve()
    if source == destination:
        raise ValueError("元の音声を上書きしないよう、別の保存先を選んでください。")
    if not target_files:
        raise ValueError("登録音を選んでください。")
    audio, rate = read_audio(source)
    refs = [read_audio(p) for p in target_files]
    result = suppress(audio, rate, refs, strength, threshold, report)
    sf.write(str(destination), result, rate, subtype="PCM_16")
