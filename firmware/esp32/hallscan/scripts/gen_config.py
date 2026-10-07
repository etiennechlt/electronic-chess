#!/usr/bin/env python3
"""Generate main/hallscan_config.h from config/board.yaml for the Hall
scanner of note 24: thresholds in ADC counts (through chessboard_calc.hall,
so the firmware, the report and the tests share one model), the ESP32-S3
pins, the scan timing and the mux channel to square mapping (one mux per
quadrant, channels row-major from the player's side, quadrant order of
chessboard_calc.plateau.quadrant_origins). The generated header is
committed so a plain build works without Python.
"""

import sys

from chessboard_calc.config import load_config
from chessboard_calc.hall import adc_lsb_mv, hall_budget
from chessboard_calc.plateau import quadrant_origins

TEMPLATE = """/* Generated from config/board.yaml by scripts/gen_config.py. Do not edit. */
#ifndef HALLSCAN_CONFIG_H
#define HALLSCAN_CONFIG_H

{defines}
#endif
"""


def square_map(cfg) -> list[list[int]]:
    """Board square (file + 8 * rank, a1 = 0) of every mux channel."""
    q = cfg.plateau.quadrant.squares
    p = cfg.pitch.plateau_mm
    grid = cfg.plateau.grid
    maps = []
    for ox, oy in quadrant_origins(cfg):
        file0, rank0 = int(round(ox / p)), int(round(oy / p))
        maps.append([file0 + idx % q + grid * (rank0 + idx // q) for idx in range(q * q)])
    return maps


def main(cfg_path: str, out_path: str) -> None:
    cfg = load_config(cfg_path)
    hr = cfg.hall_rfid
    sensor = hr.sensors[0]
    q = cfg.plateau.quadrant.squares
    if hr.mux.channels != q * q:
        raise SystemExit("hall_rfid.mux.channels must equal the squares of a quadrant")
    budget = hall_budget(cfg, cfg.pitch.plateau_mm)
    lsb = adc_lsb_mv(cfg)

    def counts(field_mt: float) -> int:
        return int(round(field_mt * sensor.sensitivity_mv_per_mt / lsb))

    maps = square_map(cfg)
    rows = ["{" + ", ".join(f"{s}u" for s in m) + "}" for m in maps]
    lines = [
        f'#define HALL_SENSOR "{sensor.part}"',
        f"/* ADC counts: {lsb:.3f} mV per LSB, {sensor.sensitivity_mv_per_mt:g} mV/mT */",
        f"#define HALL_BASELINE_COUNTS {int(round(sensor.quiescent_out_v * 1e3 / lsb))}",
        f"#define HALL_ON_COUNTS {counts(budget.threshold_mT)}",
        f"#define HALL_OFF_COUNTS {counts(budget.release_mT)}",
        f"#define HALL_WEAKEST_PRESENT_COUNTS {counts(budget.weakest_present_mT)}",
        f"#define HALL_STRONGEST_LIFTED_COUNTS {counts(budget.strongest_lifted_mT)}",
        f"#define HALL_DEBOUNCE_SCANS {hr.presence.debounce_scans}u",
        f"#define HALL_COLOR_BY_POLARITY {int(hr.color_by_polarity)}",
        "#define HALL_WHITE_POSITIVE 1   /* which pole faces down: set at calibration */",
        "",
        "/* scan: one mux per quadrant, sensor supply switched per row of each quadrant */",
        f"#define HALL_MUX_COUNT {len(maps)}u",
        f"#define HALL_MUX_CHANNELS {hr.mux.channels}u",
        f"#define HALL_GROUPS {hr.power_gating.groups}u",
        f"#define HALL_SAMPLES_PER_SQUARE {hr.esp32.samples_per_square}u",
        f"#define HALL_MUX_SETTLE_US {int(round(hr.mux.t_settle_us))}u",
        f"#define HALL_POWER_ON_US {int(round(sensor.power_on_us))}u",
        f"#define HALL_ADC_FULL_SCALE_MV {int(round(hr.esp32.adc_full_scale_mv))}u",
        "",
        f"/* {hr.esp32.module} GPIO numbers */",
    ]
    for name, gpio in hr.esp32.pins.items():
        lines.append(f"#define HALL_PIN_{name} {gpio}")
    lines += [
        "",
        "/* board square (file + 8 * rank, a1 = 0) per mux and channel */",
        "#define HALL_SQUARE_OF { \\\n    " + ", \\\n    ".join(rows) + " }",
        "",
    ]
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(TEMPLATE.format(defines="\n".join(lines)))
    print(f"wrote {out_path} ({len(hr.esp32.pins)} pins, {len(maps)} muxes)")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
