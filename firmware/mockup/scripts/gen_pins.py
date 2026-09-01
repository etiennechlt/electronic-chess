#!/usr/bin/env python3
"""Generate src/board_pins.h from config/board.yaml (mockup.nucleo_pins).

Keeps the firmware pin map single-sourced. The generated header is
committed so plain `make` works without Python; run `make pins` after
editing the yaml.
"""

import sys

import yaml

TEMPLATE = """/* Generated from config/board.yaml by scripts/gen_pins.py. Do not edit. */
#ifndef BOARD_PINS_H
#define BOARD_PINS_H

{defines}
#endif
"""


def main(cfg_path: str, out_path: str) -> None:
    with open(cfg_path, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    pins = cfg["mockup"]["nucleo_pins"]
    lines = []
    for name, spec in pins.items():
        mcu = spec["mcu"]  # e.g. PA10
        port = mcu[1]
        num = int(mcu[2:])
        upper = name.upper()
        lines.append(f"#define {upper}_PORT GPIO{port}")
        lines.append(f"#define {upper}_PIN {num}u")
        lines.append(f"/* {upper}: {mcu}, Arduino {spec['arduino']} */")
        lines.append("")
    leds = cfg["mockup"]["coil_board"]["leds"]
    chain = leds["chain_squares"]
    lines.append(f"#define LED_COUNT {len(chain)}u")
    lines.append("/* zero-based square index per chain position */")
    lines.append("#define LED_CHAIN_SQ { "
                 + ", ".join(f"{k - 1}u" for k in chain) + " }")
    for camp in ("white", "black"):
        r, g, b = leds[f"color_{camp}"]
        lines.append(f"#define LED_COLOR_{camp.upper()} "
                     f"0x{r:02X}{g:02X}{b:02X}u")
    lines.append("")
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(TEMPLATE.format(defines="\n".join(lines)))
    print(f"wrote {out_path} ({len(pins)} pins)")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
