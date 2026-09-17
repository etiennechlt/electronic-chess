"""The Nucleo bench (note 19): the bus on the Arduino connectors is the
brain's, and the shield wires every header pin as the yaml says."""

import pytest
from analoggen.fplib import FOOTPRINT_DIR


def test_bench_bus_is_the_brains_except_damp(cfg):
    brain = cfg.plateau.brain.mcu_pins
    moved = {"DAMP_EN_N"}  # PC2 only reaches a Morpho connector (bench.signals comment)
    for signal, label in cfg.bench.signals.items():
        assert signal in brain, signal
        pin = cfg.bench.arduino_pins[label]
        if signal in moved:
            assert pin != brain[signal]
        else:
            assert pin == brain[signal], (signal, label, pin, brain[signal])
    # the converter and the comparator of the firmware read PA0 (ADC1_IN1, COMP3)
    assert cfg.bench.arduino_pins[cfg.bench.signals["ADC1"]] == "PA0"


def test_console_pins_are_not_on_the_bus(cfg):
    used = {cfg.bench.arduino_pins[label] for label in cfg.bench.signals.values()}
    assert cfg.bench.console.tx not in used and cfg.bench.console.rx not in used


@pytest.mark.skipif(not FOOTPRINT_DIR.exists(), reason="KiCad libraries not installed")
def test_shield_headers_follow_the_yaml(cfg):
    from boardgen.bench import HEADERS, build_bench_circuit

    ckt = build_bench_circuit(cfg)
    by_ref = {c.ref: c for c in ckt.components}
    by_label = {label: signal for signal, label in cfg.bench.signals.items()}
    seen = set()
    for ref, (_title, _part, labels) in HEADERS.items():
        comp = by_ref[ref]
        for i, label in enumerate(labels, start=1):
            net = comp.pins.get(str(i))
            if label in by_label:
                assert net == by_label[label], (ref, i, label)
                seen.add(label)
            elif label == "GND":
                assert net == "GND"
            elif label == "3V3":
                assert net == "3V3"
            else:
                assert net is None, (ref, i, label)  # NC, 5V, VIN, IOREF, NRST, AREF stay open
    assert seen == set(cfg.bench.signals.values())


@pytest.mark.skipif(not FOOTPRINT_DIR.exists(), reason="KiCad libraries not installed")
def test_shield_link_mirrors_the_quadrant_pinout(cfg):
    from boardgen.bench import build_bench_circuit

    ckt = build_bench_circuit(cfg)
    j2 = next(c for c in ckt.components if c.ref == "J2")
    nets = [j2.pins[str(i + 1)] for i in range(16)]
    for a, b in zip(cfg.plateau.quadrant.link.pinout, nets, strict=True):
        if a in ("AMP_OUT", "LED_DIN", "LED_DOUT"):
            continue
        assert a == b
    assert nets[3] == "AMP_OUT1" and nets[6] == "LED_DIN1" and nets[12] == "LED_END"


@pytest.mark.skipif(not FOOTPRINT_DIR.exists(), reason="KiCad libraries not installed")
def test_shield_rows_sit_on_the_uno_pattern(cfg):
    """Pin k of every row lands on the Uno footprint pad it stands for."""
    from analoggen.fplib import load_footprint, pad_abs_pos
    from boardgen.bench import HEADERS, UNO_FOOTPRINT, UNO_OFFSET, UNO_ROW_ORIGIN, header_placements

    uno = {p.number: (p.dx, p.dy) for p in load_footprint(UNO_FOOTPRINT).pads}
    ox, oy = UNO_OFFSET
    placed = header_placements()
    for ref, (_title, part, labels) in HEADERS.items():
        fp = load_footprint(part.footprint)
        x, y, rot = placed[ref]
        first, _direction = UNO_ROW_ORIGIN[ref]  # Uno pad numbers grow along every row
        for k, pad in enumerate(fp.pads):
            px, py = pad_abs_pos(x, y, rot, pad)
            ux, uy = uno[str(int(first) + k)]
            assert abs(px - (ox + ux)) < 0.01 and abs(py - (oy + uy)) < 0.01, (ref, k, labels[k])
