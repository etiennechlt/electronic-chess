"""The Hall presence layer of note 24: field of the piece ferrite at the
sensor, thresholds, crosstalk, what an amplitude reading can and cannot
separate, power and scan rate. Pinned from the yaml like the LC chain."""

import math

import pytest

from chessboard_calc.config import BoardConfig, PieceType
from chessboard_calc.hall import (
    adc_lsb_mv,
    amplitude_classes,
    check,
    disc_bz_axis_mT,
    disc_bz_mT,
    hall_budget,
    hall_power,
    hall_scan,
    piece_bz_mT,
    sensor_gap_mm,
)
from chessboard_calc.physics import MU0_H_PER_M


def test_stacked_loops_match_the_closed_form_on_axis():
    for z in (1.0, 5.0, 12.0, 40.0):
        assert disc_bz_mT(0.4, 6.25, 4.0, z) == pytest.approx(
            disc_bz_axis_mT(0.4, 6.25, 4.0, z), rel=1e-3
        )


def test_far_field_is_the_dipole_of_the_magnet():
    br, r_mm, t_mm, z_mm = 0.4, 6.25, 4.0, 150.0
    moment = br / MU0_H_PER_M * math.pi * (r_mm * 1e-3) ** 2 * t_mm * 1e-3
    centre_m = (z_mm + t_mm / 2.0) * 1e-3
    dipole_mT = MU0_H_PER_M / (4.0 * math.pi) * 2.0 * moment / centre_m**3 * 1e3
    assert disc_bz_mT(br, r_mm, t_mm, z_mm) == pytest.approx(dipole_mT, rel=0.02)


def test_field_falls_with_height_and_reverses_off_axis():
    heights = [3.0, 6.0, 9.0, 15.0]
    values = [disc_bz_mT(0.4, 8.75, 4.0, z) for z in heights]
    assert values == sorted(values, reverse=True)
    # beyond the rim the return flux points the other way, and fades
    assert disc_bz_mT(0.4, 8.75, 4.0, 6.9, rho_mm=50.0) < 0.0
    assert abs(disc_bz_mT(0.4, 8.75, 4.0, 6.9, rho_mm=70.0)) < abs(
        disc_bz_mT(0.4, 8.75, 4.0, 6.9, rho_mm=50.0)
    )
    with pytest.raises(ValueError):
        disc_bz_mT(0.4, 8.75, 4.0, 0.0)


def test_sensor_gap_follows_the_stack(cfg):
    lay = cfg.hall_rfid.layout
    expected = cfg.gap.air_gap_mm + cfg.resonator.coil.height_mm - lay.die_height_mm
    assert lay.magnet_above_coil
    assert sensor_gap_mm(cfg) == pytest.approx(expected)
    assert sensor_gap_mm(cfg, 3.0) == pytest.approx(expected + 3.0)


def test_yaml_holds_for_the_decided_pitch(cfg):
    assert check(cfg) == []
    for pitch in cfg.pitch.candidates_mm:
        assert check(cfg, pitch) == [], pitch


def test_every_piece_reads_present_at_the_maximum_gap(cfg):
    for pitch in cfg.pitch.candidates_mm:
        b = hall_budget(cfg, pitch)
        for piece in PieceType:
            f = b.fields[piece]
            assert f.b_max_gap_mT > b.threshold_mT, (pitch, piece)
            assert f.b_lifted_mT < b.release_mT, (pitch, piece)
            assert f.b_max_gap_mT < f.b_nominal_mT < f.b_pressed_mT
        assert b.lift_margin >= cfg.hall_rfid.presence.min_lift_margin
        assert b.crosstalk_db <= cfg.measurement.crosstalk_max_db
        assert b.in_linear_range


def test_pinned_fields_at_the_decided_pitch(cfg):
    # The pawn carries the smallest magnet (12.5 x 4 mm) 6.9 mm from the
    # plate: about 25 mT nominal, 21 mT at the maximum gap; the king's
    # 17.5 mm disc gives about 32 mT, and under 4 mT once raised 15 mm.
    b = hall_budget(cfg, cfg.pitch.plateau_mm)
    assert b.z_nominal_mm == pytest.approx(6.9)
    assert b.fields[PieceType.PAWN].b_nominal_mT == pytest.approx(25.3, abs=0.5)
    assert b.fields[PieceType.PAWN].b_max_gap_mT == pytest.approx(20.7, abs=0.5)
    assert b.fields[PieceType.KING].b_nominal_mT == pytest.approx(32.1, abs=0.5)
    assert b.fields[PieceType.KING].b_lifted_mT == pytest.approx(3.75, abs=0.2)
    assert b.lift_margin == pytest.approx(1.9, abs=0.1)
    assert b.crosstalk_db == pytest.approx(-24.7, abs=0.5)


def test_signal_is_far_above_the_adc_noise(cfg):
    b = hall_budget(cfg, cfg.pitch.plateau_mm)
    assert b.weakest_present_lsb > 100.0
    assert b.noise_margin > 20.0
    assert adc_lsb_mv(cfg) == pytest.approx(3100.0 / 4096.0)
    # the second candidate sensor (the SS49E die) holds the same margins
    b2 = hall_budget(cfg, cfg.pitch.plateau_mm, sensor_index=1)
    assert b2.lift_margin == pytest.approx(b.lift_margin)
    assert b2.noise_margin > 20.0


def test_uniform_magnets_give_presence_only(cfg):
    # ADR 0001: 'Hall alone, 2 to 4 classes at best'. With the uniform
    # 4 mm ferrites, the three magnet diameters overlap once the gap
    # scatters: one group, presence only.
    amp = amplitude_classes(cfg, cfg.pitch.plateau_mm)
    assert len(amp.classes) == 3
    assert amp.separable_groups == 1
    assert amp.in_linear_range


def test_thickness_coding_buys_three_groups_at_50_mm_only(cfg):
    coded = amplitude_classes(cfg, cfg.pitch.plateau_mm, size_coded=True)
    assert coded.separable_groups == 3
    assert coded.in_linear_range
    assert coded.strongest_mT == pytest.approx(62.5, abs=1.0)
    # at p = 40 the smaller discs do not separate even with the extras
    assert amplitude_classes(cfg, 40.0, size_coded=True).separable_groups < 3


def test_neighbor_field_is_the_same_piece_off_axis(cfg):
    p = cfg.pitch.plateau_mm
    b = hall_budget(cfg, p)
    direct = piece_bz_mT(cfg, PieceType.KING, p, b.z_nominal_mm, rho_mm=p)
    assert b.fields[PieceType.KING].b_neighbor_mT == pytest.approx(direct)
    assert direct < 0.0
    assert abs(direct) / b.fields[PieceType.KING].b_nominal_mT < 0.01


def test_continuous_supply_costs_autonomy_and_gating_recovers_most_of_it(cfg):
    cont = hall_power(cfg, gated=False)
    gated = hall_power(cfg, gated=True)
    assert cont.squares == 64
    assert cont.current_ma == pytest.approx(64 * cfg.hall_rfid.sensors[0].i_supply_ma)
    assert gated.current_ma == pytest.approx(cont.current_ma / cfg.hall_rfid.power_gating.groups)
    assert cont.autonomy_h < 0.7 * cont.autonomy_without_h
    assert gated.autonomy_h > 0.8 * gated.autonomy_without_h
    # the SS49E die draws more than twice the DRV5053: a continuous supply
    # would more than halve the human vs human autonomy
    ss = hall_power(cfg, gated=False, sensor_index=1)
    assert ss.autonomy_h < 0.5 * ss.autonomy_without_h


def test_scan_rate_leaves_the_lc_chain_far_behind(cfg):
    for gated in (False, True):
        sc = hall_scan(cfg, gated)
        assert sc.rate_hz > 100.0 * cfg.measurement.idle_scan_hz
        assert sc.board_ms < 5.0


def test_guards_fire(raw_config_dict):
    raw = raw_config_dict
    raw["gap"]["air_mm"] = 1.0
    cfg = BoardConfig.model_validate(raw)
    assert any("taller than the air clearance" in p for p in check(cfg))
    raw = dict(raw_config_dict)
    raw["hall_rfid"]["layout"]["lift_detect_mm"] = 5.0
    assert "a lifted king still reads as present" in check(BoardConfig.model_validate(raw))
    raw["hall_rfid"]["layout"]["lift_detect_mm"] = 15.0
    raw["hall_rfid"]["sensors"][0]["sensitivity_mv_per_mt"] = 90.0
    assert "a pressed king saturates the sensor" in check(BoardConfig.model_validate(raw))
    raw["hall_rfid"]["sensors"][0]["sensitivity_mv_per_mt"] = 11.0
    raw["hall_rfid"]["presence"]["hysteresis_fraction"] = 0.6
    with pytest.raises(ValueError):
        BoardConfig.model_validate(raw)
