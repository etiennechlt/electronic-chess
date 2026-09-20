"""The committed brain pin header is exactly what gen_pins.py writes from the yaml."""

import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "firmware" / "board" / "scripts" / "gen_pins.py"
HEADER = ROOT / "firmware" / "board" / "src" / "board_pins.h"
YAML = ROOT / "config" / "board.yaml"


def _gen_pins():
    spec = importlib.util.spec_from_file_location("gen_pins", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_committed_header_matches_the_yaml(tmp_path):
    out = tmp_path / "board_pins.h"
    _gen_pins().main(str(YAML), str(out))
    assert out.read_text(encoding="utf-8") == HEADER.read_text(encoding="utf-8"), (
        "run `make pins` in firmware/board and commit src/board_pins.h"
    )


def test_plateau_chain_covers_the_64_squares_twice(cfg):
    chain = _gen_pins().led_chain(str(YAML))
    assert len(chain) == 2 * cfg.plateau.grid**2
    assert sorted(set(chain)) == list(range(cfg.plateau.grid**2))


def test_bench_chain_is_the_reduced_quadrant_at_a1(cfg):
    n = cfg.plateau.quadrant.reduced.squares
    chain = _gen_pins().led_chain(str(YAML), reduced=True)
    assert len(chain) == 2 * n * n
    assert sorted(set(chain)) == sorted(c + 8 * r for r in range(n) for c in range(n))


def test_bench_console_is_on_a_port_pin(cfg):
    con = cfg.bench.console
    assert con.usart == 2
    for pin in (con.tx, con.rx):
        assert pin[0] == "P" and pin[1] in "ABCD" and pin[2:].isdigit()


def test_full_quadrant_bench_chain_is_one_quadrant_at_a1(cfg):
    n = cfg.plateau.quadrant.squares
    chain = _gen_pins().led_chain(str(YAML), single=True)
    assert len(chain) == 2 * n * n
    assert sorted(set(chain)) == sorted(c + 8 * r for r in range(n) for c in range(n))
    # the same LED order as the first quadrant of the plateau chain
    assert chain == _gen_pins().led_chain(str(YAML))[: 2 * n * n]
