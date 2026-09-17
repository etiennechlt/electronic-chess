#!/usr/bin/env python3
"""Generate src/board_pins.h from config/board.yaml for the brain board.

Pins come from plateau.brain.mcu_pins; the LED chain (128 LEDs, four
quadrants in series, the right-hand pair mounted rotated) is taken from
the quadrant generator's layout so the firmware, the boards and the
wood template share one source. The NUCLEO=1 bench (note 19) gets its
own block: the console on the ST-Link virtual COM port (bench.console)
and the LED chain of the reduced 2 x 2 quadrant. Needs the project's
Python environment (PYTHONPATH=tools); the generated header is
committed so plain `make` works without it.
"""

import sys

import yaml

TEMPLATE = """/* Generated from config/board.yaml by scripts/gen_pins.py. Do not edit. */
#ifndef BOARD_PINS_H
#define BOARD_PINS_H

{defines}
#endif
"""


def led_chain(cfg_path: str, reduced: bool = False) -> list[int]:
    """Zero-based 8x8 square index (file + 8 * rank, rank 0 nearest the
    player) for every LED, in chain order across the four quadrants, or
    for the single reduced quadrant of the bench placed at the origin."""
    from quadgen.layout import make_layout
    from quadgen.variant import reduced_config

    from chessboard_calc.config import load_config
    from chessboard_calc.plateau import quadrant_origins

    cfg = load_config(cfg_path)
    if reduced:
        cfg = reduced_config(cfg)
        origins = [(0.0, 0.0)]
    else:
        # quadrant order on the brain: Q1 north-west, Q2 north-east, Q3
        # south-west, Q4 south-east; the east pair is rotated by 180 degrees
        origins = quadrant_origins(cfg)
    lay = make_layout(cfg)
    n = lay.n
    chain: list[int] = []
    for ox, oy in origins:
        rotated = ox > 0.0
        for led in lay.leds:
            coil = lay.coils[led.coil]
            col, row = coil.col, coil.row
            if rotated:
                col, row = n - 1 - col, n - 1 - row
            file_idx = int(ox / cfg.pitch.plateau_mm) + col
            rank = int(oy / cfg.pitch.plateau_mm) + row
            chain.append(file_idx + 8 * rank)
    return chain


def pin_defines(name: str, mcu: str) -> list[str]:
    port = mcu[1]
    num = int(mcu[2:])
    return [
        f"#define {name}_PORT GPIO{port}",
        f"#define {name}_PIN {num}u",
        f"/* {name}: {mcu} */",
        "",
    ]


def chain_defines(prefix: str, chain: list[int]) -> list[str]:
    rows = [", ".join(f"{s}u" for s in chain[i : i + 16]) for i in range(0, len(chain), 16)]
    return [
        f"#define {prefix}LED_COUNT {len(chain)}u",
        "/* zero-based 8x8 square index per chain position */",
        f"#define {prefix}LED_CHAIN_SQ {{ \\\n    " + ", \\\n    ".join(rows) + " }",
    ]


def main(cfg_path: str, out_path: str) -> None:
    with open(cfg_path, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    pins = cfg["plateau"]["brain"]["mcu_pins"]
    lines = []
    for name, mcu in pins.items():
        lines.extend(pin_defines(name.upper(), mcu))
    leds = cfg["mockup"]["coil_board"]["leds"]
    chain = led_chain(cfg_path)
    lines.extend(chain_defines("", chain))
    for camp in ("white", "black"):
        r, g, b = leds[f"color_{camp}"]
        lines.append(f"#define LED_COLOR_{camp.upper()} 0x{r:02X}{g:02X}{b:02X}u")
    quad = cfg["plateau"]["quadrant"]
    grid = cfg["plateau"]["grid"]
    lines.append("")
    lines.append(
        "/* grid: coils per quadrant row on the plateau and on the reduced bench quadrant */"
    )
    lines.append(f"#define QUADRANT_SQUARES {quad['squares']}u")
    lines.append(f"#define REDUCED_SQUARES {quad['reduced']['squares']}u")
    lines.append(f"#define PLATEAU_QUADRANTS {(grid // quad['squares']) ** 2}u")
    bench = cfg["bench"]
    lines.append("")
    lines.append(f"/* NUCLEO=1 bench: {bench['board']}, console on the ST-Link virtual COM port */")
    lines.append(f"#define NUCLEO_CONSOLE_USART {bench['console']['usart']}u")
    lines.extend(pin_defines("NUCLEO_CONSOLE_TX", bench["console"]["tx"]))
    lines.extend(pin_defines("NUCLEO_CONSOLE_RX", bench["console"]["rx"]))
    lines.append(
        "/* quadrant bus on the Arduino connectors (bench.signals); board.h applies them */"
    )
    for signal, label in bench["signals"].items():
        lines.extend(pin_defines(f"NUCLEO_{signal.upper()}", bench["arduino_pins"][label]))
    nchain = led_chain(cfg_path, reduced=True)
    lines.extend(chain_defines("NUCLEO_", nchain))
    lines.append("")
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(TEMPLATE.format(defines="\n".join(lines)))
    print(f"wrote {out_path} ({len(pins)} pins, {len(chain)} LEDs, {len(nchain)} bench LEDs)")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
