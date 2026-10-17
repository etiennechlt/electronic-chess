"""The 100 x 100 mm Hall plus RFID demonstrator (note 27): its geometry
derives from the yaml, its guards hold at the mockup pitch, and the
numbers the generator and the documents read are pinned here."""

import pytest

from chessboard_calc import hallrfid_demo as demo
from chessboard_calc.hallrfid_mockup import hall_chain


def test_yaml_holds(cfg):
    assert demo.check(cfg) == []


def test_board_squares_loops_and_pour(cfg):
    lay = demo.layout(cfg)
    assert lay.board == (0.0, 0.0, 100.0, 100.0)
    assert lay.play_area == (0.0, 0.0, 100.0, 50.0)
    assert lay.strip == (0.0, 50.0, 100.0, 100.0)
    assert [sq.name for sq in lay.squares] == ["A1", "B1"]
    assert {sq.name: sq.centre_mm for sq in lay.squares} == {"A1": (25.0, 25.0), "B1": (75.0, 25.0)}
    a1, b1 = lay.loop("A1"), lay.loop("B1")
    assert (a1.kind, a1.turns, a1.side_mm, a1.opening_mm) == ("L60x3", 3, 30.0, 22.0)
    assert (b1.kind, b1.turns, b1.side_mm, b1.opening_mm) == ("L70x2", 2, 35.0, 30.0)
    assert a1.outline == (10.0, 10.0, 40.0, 40.0)
    assert b1.outline == (57.5, 7.5, 92.5, 42.5)
    assert all(lp.feed_side == "S" for lp in lay.loops)
    # the pour starts the ground keepout past the lowest loop copper
    assert lay.pour == (0.5, 46.5, 99.5, 99.5)
    assert lay.pour[1] == pytest.approx(b1.outline[3] + cfg.hall_rfid.demo.ground_keepout_mm)


def test_reader_zones_sit_under_their_loop(cfg):
    lay = demo.layout(cfg)
    zone = cfg.hall_rfid.demo.reader_zone_mm
    assert lay.reader_zones["A1"] == (10.0, 40.5, 40.0, pytest.approx(46.5 + zone))
    assert lay.reader_zones["B1"] == (57.5, 43.0, 92.5, pytest.approx(46.5 + zone))
    for name, z in lay.reader_zones.items():
        area = (z[2] - z[0]) * (z[3] - z[1])
        assert area >= cfg.hall_rfid.mockup.reader.area_mm2[0], name


def test_trio_corridors_leave_the_openings_west_of_the_feed(cfg):
    lay = demo.layout(cfg)
    assert lay.trio_corridors["A1"] == (17.0, 36.0, 23.0, 46.5)
    assert lay.trio_corridors["B1"] == (67.0, 40.0, 73.0, 46.5)
    for name, c in lay.trio_corridors.items():
        cx = lay.square(name).centre_mm[0]
        assert c[2] < cx - demo.FEED_OFFSET_MM


def test_holes_and_fiducials(cfg):
    lay = demo.layout(cfg)
    assert lay.hole_inset_mm == pytest.approx(3.75)
    assert [h.centre_mm for h in lay.holes] == [
        (3.75, 3.75),
        (96.25, 3.75),
        (3.75, 46.25),
        (96.25, 46.25),
        (3.75, 96.25),
        (96.25, 96.25),
    ]
    assert all(h.loop_clearance_mm > 0.0 and h.edge_clearance_mm > 0.0 for h in lay.holes)
    assert len(lay.fiducials) == cfg.hall_rfid.demo.board.fiducials == 3
    for fid in lay.fiducials:
        assert 50.0 < fid.centre_mm[1] < 100.0


def test_six_hall_sensors_and_their_channels(cfg):
    lay = demo.layout(cfg)
    centre = [s for s in lay.hall_sites if s.role == "centre"]
    cluster = [s for s in lay.hall_sites if s.role == "cluster"]
    assert [s.square for s in centre] == ["A1", "B1"]
    assert [s.mux_channel for s in centre] == [0, 1]
    assert [s.direct_signal for s in centre] == ["HALL_A1", "HALL_B1"]
    assert len(cluster) == 4 and {s.square for s in cluster} == {"A1"}
    assert [s.mux_channel for s in cluster] == [4, 5, 6, 7]
    assert {s.centre_mm for s in cluster} == {
        (20.0, 20.0),
        (30.0, 20.0),
        (20.0, 30.0),
        (30.0, 30.0),
    }


def test_power_budget_of_two_readers_and_six_sensors(cfg):
    pw = demo.power(cfg)
    assert pw.loads_ma == {
        "esp32": 100.0,
        "reader_tx": 100.0,
        "readers_awake": pytest.approx(38.0),
        "hall_sensors": pytest.approx(60.0),
    }
    assert pw.total_ma == pytest.approx(298.0)
    assert pw.ok


def test_hall_chain_is_the_mockup_chain(cfg):
    ch = hall_chain(cfg, demo.layout(cfg).pitch_mm)
    assert ch.sensor.part == cfg.hall_rfid.mockup.hall.sensor
    assert ch.in_linear_range


def test_pin_map_rules(cfg):
    pins = cfg.hall_rfid.demo.esp32.pins
    adc1 = set(cfg.hall_rfid.mockup.esp32.adc1_gpios)
    for sig in ("MUX_OUT", "HALL_A1", "HALL_B1", "PICKUP"):
        assert pins[sig] in adc1, sig
    assert (pins["USB_DM"], pins["USB_DP"]) == (19, 20)
    assert len(set(pins.values())) == len(pins)
    assert not set(pins.values()) & set(cfg.hall_rfid.mockup.esp32.strapping_gpios)
    assert not set(pins.values()) & set(cfg.hall_rfid.mockup.esp32.psram_gpios)
    header = cfg.hall_rfid.demo.escape_header
    assert len(header) == 20
    assert set(header) - set(pins) == {"3V3", "GND"}


def _with(raw_config_dict, edit):
    from chessboard_calc.config import BoardConfig

    edit(raw_config_dict["hall_rfid"]["demo"], raw_config_dict)
    return BoardConfig.model_validate(raw_config_dict)


def test_guards_fire(raw_config_dict):
    import copy

    def problems(edit):
        return demo.check(_with(copy.deepcopy(raw_config_dict), edit))

    def smaller_strip(d, _):
        d["board"]["strip_mm"] = 40.0

    assert "row plus strip do not make the board height" in problems(smaller_strip)

    def wide_keepout(d, _):
        d["ground_keepout_mm"] = 60.0  # the pour, hence the reader zones, past the strip

    assert any("runs past the strip" in p for p in problems(wide_keepout))

    def duplicate_gpio(d, _):
        d["esp32"]["pins"]["LED"] = d["esp32"]["pins"]["MUX_S0"]

    assert "GPIO15 carries two signals" in problems(duplicate_gpio)

    def mux_hole(d, _):
        d["mux_channels"]["grounded"] = [2]

    assert any("every one of the 16 mux inputs" in p for p in problems(mux_hole))

    def corridor_east(d, _):
        d["trio_exit_mm"] = [-4.0, 1.0]

    assert any("not west of the feed" in p for p in problems(corridor_east))
