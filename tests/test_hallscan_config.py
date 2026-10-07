"""The committed header of the Hall scanner is exactly what gen_config.py
writes from the yaml, and its mapping covers the board once."""

import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "firmware" / "esp32" / "hallscan" / "scripts" / "gen_config.py"
HEADER = ROOT / "firmware" / "esp32" / "hallscan" / "main" / "hallscan_config.h"
YAML = ROOT / "config" / "board.yaml"


def _gen():
    spec = importlib.util.spec_from_file_location("gen_config", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_committed_header_matches_the_yaml(tmp_path):
    out = tmp_path / "hallscan_config.h"
    _gen().main(str(YAML), str(out))
    assert out.read_text(encoding="utf-8") == HEADER.read_text(encoding="utf-8"), (
        "run scripts/gen_config.py in firmware/esp32/hallscan and commit main/hallscan_config.h"
    )


def test_mux_channels_cover_the_64_squares_once(cfg):
    maps = _gen().square_map(cfg)
    assert len(maps) == (cfg.plateau.grid // cfg.plateau.quadrant.squares) ** 2
    flat = [sq for m in maps for sq in m]
    assert sorted(flat) == list(range(cfg.plateau.grid**2))
    # channel 0 of the first mux is a1, channel 1 is b1: row-major from the player
    assert maps[0][:2] == [0, 1]


def test_thresholds_in_the_header_are_the_report_numbers(cfg):
    text = HEADER.read_text(encoding="utf-8")
    from chessboard_calc.hall import adc_lsb_mv, hall_budget

    b = hall_budget(cfg, cfg.pitch.plateau_mm)
    sens = cfg.hall_rfid.sensors[0].sensitivity_mv_per_mt
    on = round(b.threshold_mT * sens / adc_lsb_mv(cfg))
    assert f"#define HALL_ON_COUNTS {on}\n" in text
    assert f"#define HALL_DEBOUNCE_SCANS {cfg.hall_rfid.presence.debounce_scans}u\n" in text
