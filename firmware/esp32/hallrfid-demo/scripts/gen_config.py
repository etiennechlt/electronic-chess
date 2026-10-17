#!/usr/bin/env python3
"""Generate main/demo_config.h from config/board.yaml for the Hall plus
RFID demonstrator (note 27): the ESP32-S3 pins of hall_rfid.demo, the
mux channel of every sensor site and the reference channels, the Hall
thresholds in ADC counts through chessboard_calc.hall at the mockup
pitch, the settling times of chessboard_calc.hallrfid_mockup.hall_chain,
and the bring-up criteria of the yaml the console prints. The header is
committed so a plain ESP-IDF build works without Python; the test
tests/test_hallrfid_demo_firmware.py checks it is current.
"""

import sys

from chessboard_calc.config import load_config
from chessboard_calc.hall import adc_lsb_mv, hall_budget, sensor_index
from chessboard_calc.hallrfid_demo import layout
from chessboard_calc.hallrfid_mockup import hall_chain

TEMPLATE = """/* Generated from config/board.yaml by scripts/gen_config.py. Do not edit. */
#ifndef DEMO_CONFIG_H
#define DEMO_CONFIG_H

{defines}
#endif
"""


def site_name(site, square_centre) -> str:
    if site.role == "centre":
        return site.square
    dx = site.centre_mm[0] - square_centre[0]
    dy = site.centre_mm[1] - square_centre[1]
    return f"{site.square}_{'n' if dy > 0 else 's'}{'e' if dx > 0 else 'w'}"


def main(cfg_path: str, out_path: str) -> None:
    cfg = load_config(cfg_path)
    hr = cfg.hall_rfid
    dm = hr.demo
    mk = hr.mockup
    lay = layout(cfg)
    sensor = hr.sensors[sensor_index(cfg, mk.hall.sensor)]
    budget = hall_budget(cfg, lay.pitch_mm, sensor_index(cfg, mk.hall.sensor))
    chain = hall_chain(cfg, lay.pitch_mm)
    lsb = adc_lsb_mv(cfg)

    def counts(field_mt: float) -> int:
        return int(round(field_mt * sensor.sensitivity_mv_per_mt / lsb))

    centres = {sq.name: sq.centre_mm for sq in lay.squares}
    sites = lay.hall_sites
    names = [site_name(s, centres[s.square]) for s in sites]
    squares = dm.squares()
    pins = dm.esp32.pins
    lines = [
        f"/* {sensor.part}: {lsb:.3f} mV per ADC count, {sensor.sensitivity_mv_per_mt:g} mV/mT, "
        f"pitch {lay.pitch_mm:g} mm */",
        f'#define DEMO_SENSOR "{sensor.part}"',
        f"#define DEMO_ADC_LSB_MV {lsb:.4f}",
        f"#define DEMO_SENSITIVITY_MV_PER_MT {sensor.sensitivity_mv_per_mt:g}",
        f"#define DEMO_BASELINE_COUNTS {int(round(sensor.quiescent_out_v * 1e3 / lsb))}",
        f"#define DEMO_RAIL_HALF_COUNTS {int(round(mk.power.regulator.v_out * 1e3 / 2.0 / lsb))}",
        f"#define DEMO_ON_COUNTS {counts(budget.threshold_mT)}",
        f"#define DEMO_OFF_COUNTS {counts(budget.release_mT)}",
        f"#define DEMO_WEAKEST_PRESENT_COUNTS {counts(budget.weakest_present_mT)}",
        f"#define DEMO_ADC_FULL_SCALE_MV {int(round(hr.esp32.adc_full_scale_mv))}u",
        f"#define DEMO_SAMPLES {hr.esp32.samples_per_square}u",
        "",
        "/* timing from hallrfid_mockup.hall_chain: ROW_EN to a valid reading, and the",
        " * mux settling after the worst kick of its common node */",
        f"#define DEMO_ROW_ON_US {int(round(chain.row_on_max_us))}u",
        f"#define DEMO_MUX_SETTLE_US {int(round(chain.settle_us))}u",
        "",
        f"/* {mk.esp32.module} GPIO numbers (hall_rfid.demo.esp32.pins) */",
    ]
    for name, gpio in pins.items():
        lines.append(f"#define DEMO_PIN_{name} {gpio}")
    lines += [
        "",
        "/* the sensor sites: mux channel, name, whether a direct ADC input doubles it */",
        f"#define DEMO_SITES {len(sites)}u",
        "#define DEMO_SITE_CHANNEL {" + ", ".join(f"{s.mux_channel}u" for s in sites) + "}",
        "#define DEMO_SITE_NAME {" + ", ".join(f'"{n}"' for n in names) + "}",
        "#define DEMO_SITE_DIRECT_PIN {"
        + ", ".join(str(pins[s.direct_signal]) if s.direct_signal else "-1" for s in sites)
        + "}",
        f"#define DEMO_CH_GROUND {dm.mux_channels.ground}u",
        f"#define DEMO_CH_RAIL_HALF {dm.mux_channels.rail_half}u",
        f"#define DEMO_CH_LED_STEP {dm.mux_channels.led_step}u",
        "",
        "/* the readers, in square order: NSS and NRSTPD pins */",
        f"#define DEMO_READERS {len(squares)}u",
        "#define DEMO_READER_NAME {" + ", ".join(f'"{sq}"' for sq in squares) + "}",
        "#define DEMO_READER_NSS {" + ", ".join(str(pins[f"NSS_{sq}"]) for sq in squares) + "}",
        "#define DEMO_READER_NRSTPD {"
        + ", ".join(str(pins[f"NRSTPD_{sq}"]) for sq in squares)
        + "}",
        "",
        "/* bring-up criteria the console prints (hall_rfid.mockup) */",
        f"#define DEMO_R_SENSE_OHM {mk.reader.r_sense_ohm:g}",
        f"#define DEMO_I_TVDD_ACCEPT_MA {mk.reader.i_tvdd_accept_ma:g}",
        f"#define DEMO_I_IDLE_MA {mk.reader.i_idle_ma:g}",
        f"#define DEMO_I_IDLE_MAX_MA {mk.reader.i_idle_max_ma:g}",
        f"#define DEMO_HALL_I_MA {sensor.i_supply_ma:g}",
        f"#define DEMO_HALL_I_MAX_MA {(sensor.i_supply_max_ma or sensor.i_supply_ma):g}",
        "#define DEMO_NXP_VERSION {"
        + ", ".join(f"0x{v:02X}" for v in mk.criteria.nxp_version_reg)
        + "}",
        f"#define DEMO_READ_TRIALS {mk.criteria.read_trials}u",
        f"#define DEMO_READ_TRIALS_CONFIRM {mk.criteria.read_trials_confirm}u",
        "",
    ]
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(TEMPLATE.format(defines="\n".join(lines)))
    print(f"wrote {out_path} ({len(pins)} pins, {len(sites)} sites, {len(squares)} readers)")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
