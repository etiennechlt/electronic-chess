"""The NFC identity layer of note 24: loop, tag, link budget, and the
multiplexer question of ADR 0001 answered by the model."""

from chessboard_calc.config import BoardConfig
from chessboard_calc.nfc import analog_mux_verdict, antenna, check, link, switch_verdict, tag


def test_yaml_holds(cfg):
    assert check(cfg) == []


def test_tag_resonates_above_the_carrier(cfg):
    t = tag(cfg)
    f_carrier = cfg.hall_rfid.nfc.f_hz * 1e-6
    assert f_carrier < t.f_self_mhz < 1.5 * f_carrier
    assert 1.0 < t.L_uH < 4.0


def test_loop_fits_the_square_and_tunes_with_a_sane_capacitor(cfg):
    for pitch in cfg.pitch.candidates_mm:
        a = antenna(cfg, pitch)
        assert 0.0 < a.d_in_mm < a.side_mm < pitch
        assert 100.0 < a.c_res_pF < 1000.0
        assert a.r_series_ohm < 3.0   # a few ohms at most: no analog switch can sit there


def test_field_at_the_tag_clears_the_iso_minimum_with_margin(cfg):
    for pitch in cfg.pitch.candidates_mm:
        near = link(cfg, pitch)
        far = link(cfg, pitch, cfg.gap.max_total_mm - cfg.gap.nominal_total_mm)
        assert 0.05 < far.k < near.k < 0.5
        assert far.h_margin > 2.0


def test_the_analog_mux_kills_the_loop(cfg):
    # ADR 0001 wrote it by hand; the model puts numbers on it: the
    # CD74HC4067 in the resonant loop leaves a Q below 1 and the off
    # channels detune the loop by a tenth of the carrier.
    v = analog_mux_verdict(cfg, cfg.pitch.plateau_mm)
    assert v.q_with_switch < 1.0
    assert v.detune_pct < -5.0
    assert not v.ok


def test_even_an_rf_switch_in_the_loop_halves_the_q(cfg):
    # the switch must sit in the matched section, never in the loop
    v = switch_verdict(cfg, cfg.pitch.plateau_mm, "spdt", 1.5, 0.5, 1.0, 2)
    assert v.q_with_switch < cfg.hall_rfid.nfc.antenna.q_target / 2.0
    assert abs(v.detune_pct) < 1.0
    ideal = switch_verdict(cfg, cfg.pitch.plateau_mm, "ideal", 0.0, 0.0, 0.0, 1)
    assert ideal.ok


def test_guards_fire(raw_config_dict):
    raw = raw_config_dict
    raw["hall_rfid"]["nfc"]["tag"]["turns"] = 20
    assert "tag self-resonance away from the carrier" in check(BoardConfig.model_validate(raw))
    raw["hall_rfid"]["nfc"]["tag"]["turns"] = 7
    raw["hall_rfid"]["nfc"]["antenna_current_ma_rms"] = 10.0
    problems = check(BoardConfig.model_validate(raw))
    assert any("below the ISO 14443 minimum" in p for p in problems)
