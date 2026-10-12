"""The Hall plus RFID test board of note 25: its 2 x 2 geometry, the
readers in the corridors between loops, the ground tree, the Hall chain
timing and the 3.3 V budget, at both pitches, pinned from the yaml; and
the guards that refuse a layout that does not hold."""

import copy
import math

import pytest
from shapely.geometry import LineString, box

from chessboard_calc.config import BoardConfig, PieceType
from chessboard_calc.hall import adc_lsb_mv, offset_coverage
from chessboard_calc.hallrfid_mockup import (
    check,
    cluster_coverage,
    cluster_offsets,
    ground_rings,
    hall_chain,
    largest_free_square_mm,
    layout,
    power,
)


def _mk(cfg):
    return cfg.hall_rfid.mockup


def test_yaml_holds_at_the_mockup_pitch(cfg):
    assert check(cfg) == []
    assert check(cfg, 50.0, _mk(cfg).ground_keepout_mm) == []


def test_p40_needs_the_reduced_keepout_for_its_readers(cfg):
    # note 25, 4.2: at p = 40 the central corridor leaves 6 mm outside two
    # 4 mm keepouts, too little for the 8 mm of a QFN-32 and its fan-out
    full = check(cfg, 40.0, _mk(cfg).ground_keepout_mm)
    assert [p for p in full if p.startswith("reader of")] == [
        "reader of B1 does not fit corridor A1|B1 outside the 4 mm ground keepout",
        "reader of B2 does not fit corridor A2|B2 outside the 4 mm ground keepout",
    ]
    # with the reduced keepout the readers and the Hall cluster hold (+-8.03 mm
    # against the +-8 mm of D14); what remains is the RFID verdict of the
    # model: at the service field no trim brings the L60x3 tags to the Q5
    # margin at p = 40 (nfc.mockup_check), the finding note 25 reports
    assert check(cfg, 40.0, _mk(cfg).ground_keepout_min_mm) == [
        "loop L60x3 at p = 40: tag P activation margin below the minimum at the service "
        "field, whatever its trim",
        "loop L60x3 at p = 40: tag G activation margin below the minimum at the service "
        "field, whatever its trim",
    ]


def test_squares_loops_and_board_outline(cfg):
    lay = layout(cfg, 50.0)
    centres = {sq.name: sq.centre_mm for sq in lay.squares}
    assert centres == {"A1": (25.0, 25.0), "B1": (75.0, 25.0), "A2": (25.0, 75.0),
                       "B2": (75.0, 75.0)}
    a1, b1 = lay.loop("A1"), lay.loop("B1")
    assert (a1.kind, a1.side_mm, a1.turns, a1.opening_mm) == ("L60x3", pytest.approx(30.0), 3,
                                                              pytest.approx(22.0))
    assert (b1.kind, b1.side_mm, b1.turns, b1.opening_mm) == ("L70x2", pytest.approx(35.0), 2,
                                                              pytest.approx(30.0))
    assert lay.loop("A2").kind == "L60x3" and lay.loop("B2").kind == "L70x2"
    # 100 x 145 mm useful, 110 x 145 with the rails on the long sides
    assert lay.useful == (0.0, 0.0, 100.0, 145.0)
    assert lay.board == (-5.0, 0.0, 105.0, 145.0)
    assert lay.strip == (0.0, 100.0, 100.0, 145.0)
    small = layout(cfg, 40.0)
    assert small.useful == (0.0, 0.0, 80.0, 125.0)
    assert small.loop("A1").opening_mm == pytest.approx(16.0)


def test_corridor_widths_at_both_pitches(cfg):
    lay = layout(cfg, 50.0, 4.0)
    central, a_rows, b_rows = (lay.corridor(n) for n in ("A1|B1", "A1|A2", "B1|B2"))
    assert lay.corridor("A2|B2").width_mm == pytest.approx(central.width_mm)
    assert (central.width_mm, central.free_width_mm) == (pytest.approx(17.5), pytest.approx(9.5))
    assert (a_rows.width_mm, a_rows.free_width_mm) == (pytest.approx(20.0), pytest.approx(12.0))
    assert (b_rows.width_mm, b_rows.free_width_mm) == (pytest.approx(15.0), pytest.approx(7.0))
    # play area outside keepouts, edge clearance and holes (note 25:
    # 2 515 mm2 prél., rasterised on an earlier diagonal layout)
    assert lay.free_area_mm2 == pytest.approx(2565.0, abs=5.0)
    assert sum(c.free_area_mm2 for c in lay.corridors) == pytest.approx(1839.0, abs=5.0)
    small = layout(cfg, 40.0, 4.0)
    assert small.corridor("A1|B1").free_width_mm == pytest.approx(6.0)
    assert small.corridor("A1|A2").free_width_mm == pytest.approx(8.0)
    assert small.corridor("B1|B2").free_width_mm == pytest.approx(4.0)
    reduced = layout(cfg, 40.0, _mk(cfg).ground_keepout_min_mm)
    assert reduced.corridor("A1|B1").free_width_mm == pytest.approx(10.0)


def test_corridors_scale_with_the_pitch(cfg):
    mk = _mk(cfg)
    s_a = mk.loops[mk.loop_by_column["A"]].side_ratio
    s_b = mk.loops[mk.loop_by_column["B"]].side_ratio
    for pitch in cfg.pitch.candidates_mm:
        lay = layout(cfg, pitch, 0.0)
        assert lay.corridor("A1|B1").width_mm == pytest.approx(pitch * (1 - (s_a + s_b) / 2))
        assert lay.corridor("A1|A2").width_mm == pytest.approx(pitch * (1 - s_a))
        assert lay.corridor("B1|B2").width_mm == pytest.approx(pitch * (1 - s_b))


def test_readers_sit_in_corridors_facing_their_own_loop(cfg):
    lay = layout(cfg, 50.0)
    placed = {r.square: (r.corridor, r.faces, r.part.maker) for r in lay.readers}
    assert placed == {
        "A1": ("A1|A2", "N", "NXP"),
        "A2": ("A1|A2", "S", "JSMSEMI"),
        "B1": ("A1|B1", "W", "NXP"),
        "B2": ("A2|B2", "W", "JSMSEMI"),
    }
    for r in lay.readers:
        assert r.fits
        assert lay.loop(r.square).feed_side == r.faces
    footprints = [box(*r.footprint) for r in lay.readers]
    for i, a in enumerate(footprints):
        for b in footprints[i + 1:]:
            assert not a.intersects(b)


def test_holes_sit_at_half_the_smallest_loop_margin(cfg):
    lay = layout(cfg, 50.0)
    assert lay.hole_inset_mm == pytest.approx(3.75)
    assert {h.centre_mm for h in lay.holes} == {(3.75, 3.75), (96.25, 3.75), (3.75, 96.25),
                                                (96.25, 96.25)}
    assert min(h.loop_clearance_mm for h in lay.holes) == pytest.approx(3.70, abs=0.01)
    small = layout(cfg, 40.0)
    assert small.hole_inset_mm == pytest.approx(3.0)
    assert min(h.loop_clearance_mm for h in small.holes) == pytest.approx(2.64, abs=0.01)
    for h in (*lay.holes, *small.holes):
        assert h.loop_clearance_mm > 0.0 and h.edge_clearance_mm > 0.0


def test_ground_is_a_cross_from_the_strip_and_never_a_ring(cfg):
    for pitch, keepout in ((50.0, 4.0), (40.0, 2.0)):
        lay = layout(cfg, pitch, keepout)
        assert ground_rings(lay) == []
        assert len(lay.ground) == 3
        trunk = next(s for s in lay.ground if s.corridor == "A|B")
        assert trunk.start[1] == lay.strip[1]        # leaves the strip
        edge = _mk(cfg).board.edge_clearance_mm
        for seg in lay.ground:
            line = LineString([seg.start, seg.end])
            for lp in lay.loops:
                assert line.distance(box(*lp.outline)) >= keepout - 1e-9
            # perpendicular to the outer edges, ending at the edge clearance
            for x, y in (seg.start, seg.end):
                assert x >= edge - 1e-9 and x <= lay.play_area[2] - edge + 1e-9
                assert y >= edge - 1e-9
        for r in lay.readers:
            assert any(LineString([s.start, s.end]).intersects(box(*r.footprint))
                       for s in lay.ground)


def test_fiducials_on_the_rails(cfg):
    lay = layout(cfg, 50.0)
    bd = _mk(cfg).board
    assert len(lay.fiducials) == bd.fiducials
    for f in lay.fiducials:
        assert f.on_rail
        x, y = f.centre_mm
        assert min(x - lay.board[0], lay.board[2] - x) == pytest.approx(bd.fiducial_edge_mm)
        assert min(y - lay.board[1], lay.board[3] - y) == pytest.approx(bd.fiducial_edge_mm)


def test_eight_hall_sensors_and_their_mux_channels(cfg):
    lay = layout(cfg, 50.0)
    centre = [s for s in lay.hall_sites if s.role == "centre"]
    cluster = [s for s in lay.hall_sites if s.role == "cluster"]
    assert [s.square for s in centre] == ["A1", "B1", "A2", "B2"]
    assert [s.mux_channel for s in centre] == [0, 1, 2, 3]
    assert [s.direct_signal for s in centre] == ["HALL_A1", "HALL_B1", "HALL_A2", "HALL_B2"]
    assert {s.square for s in cluster} == {"A1"}
    assert sorted(s.mux_channel for s in cluster) == [4, 5, 6, 7]
    # on the diagonals at +-0.10 p: +-5 mm at p = 50, +-4 at p = 40
    assert {s.offset_mm for s in cluster} == {(-5.0, -5.0), (5.0, -5.0), (-5.0, 5.0), (5.0, 5.0)}
    assert max(abs(x) for x, _ in cluster_offsets(cfg, 40.0)) == pytest.approx(4.0)


def test_cluster_coverage_against_the_admissible_offset(cfg):
    # at 0.10 p the diagonal cluster covers +-9.3 mm at p = 50 and +-8.0 at
    # p = 40, both over the +-8 mm of D14; on the axes it would cover +-6.4
    # (0.12 p, the first proposal of note 25, gave only +-8.8 and +-7.9)
    cov50 = cluster_coverage(cfg, 50.0)
    assert cov50.sensor.part == _mk(cfg).hall.sensor
    assert cov50.covered_mm == pytest.approx(9.32, abs=0.02)
    assert cov50.possible_mm == pytest.approx(16.25)
    assert cov50.ok
    d = _mk(cfg).hall.cluster_offset_ratio * 50.0
    axes = ((0.0, 0.0), (d, 0.0), (-d, 0.0), (0.0, d), (0.0, -d))
    assert offset_coverage(cfg, 50.0, "DRV5055A3", axes).covered_mm == pytest.approx(6.45,
                                                                                    abs=0.02)
    cov40 = cluster_coverage(cfg, 40.0)
    assert cov40.covered_mm == pytest.approx(8.03, abs=0.02)
    assert cov40.possible_mm == pytest.approx(13.0)
    assert cov40.ok


def test_hall_chain_filter_and_mux_settling(cfg):
    ch = hall_chain(cfg, 50.0)
    assert ch.sensor.part == "DRV5055A3"
    assert ch.corner_khz == pytest.approx(15.9, abs=0.1)
    assert ch.carrier_db == pytest.approx(-58.6, abs=0.1)       # note 25: -59 dB
    assert ch.share_fraction == pytest.approx(0.005, abs=1e-4)  # 0.5 % of the step
    assert ch.kick_quiescent_mv == pytest.approx(8.2, abs=0.1)  # 8 mV, 11 counts
    assert ch.kick_quiescent_lsb == pytest.approx(10.8, abs=0.1)
    assert ch.settle_quiescent_us == pytest.approx(30.9, abs=0.2)   # about 31 us
    assert ch.kick_worst_lsb == pytest.approx(14.3, abs=0.1)
    assert ch.settle_us == pytest.approx(33.7, abs=0.2)
    # the 2 us of mux.t_settle_us no longer holds with the filter
    assert ch.settle_us > 10.0 * cfg.hall_rfid.mux.t_settle_us
    esp = cfg.hall_rfid.esp32
    assert ch.channel_us == pytest.approx(ch.settle_us + esp.samples_per_square
                                          * esp.adc_sample_us)


def test_row_enable_to_a_valid_reading(cfg):
    ch = hall_chain(cfg, 50.0)
    assert ch.row_on_typ_us == pytest.approx(259.0, abs=1.0)   # note 25: about 260 us
    assert ch.row_on_max_us == pytest.approx(417.0, abs=1.0)   # note 25: 415 us at most
    assert ch.row_on_typ_us > ch.sensor.power_on_us
    assert ch.row_on_max_us > ch.sensor.power_on_max_us


def test_king_and_pawn_readings_with_the_mockup_sensor(cfg):
    ch50, ch40 = hall_chain(cfg, 50.0), hall_chain(cfg, 40.0)
    assert ch50.king_pressed_v == pytest.approx(2.17, abs=0.005)    # note 25: 2.17 V
    assert ch50.weakest_pawn_lsb == pytest.approx(409.5, abs=0.5)    # 409 counts
    assert ch40.king_pressed_v == pytest.approx(2.09, abs=0.005)
    assert ch40.weakest_pawn_lsb == pytest.approx(270.2, abs=0.5)
    for ch in (ch50, ch40):
        assert ch.in_linear_range
        assert ch.king_pressed_v < ch.sensor.out_range_v[1]
        assert ch.kick_worst_mv / adc_lsb_mv(cfg) == pytest.approx(ch.kick_worst_lsb)


def test_power_budget_and_regulator(cfg):
    pw = power(cfg)
    assert pw.loads_ma == {"esp32": 100.0, "reader_tx": 100.0, "readers_awake": 76.0,
                           "hall_sensors": 80.0}
    assert pw.total_ma == pytest.approx(356.0)          # note 25: under 0.36 A
    # the load drop plus the regulator's own ground current at its maximum
    assert pw.dissipation_nominal_w == pytest.approx(0.655, abs=0.002)
    assert pw.dissipation_w == pytest.approx(0.747, abs=0.002)           # at 5.25 V
    assert pw.t_junction_c == pytest.approx(107.2, abs=0.5)
    assert pw.dissipation_w < pw.p_max_w
    assert pw.headroom_v == pytest.approx(1.45)         # USB minimum minus 3.3 V
    assert pw.ok


def test_pin_map_follows_the_esp32_rules(cfg):
    esp = _mk(cfg).esp32
    pins = esp.pins
    assert len(set(pins.values())) == len(pins)
    assert all(pins[s] in esp.adc1_gpios for s in esp.analog_signals)
    assert not set(pins.values()) & set(esp.strapping_gpios)
    assert not set(pins.values()) & set(esp.psram_gpios)
    assert [pins[s] for s in esp.usb_signals] == list(esp.usb_gpios)
    assert set(pins.values()) <= set(esp.module_gpios)
    # the ESP32-S3 facts the rules rest on, pinned so a yaml slip shows
    assert list(esp.adc1_gpios) == list(range(1, 11))
    assert set(esp.strapping_gpios) == {0, 3, 45, 46}
    assert list(esp.usb_gpios) == [19, 20]
    assert set(esp.psram_gpios) == {35, 36, 37}
    assert set(esp.module_gpios) == set(range(0, 22)) | set(range(35, 49))


def _with(raw_config_dict, edit):
    raw = copy.deepcopy(raw_config_dict)
    edit(raw["hall_rfid"]["mockup"], raw)
    return BoardConfig.model_validate(raw)


def test_guards_fire(raw_config_dict):
    def problems(edit, *args):
        return check(_with(raw_config_dict, edit), *args)

    def three_columns(m, _):
        m["columns"] = ["A", "B", "C"]
        m["loop_by_column"]["C"] = "L60x3"

    # two trunks from the strip close a ring around the middle square
    assert "ground forms a ring around B2" in problems(three_columns)
    wide = problems(lambda m, _: m.update(ground_keepout_mm=8.0))
    assert "ground along B1|B2 enters the keepout of B1" in wide
    assert any(p.startswith("reader of A1 does not fit") for p in wide)
    assert problems(lambda m, _: m["reader"].update(footprint_square_mm=10.0)) == [
        "reader of B1 does not fit corridor A1|B1 outside the 4 mm ground keepout",
        "reader of B2 does not fit corridor A2|B2 outside the 4 mm ground keepout",
    ]
    assert problems(lambda m, _: m["play_area_heights_mm"].update(reader_qfn=2.0)) == [
        "reader_qfn stands 2 mm, over the 1.8 mm under the plywood"
    ]

    def tall_sensor(_, raw):
        next(s for s in raw["hall_rfid"]["sensors"] if s["part"] == "DRV5055A3")[
            "height_mm"] = 1.9

    assert problems(tall_sensor) == ["DRV5055A3 stands 1.9 mm, over the 1.8 mm under the plywood"]
    holes = problems(lambda m, _: m["board"].update(hole_d_mm=11.0))
    assert "M3 hole at (96.25, 3.75) cuts a loop" in holes
    assert problems(lambda m, _: m["board"].update(rail_mm=4.0))[0].endswith("leaves the rails")
    spread = problems(lambda m, _: m["hall"].update(cluster_offset_ratio=0.2))
    assert "Hall sensor at (10.00, 10.00) leaves the opening of A1" in spread
    assert any("cluster covers" in p for p in spread)
    pins = problems(lambda m, _: m["esp32"]["pins"].update(HALL_B1=11, LED=0, RFID_IRQ=19,
                                                           NSS_A1=35))
    assert {"GPIO11 carries two signals", "HALL_B1 on GPIO11, not an ADC1 input",
            "LED drives the strapping pin GPIO0", "RFID_IRQ takes the USB pin GPIO19",
            "NSS_A1 on GPIO35, kept free for the octal PSRAM"} <= set(pins)
    assert problems(lambda m, _: m["esp32"]["pins"].pop("NRSTPD_A2")) == [
        "the pin map lacks NRSTPD_A2"
    ]
    mux = problems(lambda m, _: m["mux_channels"].update(cluster=[4, 5, 6, 6],
                                                         extension=[11, 12, 13, 14, 16]))
    assert mux == ["a mux channel is used twice",
                   "a mux channel lies beyond the 16 of the CD74HC4067"]
    hungry = problems(lambda m, _: m["power"].update(esp32_ma=800.0))
    assert "3.3 V load of 1056 mA over the AMS1117-3.3 rating" in hungry
    hot = problems(lambda m, _: m["power"].update(theta_ja_c_per_w=300.0))
    assert hot == ["AMS1117-3.3 junction at 264 C"]

    def low_input(m, _):
        m["power"]["v_in_min"] = 4.5

    assert problems(low_input) == [
        "AMS1117-3.3 input of 4.5 V leaves 1.20 V, under its 1.3 V dropout"
    ]
    pins = problems(lambda m, _: m["esp32"]["pins"].update(USB_DM=20, USB_DP=19, LED=26))
    assert {"USB_DM off its USB pin GPIO19", "USB_DP off its USB pin GPIO20",
            "LED on GPIO26, not a pin of the ESP32-S3-WROOM-1-N8"} <= set(pins)
    assert problems(lambda m, _: m["esp32"]["pins"].pop("SPI_MISO")) == [
        "the pin map lacks SPI_MISO"
    ]

    def sensitive(_, raw):
        # the 60 mV/mT option of the same part, same package and pins
        next(s for s in raw["hall_rfid"]["sensors"] if s["part"] == "DRV5055A3")[
            "sensitivity_mv_per_mt"] = 60.0

    hot_king = problems(sensitive)
    assert "DRV5055A3: the pressed king leaves the sensor's linear range" in hot_king
    assert any(p.startswith("DRV5055A3: the pressed king reads") for p in hot_king)

    def crowded_l70(m, _):
        m["loops"]["L70x2"].update(turns=11)

    assert "Hall sensor at (0.00, 0.00) leaves the opening of B1" in problems(crowded_l70)
    for edit in (lambda m, _: m.update(ground_keepout_min_mm=6.0),
                 lambda m, _: m["reader"].update(i_idle_max_ma=1.0)):
        with pytest.raises(ValueError):
            _with(raw_config_dict, edit)

    def stricter(_, raw):
        raw["hall_rfid"]["layout"]["admissible_offset_mm"] = 9.5

    assert problems(stricter) == ["the A1 cluster covers +-9.32 mm, under the admissible +-9.5 mm"]
    with pytest.raises(ValueError):
        _with(raw_config_dict, lambda m, _: m["power"].update(v_in=[3.0, 5.0]))


def test_every_piece_is_seen_further_than_the_pawn(cfg):
    cov = cluster_coverage(cfg, 50.0)
    assert cov.weakest == PieceType.PAWN
    assert all(r >= cov.detection_radius_mm for r in cov.radius_mm.values())
    assert cov.detection_radius_mm == pytest.approx(6.61, abs=0.02)
    # the edge midpoint (h, 0) is the last point the corner sensor (a, a) reaches
    a = _mk(cfg).hall.cluster_offset_ratio * 50.0
    assert cov.covered_mm == pytest.approx(
        a + math.sqrt(cov.detection_radius_mm**2 - a * a), abs=1e-6
    )


def test_own_margin_cannot_hold_a_reader(cfg):
    # note 25, 4.2: once the 4 mm keepout is removed, the own margin of a
    # square offers at most a 7.2 mm free square (L60x3) or 4.7 mm (L70x2)
    # at p = 50, under the 8 mm a reader needs: readers go in the corridors
    footprint = _mk(cfg).reader.footprint_square_mm
    expected = {(50.0, "L60x3"): 7.17, (50.0, "L70x2"): 4.67,
                (40.0, "L60x3"): 5.17, (40.0, "L70x2"): 3.17}
    for pitch in cfg.pitch.candidates_mm:
        for keepout in (_mk(cfg).ground_keepout_mm, _mk(cfg).ground_keepout_min_mm):
            lay = layout(cfg, pitch, keepout)
            for sq in lay.squares:
                lp = lay.loop(sq.name)
                # an inner corner, against the rounded keepout corner
                margin = (pitch - lp.side_mm) / 2.0
                assert sq.free_square_mm == pytest.approx(margin - keepout / math.sqrt(2),
                                                          abs=2e-3)
                # the 2 mm keepout is the p = 40 variant; at p = 50 it would
                # leave an L60x3 square 8.6 mm, room for its own reader
                roomy = (pitch, keepout, lp.kind) == (50.0, 2.0, "L60x3")
                assert (sq.free_square_mm >= footprint) == roomy
                if keepout == _mk(cfg).ground_keepout_mm:
                    assert sq.free_square_mm == pytest.approx(expected[(pitch, lp.kind)],
                                                              abs=0.01)


def test_largest_free_square_against_simple_shapes():
    assert largest_free_square_mm((0.0, 0.0, 10.0, 6.0), []) == pytest.approx(6.0, abs=1e-6)
    # a point obstacle with 2 mm clearance in the middle of a 10 mm box:
    # the best square sits in a corner, its far corner 2 mm from the point
    side = largest_free_square_mm((0.0, 0.0, 10.0, 10.0), [((5.0, 5.0, 5.0, 5.0), 2.0)])
    assert side == pytest.approx(5.0 - 2.0 / math.sqrt(2), abs=2e-3)
    # an obstacle out of reach changes nothing
    far = largest_free_square_mm((0.0, 0.0, 10.0, 6.0), [((20.0, 0.0, 30.0, 6.0), 4.0)])
    assert far == pytest.approx(6.0, abs=1e-6)
    assert largest_free_square_mm((0.0, 0.0, 4.0, 4.0), [((0.0, 0.0, 4.0, 4.0), 1.0)]) == 0.0
