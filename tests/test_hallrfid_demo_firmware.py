"""The committed header of the demonstrator firmware is exactly what its
generator writes from the yaml, and what it says about the board agrees
with the layout and the pin map."""

import importlib.util
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
FW = ROOT / "firmware" / "esp32" / "hallrfid-demo"
SCRIPT = FW / "scripts" / "gen_config.py"
HEADER = FW / "main" / "demo_config.h"
YAML = ROOT / "config" / "board.yaml"


def _gen():
    spec = importlib.util.spec_from_file_location("gen_demo_config", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _define(text: str, name: str) -> str:
    m = re.search(rf"^#define {name} (.+)$", text, re.MULTILINE)
    assert m, name
    return m.group(1).strip()


def test_committed_header_matches_the_yaml(tmp_path):
    out = tmp_path / "demo_config.h"
    _gen().main(str(YAML), str(out))
    assert out.read_text(encoding="utf-8") == HEADER.read_text(encoding="utf-8"), (
        "run scripts/gen_config.py in firmware/esp32/hallrfid-demo and commit main/demo_config.h"
    )


def test_header_pins_and_sites_follow_the_yaml(cfg):
    from chessboard_calc.hallrfid_demo import layout

    text = HEADER.read_text(encoding="utf-8")
    dm = cfg.hall_rfid.demo
    for sig, gpio in dm.esp32.pins.items():
        assert _define(text, f"DEMO_PIN_{sig}") == str(gpio)
    lay = layout(cfg)
    channels = _define(text, "DEMO_SITE_CHANNEL")
    assert channels == "{" + ", ".join(f"{s.mux_channel}u" for s in lay.hall_sites) + "}"
    assert _define(text, "DEMO_SITES") == f"{len(lay.hall_sites)}u"
    assert _define(text, "DEMO_READERS") == f"{len(dm.squares())}u"
    nss = "{" + ", ".join(str(dm.esp32.pins[f"NSS_{sq}"]) for sq in dm.squares()) + "}"
    assert _define(text, "DEMO_READER_NSS") == nss
    assert _define(text, "DEMO_CH_GROUND") == f"{dm.mux_channels.ground}u"
    accept = cfg.hall_rfid.mockup.reader.i_tvdd_accept_ma
    assert _define(text, "DEMO_I_TVDD_ACCEPT_MA") == f"{accept:g}"


def test_thresholds_are_the_mockup_chain_numbers(cfg):
    from chessboard_calc.hall import adc_lsb_mv, hall_budget, sensor_index
    from chessboard_calc.hallrfid_demo import layout
    from chessboard_calc.hallrfid_mockup import hall_chain

    text = HEADER.read_text(encoding="utf-8")
    idx = sensor_index(cfg, cfg.hall_rfid.mockup.hall.sensor)
    sensor = cfg.hall_rfid.sensors[idx]
    pitch = layout(cfg).pitch_mm
    budget = hall_budget(cfg, pitch, idx)
    lsb = adc_lsb_mv(cfg)
    on = int(round(budget.threshold_mT * sensor.sensitivity_mv_per_mt / lsb))
    off = int(round(budget.release_mT * sensor.sensitivity_mv_per_mt / lsb))
    assert _define(text, "DEMO_ON_COUNTS") == str(on)
    assert _define(text, "DEMO_OFF_COUNTS") == str(off)
    assert off < on
    chain = hall_chain(cfg, pitch)
    assert _define(text, "DEMO_MUX_SETTLE_US") == f"{int(round(chain.settle_us))}u"
    assert _define(text, "DEMO_ROW_ON_US") == f"{int(round(chain.row_on_max_us))}u"
