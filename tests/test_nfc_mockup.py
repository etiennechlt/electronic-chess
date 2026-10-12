"""The NFC chain of the Hall + RFID mockup (note 25), recomputed from the
yaml: loops against the filament model, the MFRC522 matching network,
the tags in their bases, activation, neighbours and metal under the board.
Key numbers are pinned with tolerances; the guards are shown to fire."""

import math

import numpy as np
import pytest

from chessboard_calc import filament as fl
from chessboard_calc.config import BoardConfig, base_diameter_mm
from chessboard_calc.coupling import mutual_coaxial_loops_nH
from chessboard_calc.nfc import (
    antenna,
    ferrite_dl_h,
    field_pickup,
    hall_trace_pickup,
    loop_esr_ohm,
    loop_geometry,
    loop_merit,
    loop_model,
    main_and_trims,
    matching,
    metal_detune,
    mockup_check,
    mux_emulation,
    neighbor_relay,
    reference_chip_voltage_v,
    tag_activation,
    tag_geometry,
    tag_magnet_detune,
    tag_piece_coil,
    tag_trim_pF,
    tag_tuning,
    tx_supply_spread,
)
from chessboard_calc.physics import MU0_H_PER_M, RHO_CU_OHM_M


def _loops(cfg):
    return sorted(set(cfg.hall_rfid.mockup.loop_by_column.values()))


def _max_extra_gap(cfg):
    return cfg.gap.max_total_mm - cfg.gap.nominal_total_mm


def test_mockup_yaml_holds(cfg):
    assert mockup_check(cfg) == []


# ------------------------------------------------------------- filament model
def test_filament_field_and_mutuals_match_closed_forms():
    side, z = 30.0, 5.5     # one square filament of centreline side 30 mm
    loop = fl.square_loop(side + 1.0, 1, 1.0, 0.5, nsub=1)
    a, h = side * 1e-3, z * 1e-3
    den = 2.0 * math.pi * (h * h + a * a / 4.0) * math.sqrt(h * h + a * a / 2.0)
    on_axis = MU0_H_PER_M * a * a / den
    assert fl.bz_t_per_a(loop, np.array([[0.0, 0.0, h]]))[0] == pytest.approx(on_axis, rel=1e-9)
    small = fl.flux_through_circles_h(loop, (0.0, 0.0), z, np.array([0.5]))[0]
    assert small == pytest.approx(on_axis * math.pi * 0.5e-3**2, rel=1e-3)
    m = fl.coaxial_mutual_h(np.array(10e-3), np.array(6e-3), np.array(5.5e-3)) * 1e9
    assert m == pytest.approx(mutual_coaxial_loops_nH(10.0, 6.0, 5.5), rel=1e-12)
    other = fl.square_loop(35.0, 2, 1.0, 0.5, nsub=3, centre_mm=(50.0, 0.0))
    assert fl.mutual_h(loop, other) == pytest.approx(fl.mutual_h(other, loop), rel=1e-12)


def test_peec_falls_back_to_dc_and_shows_the_skin_effect():
    dc = RHO_CU_OHM_M / (1e-3 * 35e-6)
    low = fl.strip_resistance_per_m((10.0,), (0.0,), 1.0, 0.035, 1.0)[0]
    assert low == pytest.approx(dc, rel=1e-6)
    ac = fl.strip_resistance_per_m((10.0,), (0.0,), 1.0, 0.035, 13.56e6)[0]
    assert 1.5 < ac / dc < 2.5


def test_mohan_agrees_with_the_filament_model(cfg):
    # note 25, paragraph 2, point 10: the corrected d_in, pinned at 2 %
    loops = [cfg.hall_rfid.nfc.antenna, *cfg.hall_rfid.mockup.loops.values()]
    for pitch in cfg.pitch.candidates_mm:
        for lp in loops:
            m = loop_model(cfg, pitch, lp)
            assert m.L_uH == pytest.approx(m.L_filament_uH, rel=0.02)
        geo = loop_geometry(cfg.hall_rfid.nfc.antenna, pitch)
        ant = antenna(cfg, pitch)
        assert (ant.d_in_mm, ant.L_uH) == (geo.d_in_mm, geo.L_uH)


def test_loop_inductances_at_p50(cfg):
    l60, l70 = loop_model(cfg, 50.0, "L60x3"), loop_model(cfg, 50.0, "L70x2")
    assert l60.geometry.d_in_mm == pytest.approx(22.0)
    assert l70.geometry.d_in_mm == pytest.approx(30.0)
    assert l60.L_uH == pytest.approx(0.491, abs=0.003)
    assert l70.L_uH == pytest.approx(0.343, abs=0.003)
    assert l60.L_filament_uH == pytest.approx(0.485, abs=0.003)
    assert l70.L_filament_uH == pytest.approx(0.339, abs=0.003)


def test_loop_resistance_shows_skin_and_proximity(cfg):
    for pitch in cfg.pitch.candidates_mm:
        for name in _loops(cfg):
            m = loop_model(cfg, pitch, name)
            assert m.r_ac_ohm == loop_esr_ohm(cfg, pitch, name)
            assert 1.6 < m.r_ac_ohm / m.r_dc_ohm < 2.4
            assert 90.0 < m.q0 < 160.0
            assert 0.0 < m.c_self_pF < 3.0
    assert loop_esr_ohm(cfg, 50.0, "L60x3") == pytest.approx(0.30, abs=0.02)
    assert loop_esr_ohm(cfg, 50.0, "L70x2") == pytest.approx(0.25, abs=0.02)


# ----------------------------------------------------------- matching network
def test_preferred_main_and_trims():
    assert main_and_trims(62.06, "E12") == [(56.0, 0.0), (56.0, 5.6), (56.0, 6.8)]
    assert main_and_trims(470.0, "E12") == [(470.0, 0.0)]


def test_exact_network_hits_the_target_and_normalized_one_stays_tuned(cfg):
    m = cfg.hall_rfid.mockup.matching
    for pitch in cfg.pitch.candidates_mm:
        for name in _loops(cfg):
            mt = matching(cfg, pitch, name)
            assert abs(mt.z_exact_ohm - m.z_target_ohm) < 0.01 * m.z_target_ohm
            assert abs(mt.detune_pct) < mt.half_band_pct
            assert abs(mt.z_ohm - m.z_target_ohm) < 0.2 * m.z_target_ohm   # E12 trims
            assert mt.q_loaded == pytest.approx(m.q_loaded, rel=0.05)
            assert mt.c1_built_pF == pytest.approx(mt.c1_exact_pF, rel=0.03)
            assert mt.c2_built_pF == pytest.approx(mt.c2_exact_pF, rel=0.03)


def test_tx_supply_stays_under_the_reader_limit_at_the_tolerance_corners(cfg):
    rd = cfg.hall_rfid.mockup.reader
    for pitch in cfg.pitch.candidates_mm:
        for name in _loops(cfg):
            mt = matching(cfg, pitch, name)
            assert mt.i_tvdd_ma < mt.i_tvdd_worst_ma < rd.i_tvdd_max_ma
            assert mt.i_tvdd_ma < rd.i_tvdd_accept_ma


def test_receive_divider_lands_in_its_window(cfg):
    rd = cfg.hall_rfid.mockup.reader
    lo, hi = rd.rx_target_vpp
    for pitch in cfg.pitch.candidates_mm:
        for name in _loops(cfg):
            mt = matching(cfg, pitch, name)
            assert lo <= mt.v_rx_vpp <= hi
            assert mt.v_rx_max_vpp < rd.rx_max_vpp
            assert mt.v_c0_vpp > rd.rx_max_vpp    # the divider is needed


def test_matching_values_at_p50(cfg):
    # note 25, paragraph 4.4 (L from the corrected Mohan formula)
    l60, l70 = matching(cfg, 50.0, "L60x3"), matching(cfg, 50.0, "L70x2")
    assert (l60.rq_ohm, l70.rq_ohm) == (0.68, 0.47)
    assert (l60.c1_pF[0], l60.c2_pF[0]) == (56.0, 470.0)
    assert (l70.c1_pF[0], l70.c2_pF[0]) == (82.0, 680.0)
    assert l60.c1_exact_pF == pytest.approx(62.0, abs=1.0)
    assert l60.c2_exact_pF == pytest.approx(502.0, abs=6.0)
    assert l70.c1_exact_pF == pytest.approx(85.0, abs=1.0)
    assert l70.c2_exact_pF == pytest.approx(742.0, abs=8.0)
    assert l60.i_loop_ma == pytest.approx(270.0, abs=20.0)
    assert l70.i_loop_ma == pytest.approx(315.0, abs=25.0)
    for mt in (l60, l70):
        assert mt.i_tx_ma == pytest.approx(52.0, abs=6.0)
        assert mt.f_emc_mhz == pytest.approx(14.34, abs=0.01)
        assert 7.0 < mt.v_c0_vpp < 8.5
        # the tag tuned high barely moves the TX current (note 25, point 8)
        assert mt.i_tx_no_tag_ma == pytest.approx(mt.i_tx_ma, rel=0.15)
        # full conductance overshoots the ISO maximum: the firmware throttles
        assert 2.0 < mt.h_axis_a_per_m / cfg.hall_rfid.nfc.h_max_a_per_m < 4.0


def test_p40_l60x3_takes_the_l70x2_values_of_p50(cfg):
    a, b = matching(cfg, 40.0, "L60x3"), matching(cfg, 50.0, "L70x2")
    assert a.rq_ohm == b.rq_ohm
    assert (a.c1_pF[0], a.c2_pF[0]) == (b.c1_pF[0], b.c2_pF[0])


# --------------------------------------------------------------------- tags
def test_tags_fit_their_base_and_tune_into_the_window(cfg):
    tg = cfg.hall_rfid.mockup.tags
    lo, hi = tg.f_self_mhz
    for pitch in cfg.pitch.candidates_mm:
        for size, piece in tg.sizes.items():
            geo = tag_geometry(cfg, pitch, size)
            base = base_diameter_mm(cfg, piece, pitch)
            assert geo.disc_mm + 2.0 * (tg.wall_mm + tg.fit_mm) == pytest.approx(base)
            assert geo.d_in_mm >= tg.opening_min_ratio * geo.copper_d_mm
            assert geo.tuned and lo <= geo.f_self_mhz <= hi
            assert geo.track_mm in tg.track_options_mm
            assert 0.6 < geo.k_layers < 0.75
            tt = tag_tuning(cfg, pitch, size)
            assert tt.f_mhz[0] == pytest.approx(geo.f_self_mhz)
            assert list(tt.f_mhz) == sorted(tt.f_mhz, reverse=True)


def test_tag_values(cfg):
    # note 25, paragraph 5
    p50 = tag_tuning(cfg, 50.0, "P")
    g = p50.geometry
    assert (g.disc_mm, g.turns_per_layer, g.track_mm) == (pytest.approx(14.5), 5, 0.20)
    assert g.L_uH == pytest.approx(1.67, abs=0.03)
    assert g.d_in_mm == pytest.approx(9.9)
    assert p50.f_mhz == pytest.approx((17.3, 15.2, 14.5), abs=0.15)
    p40 = tag_geometry(cfg, 40.0, "P")
    assert (p40.disc_mm, p40.turns_per_layer, p40.track_mm) == (pytest.approx(11.0), 7, 0.15)
    assert p40.f_self_mhz == pytest.approx(16.5, abs=0.2)
    g50 = tag_geometry(cfg, 50.0, "G")
    assert (g50.disc_mm, g50.turns_per_layer, g50.track_mm) == (pytest.approx(19.5), 4, 0.20)
    assert g50.f_self_mhz == pytest.approx(16.1, abs=0.2)
    assert tag_geometry(cfg, 40.0, "G").disc_mm == pytest.approx(15.0)


# --------------------------------------------------------------- activation
def test_activation_margin_holds_at_the_maximum_gap(cfg):
    tg = cfg.hall_rfid.mockup.tags
    dz = _max_extra_gap(cfg)
    for pitch in cfg.pitch.candidates_mm:
        for name in _loops(cfg):
            for size in tg.sizes:
                near = tag_activation(cfg, pitch, name, size)
                far = tag_activation(cfg, pitch, name, size, dz)
                assert far.margin >= tg.activation_margin_min
                assert far.margin < near.margin and far.k < near.k
                assert far.margin_service == pytest.approx(far.margin * far.service_fraction)
                # Q5: at the service field, one trim of each size keeps the margin
                best = max(tag_activation(cfg, pitch, name, size, dz, trim).margin_service
                           for trim in tg.trims_pF[size])
                assert best >= tg.activation_margin_min
            # the service fraction holds the tuning tag's field at the ISO maximum
            tuned = tag_activation(cfg, pitch, name, cfg.hall_rfid.mockup.matching.tune_tag)
            h_service = tuned.h_axis_a_per_m * tuned.service_fraction
            assert h_service == pytest.approx(cfg.hall_rfid.nfc.h_max_a_per_m, rel=1e-6)
            assert (tag_activation(cfg, pitch, name, "G", dz).margin
                    > tag_activation(cfg, pitch, name, "P", dz).margin)


def test_activation_values_at_p50(cfg):
    assert reference_chip_voltage_v(cfg) == pytest.approx(1.5, abs=0.1)
    dz = _max_extra_gap(cfg)
    p60 = tag_activation(cfg, 50.0, "L60x3", "P", dz)
    assert p60.margin == pytest.approx(4.1, abs=0.4)
    # at the service field (7.5 A/m on axis) the bare pawn tag stays under
    # the margin of 2 over the reference sticker: M13a decides (note 25, Q5)
    assert 1.0 < p60.margin_service < cfg.hall_rfid.mockup.tags.activation_margin_min
    # a trim towards the carrier buys voltage at the same conductance
    trimmed = tag_activation(cfg, 50.0, "L60x3", "P", dz, trim_pF=22.0)
    assert trimmed.margin_service > p60.margin_service
    assert tag_activation(cfg, 50.0, "L70x2", "P", dz).margin == pytest.approx(2.8, abs=0.3)


# --------------------------------------------------------------- neighbours
def test_held_neighbours_relay_less_than_floating_ones(cfg):
    for pitch in cfg.pitch.candidates_mm:
        for a in _loops(cfg):
            for b in _loops(cfg):
                held = neighbor_relay(cfg, pitch, a, b, "held")
                floating = neighbor_relay(cfg, pitch, a, b, "floating")
                assert held.idle_current_ratio < floating.idle_current_ratio
                assert held.k_loops < 0.0 and held.direct_pct < 5.0
                if a == b:
                    assert held.relayed_pct < floating.relayed_pct
    side = neighbor_relay(cfg, 50.0, "L70x2", "L70x2", "floating")
    diag = neighbor_relay(cfg, 50.0, "L70x2", "L70x2", "floating", diagonal=True)
    assert abs(diag.k_loops) < abs(side.k_loops)
    with pytest.raises(ValueError):
        neighbor_relay(cfg, 50.0, "L60x3", "L60x3", "off")


def test_relay_values_at_p50(cfg):
    # note 25, paragraph 4.4: 18 and 34 % floating, 5.7 and 13 % held
    def pct(a, b, state):
        return neighbor_relay(cfg, 50.0, a, b, state).relayed_pct

    assert pct("L60x3", "L60x3", "held") == pytest.approx(5.7, abs=1.5)
    assert pct("L70x2", "L70x2", "held") == pytest.approx(13.0, abs=2.5)
    assert pct("L60x3", "L60x3", "floating") == pytest.approx(19.0, abs=4.0)
    assert pct("L70x2", "L70x2", "floating") == pytest.approx(35.0, abs=5.0)
    assert pct("L70x2", "L60x3", "floating") < 45.0


# -------------------------------------------------------------------- metal
def test_metal_detune_falls_with_the_distance(cfg):
    heights = (0.0, *cfg.hall_rfid.mockup.criteria.disturber_distances_mm)
    for pitch in cfg.pitch.candidates_mm:
        for name in _loops(cfg):
            d = [metal_detune(cfg, pitch, name, h).detune_pct for h in heights]
            assert all(x > y > 0.0 for x, y in zip(d[:-1], d[1:], strict=True))
            assert not metal_detune(cfg, pitch, name, 0.0).ok
            assert metal_detune(cfg, pitch, name, cfg.hall_rfid.mockup.board.standoff_mm).ok
    on_table = metal_detune(cfg, 50.0, "L60x3", 0.0)
    assert on_table.l_drop_pct == pytest.approx(50.0, abs=5.0)
    assert metal_detune(cfg, 50.0, "L60x3", 10.0).detune_pct == pytest.approx(3.2, abs=0.5)
    assert metal_detune(cfg, 50.0, "L70x2", 30.0).detune_pct < 0.5


# ------------------------------------------- the preliminary values of note 25
def test_pawn_tag_gets_two_fifths_of_the_reference_emf(cfg):
    # paragraph 2, point 2: 38 to 41 % at equal loop current
    for name in _loops(cfg):
        act = tag_activation(cfg, 50.0, name, "P")
        assert 0.36 < act.emf_vs_reference < 0.43
        assert act.emf_vs_reference < tag_activation(cfg, 50.0, name, "G").emf_vs_reference < 1.0


def test_tag_tuning_trades_voltage_against_matching(cfg):
    # paragraph 2, point 8
    rd = cfg.hall_rfid.mockup.reader
    low = max(cfg.hall_rfid.mockup.tags.trims_pF["P"])
    for name in _loops(cfg):
        own = matching(cfg, 50.0, name)
        # tuned high, the bare tag barely moves the TX current: 46 to 53 mA
        assert 42.0 < own.i_tx_no_tag_ma < own.i_tx_ma < 58.0
        # tuned low, it asks for a larger C1 and its own network
        assert matching(cfg, 50.0, name, "P", low).c1_exact_pF > own.c1_exact_pF + 8.0
        blind = matching(cfg, 50.0, name, "P", low, tuned_with_tag=False)
        assert blind.i_tx_ma > own.i_tx_ma * 2.0
    blind60 = matching(cfg, 50.0, "L60x3", "P", low, tuned_with_tag=False)
    assert _i_tvdd_ma(blind60.i_tx_ma) > rd.i_tvdd_max_ma
    # with the tag at 14 MHz, the note's case: C1 of 124 pF, 155 to 215 mA
    trim14 = tag_trim_pF(cfg, 50.0, "P", 14.0)
    bare = tag_geometry(cfg, 50.0, "P").f_self_mhz
    assert tag_trim_pF(cfg, 50.0, "P", bare) == pytest.approx(0.0)
    assert matching(cfg, 50.0, "L60x3", "P", trim14).c1_exact_pF == pytest.approx(124.0, abs=8.0)
    for name in _loops(cfg):
        blind14 = matching(cfg, 50.0, name, "P", trim14, tuned_with_tag=False)
        assert 145.0 < blind14.i_tx_ma < 225.0


def _i_tvdd_ma(i_tx_ma):
    return 2.0 * math.sqrt(2.0) / math.pi * i_tx_ma


def test_ferrite_integral_matches_the_image_of_a_half_space():
    # a wide, thick slab is a half space: dL = eta sum M(r_i, r_j, d_i + d_j)
    radii, layers, gap, chi = (6.6, 6.2, 5.8), (0.0, 0.8), 1.2, 0.01
    dl = ferrite_dl_h(radii, layers, 200.0, max(layers) + gap, 200.0, chi)
    r = np.array([ri for _ in layers for ri in radii]) * 1e-3
    d = np.array([max(layers) + gap - z for z in layers for _ in radii]) * 1e-3
    image = chi / (2.0 + chi) * float(np.sum(fl.coaxial_mutual_h(r[:, None], r[None, :],
                                                                 d[:, None] + d[None, :])))
    assert dl == pytest.approx(image, rel=0.02)


def test_piece_magnet_and_lc_coil_against_the_tag(cfg):
    # paragraph 2, point 9: the magnet detunes under 1 %, the closed LC
    # coil (k of 0.6 to 0.65) takes a third to two fifths of the inductance
    for pitch in cfg.pitch.candidates_mm:
        for size in cfg.hall_rfid.mockup.tags.sizes:
            mag = tag_magnet_detune(cfg, pitch, size)
            assert -1.0 < mag.detune_pct < 0.0 < mag.l_rise_pct < 2.5
            coil = tag_piece_coil(cfg, pitch, size)
            assert 0.6 < coil.k < 0.7
            assert coil.l_loss_pct == pytest.approx(100.0 * coil.k**2, rel=0.03)
            assert coil.f_tag_mhz > cfg.hall_rfid.mockup.tags.f_self_mhz[1]
    assert tag_magnet_detune(cfg, 50.0, "P").gap_mm == pytest.approx(1.2)


def test_l60x3_gives_more_field_per_watt_and_less_coupling(cfg):
    # paragraph 4.2: 1.5 times the field per square root of watt, half the coupling
    for pitch in cfg.pitch.candidates_mm:
        a, b = loop_merit(cfg, pitch, "L60x3"), loop_merit(cfg, pitch, "L70x2")
        assert a.h_per_sqrt_w_loaded / b.h_per_sqrt_w_loaded == pytest.approx(1.5, abs=0.1)
        assert a.h_per_sqrt_w_loop > b.h_per_sqrt_w_loop
        assert a.k_side / b.k_side == pytest.approx(0.55, abs=0.08)
        assert abs(a.k_diagonal) < abs(a.k_side)


def test_hall_trio_picks_up_little_carrier(cfg):
    # paragraph 4.3: about 20 mV for a tight trio, 200 mV at 5 mm, -59 dB filter
    for name in _loops(cfg):
        tight = hall_trace_pickup(cfg, 50.0, name)
        wide = hall_trace_pickup(cfg, 50.0, name, 5.0)
        assert tight.spacing_mm == pytest.approx(2.0 * cfg.hall_rfid.mockup.hall.trio_pitch_mm)
        assert 15.0 < tight.emf_mv < 40.0
        assert 140.0 < wide.emf_mv < 230.0
        assert tight.filter_db == pytest.approx(-59.0, abs=1.0)
        assert tight.filtered_mv < 0.1


def test_tx_current_spreads_with_capacitors_and_loop_inductance(cfg):
    # paragraph 4.4: 92 and 110 mA at +-5 % on C1 and C2, 91 and 110 mA at
    # 5 % on the loop inductance, 160 and 190 mA at 10 %
    rd = cfg.hall_rfid.mockup.reader
    l_tol = cfg.hall_rfid.mockup.criteria.loop_l_tol_pct
    for name in _loops(cfg):
        caps = tx_supply_spread(cfg, 50.0, name, 5.0)
        assert 90.0 < caps.i_tx_max_ma < 120.0
        l5 = tx_supply_spread(cfg, 50.0, name, 0.0, l_tol)
        l10 = tx_supply_spread(cfg, 50.0, name, 0.0, 2.0 * l_tol)
        assert 90.0 < l5.i_tx_max_ma < 120.0
        assert 155.0 < l10.i_tx_max_ma < 195.0
        assert l10.i_tvdd_max_ma > rd.i_tvdd_max_ma > rd.i_tvdd_accept_ma > l10.i_tvdd_min_ma
        own = matching(cfg, 50.0, name)
        nominal = tx_supply_spread(cfg, 50.0, name, 0.0)
        assert nominal.i_tvdd_max_ma == pytest.approx(
            max(own.i_tvdd_ma, _i_tvdd_ma(own.i_tx_no_tag_ma))
        )


def test_mux_emulation_collapses_the_field(cfg):
    # paragraph 4.4 and Q8: 0.6 to 0.9 A/m at full conductance, 160 to
    # 215 mA of TX current, the same with the loop cut
    nfc_cfg = cfg.hall_rfid.nfc
    emu = mux_emulation(cfg, 50.0, "L70x2")
    assert emu.q_loop == pytest.approx(0.27, abs=0.04)
    assert 0.5 < emu.h_axis_a_per_m < 1.0 < nfc_cfg.h_min_a_per_m
    assert 150.0 < emu.i_tx_ma < 220.0
    assert emu.i_tx_cut_loop_ma == pytest.approx(emu.i_tx_ma, rel=0.05)
    assert emu.h_at_tvdd_limit_a_per_m < emu.h_axis_a_per_m


def test_field_tag_beats_a_single_turn(cfg):
    # paragraph 5: one turn gives 18 to 45 mV peak between 1.5 and 3.75 A/m
    nfc_cfg = cfg.hall_rfid.nfc
    h_low = nfc_cfg.h_min_a_per_m
    h_high = nfc_cfg.h_max_a_per_m / cfg.hall_rfid.mockup.tags.activation_margin_min
    low, high = field_pickup(cfg, h_low), field_pickup(cfg, h_high)
    assert low.single_turn_mv_peak == pytest.approx(18.0, abs=1.5)
    assert high.single_turn_mv_peak == pytest.approx(45.0, abs=3.0)
    assert high.emf_mv_peak / low.emf_mv_peak == pytest.approx(h_high / h_low)
    assert low.emf_mv_peak > 3.0 * low.single_turn_mv_peak


# ------------------------------------------------------------------- guards
@pytest.mark.parametrize(
    ("path", "value", "message"),
    [
        (("tags", "f_self_mhz"), [30.0, 31.0], "self-resonance outside its window"),
        (("tags", "wall_mm"), 10.0, "does not fit its base"),
        (("tags", "activation_margin_min"), 50.0, "activation margin below the minimum"),
        (("matching", "q_loaded"), 500.0, "below the loaded Q target"),
        (("matching", "z_target_ohm"), 0.5, "no C1, C2 network reaches the target"),
    ],
)
def test_guards_fire(raw_config_dict, path, value, message):
    raw = raw_config_dict
    raw["hall_rfid"]["mockup"][path[0]][path[1]] = value
    problems = mockup_check(BoardConfig.model_validate(raw))
    assert any(message in p for p in problems), problems


def test_rx_guard_fires(raw_config_dict):
    # a window above what the C0 node carries: no R1 reaches it
    reader = raw_config_dict["hall_rfid"]["mockup"]["reader"]
    reader["rx_max_vpp"] = 30.0
    reader["rx_target_vpp"] = [15.0, 20.0]
    problems = mockup_check(BoardConfig.model_validate(raw_config_dict))
    assert any("RX amplitude outside its target" in p for p in problems)


def test_tx_supply_guard_fires(raw_config_dict):
    reader = raw_config_dict["hall_rfid"]["mockup"]["reader"]
    reader["i_tvdd_max_ma"] = 55.0
    reader["i_tvdd_accept_ma"] = 40.0
    problems = mockup_check(BoardConfig.model_validate(raw_config_dict))
    assert any("TX supply over the reader limit" in p for p in problems)
