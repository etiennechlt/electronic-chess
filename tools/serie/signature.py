"""The signature sound: every resonator line heard as a ringdown note.

Each line of the frequency plan is divided by `serie.transpose_ratio`
(1000 in the bible, so 216.6 kHz is heard at 216.6 Hz) and played with
an instant attack and an exponential decay, the way the piece itself
rings after the board strikes it. Two quiet harmonics ride on the
fundamental so the low notes survive a phone speaker.
"""

from __future__ import annotations

import wave
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from chessboard_calc.config import BoardConfig
from chessboard_calc.resonance import frequency_plan


@dataclass(frozen=True)
class Note:
    piece: str
    color: str
    f0_hz: float
    audio_hz: float

    @property
    def slug(self) -> str:
        return f"{self.piece}-{self.color}"


def notes(cfg: BoardConfig) -> list[Note]:
    """The twelve notes, lowest first, in the order of the frequency plan."""
    ratio = cfg.serie.transpose_ratio
    return [
        Note(str(line.piece), str(line.color), line.f0_hz, line.f0_hz / ratio)
        for line in frequency_plan(cfg).lines
    ]


def ringdown(cfg: BoardConfig, audio_hz: float, length_s: float | None = None) -> np.ndarray:
    """One note: harmonics of `audio_hz` under a ringdown envelope, peak 1."""
    s = cfg.serie
    rate = s.sample_rate_hz
    t = np.arange(int(round((length_s or s.note_s) * rate))) / rate
    attack = np.clip(t / (s.attack_ms * 1e-3), 0.0, 1.0)
    tone = np.zeros_like(t)
    for k, gain in enumerate(s.harmonics, start=1):
        # upper harmonics die faster, as on a struck resonator
        tone += gain * np.sin(2 * np.pi * k * audio_hz * t) * np.exp(-t * k / s.decay_s)
    out = attack * tone
    return out / np.max(np.abs(out))


def scale(cfg: BoardConfig, gain: float = 0.8) -> np.ndarray:
    """The twelve notes rising, one every `serie.scale_step_s`."""
    s = cfg.serie
    step = int(round(s.scale_step_s * s.sample_rate_hz))
    voices = [ringdown(cfg, note.audio_hz) for note in notes(cfg)]
    out = np.zeros(step * (len(voices) - 1) + len(voices[-1]))
    for i, voice in enumerate(voices):
        out[i * step : i * step + len(voice)] += voice
    return gain * out / np.max(np.abs(out))


def thud(cfg: BoardConfig, length_s: float = 0.5) -> np.ndarray:
    """A layer set down on the board: a low thump and a short breath of noise,
    peak 1. The noise is seeded, so every build writes the same file."""
    s = cfg.serie
    rate = s.sample_rate_hz
    t = np.arange(int(round(length_s * rate))) / rate
    env = np.exp(-t / s.thud.decay_s)
    body = np.sin(2 * np.pi * s.thud.hz * t * (1.0 + 0.6 * np.exp(-t / 0.02)))
    noise = np.random.default_rng(0).standard_normal(len(t)) * np.exp(-t / (s.thud.decay_s / 4))
    out = np.clip(t / (s.attack_ms * 1e-3), 0.0, 1.0) * (env * body + s.thud.noise * noise)
    return out / np.max(np.abs(out))


def write_wav(path: Path, samples: np.ndarray, rate: int) -> None:
    """Mono 16-bit PCM, the format every editor and the film renderer read."""
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = (np.clip(samples, -1.0, 1.0) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as fh:
        fh.setnchannels(1)
        fh.setsampwidth(2)
        fh.setframerate(rate)
        fh.writeframes(pcm.tobytes())


def write_all(cfg: BoardConfig, out_dir: Path, gain: float = 0.8) -> list[Path]:
    """One file per note (`pawn-black.wav`...), the rising scale (`gamme.wav`)
    and the set-down thud of the build film (`pose.wav`)."""
    rate = cfg.serie.sample_rate_hz
    written = []
    for note in notes(cfg):
        path = out_dir / f"{note.slug}.wav"
        write_wav(path, gain * ringdown(cfg, note.audio_hz), rate)
        written.append(path)
    path = out_dir / "gamme.wav"
    write_wav(path, scale(cfg, gain), rate)
    written.append(path)
    path = out_dir / "pose.wav"
    write_wav(path, gain * thud(cfg), rate)
    written.append(path)
    return written
