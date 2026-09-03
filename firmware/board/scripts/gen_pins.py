#!/usr/bin/env python3
"""Generate src/board_pins.h from config/board.yaml for the brain board.

Pins come from plateau.brain.mcu_pins; the LED chain (128 LEDs, four
quadrants in series, the right-hand pair mounted rotated) is taken from
the quadrant generator's layout so the firmware, the boards and the
wood template share one source. Needs the project's Python environment
(PYTHONPATH=tools); the generated header is committed so plain `make`
works without it.
"""

import sys

import yaml

TEMPLATE = """/* Generated from config/board.yaml by scripts/gen_pins.py. Do not edit. */
#ifndef BOARD_PINS_H
#define BOARD_PINS_H

{defines}
#endif
"""


def led_chain(cfg_path: str) -> list[int]:
    """Zero-based 8x8 square index (file + 8 * rank, rank 0 nearest the
    player) for every LED, in chain order across the four quadrants."""
    from quadgen.layout import make_layout

    from chessboard_calc.config import load_config
    from chessboard_calc.plateau import quadrant_origins

    cfg = load_config(cfg_path)
    lay = make_layout(cfg)
    n = lay.n
    chain: list[int] = []
    # quadrant order on the brain: Q1 north-west, Q2 north-east, Q3 south-west,
    # Q4 south-east; the east pair is rotated by 180 degrees
    origins = quadrant_origins(cfg)
    for ox, oy in origins:
        rotated = (ox > 0.0)
        for led in lay.leds:
            coil = lay.coils[led.coil]
            col, row = coil.col, coil.row
            if rotated:
                col, row = n - 1 - col, n - 1 - row
            file_idx = int(ox / cfg.pitch.plateau_mm) + col
            rank = int(oy / cfg.pitch.plateau_mm) + row
            chain.append(file_idx + 8 * rank)
    return chain


def main(cfg_path: str, out_path: str) -> None:
    with open(cfg_path, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    pins = cfg["plateau"]["brain"]["mcu_pins"]
    lines = []
    for name, mcu in pins.items():
        port = mcu[1]
        num = int(mcu[2:])
        upper = name.upper()
        lines.append(f"#define {upper}_PORT GPIO{port}")
        lines.append(f"#define {upper}_PIN {num}u")
        lines.append(f"/* {upper}: {mcu} */")
        lines.append("")
    leds = cfg["mockup"]["coil_board"]["leds"]
    chain = led_chain(cfg_path)
    lines.append(f"#define LED_COUNT {len(chain)}u")
    lines.append("/* zero-based 8x8 square index per chain position */")
    rows = [", ".join(f"{s}u" for s in chain[i:i + 16]) for i in range(0, len(chain), 16)]
    lines.append("#define LED_CHAIN_SQ { \\\n    " + ", \\\n    ".join(rows) + " }")
    for camp in ("white", "black"):
        r, g, b = leds[f"color_{camp}"]
        lines.append(f"#define LED_COLOR_{camp.upper()} 0x{r:02X}{g:02X}{b:02X}u")
    lines.append("")
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(TEMPLATE.format(defines="\n".join(lines)))
    print(f"wrote {out_path} ({len(pins)} pins, {len(chain)} LEDs)")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
