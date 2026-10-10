"""The films' signature sound and facts stay tied to config/board.yaml."""

from __future__ import annotations

import re
import wave
from pathlib import Path

import numpy as np
from serie.facts import NNBSP, facts, fr, piece_name, yaml_quote
from serie.signature import notes, ringdown, scale, thud, write_all

from chessboard_calc import plateau
from chessboard_calc.power import autonomy_h
from chessboard_calc.resonance import frequency_plan

ROOT = Path(__file__).resolve().parents[1]
FILMS = ROOT / "media"


def test_twelve_notes_follow_the_frequency_plan(cfg):
    plan = frequency_plan(cfg)
    found = notes(cfg)
    assert len(found) == len(plan.lines) == 12
    for note, line in zip(found, plan.lines, strict=True):
        assert note.audio_hz == line.f0_hz / cfg.serie.transpose_ratio
    assert [n.audio_hz for n in found] == sorted(n.audio_hz for n in found)
    # the bible: from about 217 to 613 Hz, all of it audible on a phone
    assert 150.0 < found[0].audio_hz and found[-1].audio_hz < 1000.0


def test_ringdown_decays_with_the_configured_time_constant(cfg):
    note = notes(cfg)[0]
    wave_ = ringdown(cfg, note.audio_hz)
    rate = cfg.serie.sample_rate_hz
    assert len(wave_) == round(cfg.serie.note_s * rate)
    assert np.max(np.abs(wave_)) == 1.0
    # one period of energy early, one period one decay constant later
    period = int(rate / note.audio_hz)
    early = np.max(np.abs(wave_[int(0.01 * rate) : int(0.01 * rate) + period]))
    t1 = int((0.01 + cfg.serie.decay_s) * rate)
    late = np.max(np.abs(wave_[t1 : t1 + period]))
    assert 0.30 < late / early < 0.42  # e^-1 on the fundamental, harmonics gone
    assert np.array_equal(wave_, ringdown(cfg, note.audio_hz))  # deterministic


def test_scale_lasts_eleven_steps_and_a_note(cfg):
    s = cfg.serie
    assert len(scale(cfg)) == round(11 * s.scale_step_s * s.sample_rate_hz) + round(
        s.note_s * s.sample_rate_hz
    )


def test_thud_is_a_short_low_deterministic_hit(cfg):
    hit = thud(cfg)
    rate = cfg.serie.sample_rate_hz
    assert len(hit) == round(0.5 * rate)
    assert np.max(np.abs(hit)) == 1.0
    # most of the energy within a few decay constants, nothing left at the end
    tail = int(5 * cfg.serie.thud.decay_s * rate)
    assert np.sum(hit[tail:] ** 2) < 0.01 * np.sum(hit**2)
    assert np.array_equal(hit, thud(cfg))  # seeded noise: same file every build


def test_signature_writes_a_file_per_note_the_scale_and_the_thud(cfg, tmp_path):
    written = write_all(cfg, tmp_path)
    assert len(written) == 14
    expected = {"pawn-black.wav", "king-white.wav", "gamme.wav", "pose.wav"}
    assert {p.name for p in written} >= expected
    with wave.open(str(tmp_path / "queen-white.wav")) as fh:
        assert fh.getframerate() == cfg.serie.sample_rate_hz
        assert fh.getnchannels() == 1


def test_facts_are_the_computed_values_in_french(cfg):
    f = facts(cfg)
    assert fr(1399) == f"1{NNBSP}399"
    assert fr(216.64, 1) == "216,6"
    assert f["autonomy_human_h"] == fr(autonomy_h(cfg, engine_on=False))
    assert f["line"]["queen-white"]["name"] == "dame blanche"
    assert f["line"]["pawn-black"]["label"].endswith(f"{NNBSP}kHz")
    assert piece_name("rook", "black") == "tour noire"
    assert f["lines_count"] == "12"


def test_scene_facts_match_the_board(cfg):
    f = facts(cfg)
    scene = f["scene"]
    assert set(scene["pieces"]) == {"pawn", "knight", "bishop", "rook", "queen", "king"}
    for kind, dims in scene["pieces"].items():
        assert dims["coil_id"] < dims["coil_od"] <= dims["base"]
        assert dims["magnet_d"] < dims["base"]
        assert dims["height"] == round(dims["base"] * cfg.serie.piece_height_ratio[kind], 2)
    assert len(scene["led_points"]) == int(f["leds"]) == len(plateau.led_points(cfg))
    side = scene["pitch"] * scene["grid"]
    assert all(0 < x < side and 0 < y < side for x, y in scene["led_points"])
    # the module sits higher on the carriage base by the difference of the two bases
    assert int(f["gantry_thickness_mm"]) - int(f["thickness_mm"]) == round(scene["gantry_lift"])


def test_yaml_quote_is_the_file_itself(cfg):
    quoted = yaml_quote()
    text = (ROOT / "config" / "board.yaml").read_text(encoding="utf-8")
    for line in quoted:
        assert line.strip() in text
    assert f"L_target_uH: {cfg.resonator.L_target_uH}" in "\n".join(quoted)


def test_films_never_type_a_computed_number(cfg):
    """A composition shows numbers through data-fact only: any label the
    facts compute, found typed in a film source, is a duplicate that will
    drift the day the yaml changes."""
    f = facts(cfg)
    labels = [ln["label"] for ln in f["lines"]] + [
        f"{f['autonomy_human_h']} h",
        f"{f['module_cm']} cm",
        f"{f['thickness_mm']} mm",
        f"{f['energy_wh']} Wh",
        f"{f['coil_uh']} µH",
        f"{f['band_low_khz']} à {f['band_high_khz']}",
        f"{f['base_height_mm']} mm",
        f"{f['gantry_thickness_mm']} mm",
        f"{f['pawn_coil_mm']} mm",
        f"{f['pawn_magnet_mm']} mm",
    ]
    variants = {re.sub(f"[{NNBSP}  ]", " ", label) for label in labels}
    skip = {"assets", "node_modules", "renders"}
    sources = [p for p in FILMS.rglob("*.html") if not skip & set(p.parts)]
    for path in sources:
        text = re.sub(f"[{NNBSP} ]|&nbsp;|&#8239;", " ", path.read_text(encoding="utf-8"))
        for label in variants:
            assert label not in text, f"{path.relative_to(ROOT)} types {label!r}"
