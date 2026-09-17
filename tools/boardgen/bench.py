"""The bench shield (note 19): a Nucleo-64 shield that drives the reduced
2 x 2 quadrant from a Nucleo-G474RE while the brain and the power board
are not built yet. It carries what the brain would have given the
quadrant and nothing else: the 12 V rail from a protected jack, the 5 V
buck for the LEDs, the LP2985 plus ferrite bead analog island for 5VA,
the 74AHCT1G125 LED buffer, the FPC link with the quadrant's own pinout,
the RC in front of the ADC, test points, and the four Arduino Uno V3
pin headers that plug into the Nucleo.

Header geometry comes from the official Arduino_UNO_R3 footprint (the
four rows of the Uno V3 pattern), the bus assignment from bench.signals
in config/board.yaml, which the NUCLEO=1 firmware build applies too.
80 x 56 mm, 2 layers: parts and signals on F.Cu, ground pour on B.Cu.
"""

from __future__ import annotations

from analoggen.circuit import C1206, CP, DSS34, DTVS, FB, JACK, LDO, TP, C, Circuit, Part, R
from analoggen.fplib import load_footprint

from chessboard_calc.config import BoardConfig

from .brain import BUCK3A, BUF5, FPC16, FUSE, H1X03, LBUCK, link_pinout
from .core import GenericBoard, Spec, pins_by_name, shelf

GND = "GND"
H1X06 = Part(
    "Connector_Generic", "Conn_01x06", "Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical"
)
H1X08 = Part(
    "Connector_Generic", "Conn_01x08", "Connector_PinHeader_2.54mm:PinHeader_1x08_P2.54mm_Vertical"
)
H1X10 = Part(
    "Connector_Generic", "Conn_01x10", "Connector_PinHeader_2.54mm:PinHeader_1x10_P2.54mm_Vertical"
)

# The Uno V3 connector rows, pin 1 first, as the Nucleo-64 exposes them
# (UM2505): power and analog on one edge, the two digital rows on the
# other. NC pins stay open on the shield.
HEADERS = {
    "J3": ("POWER", H1X08, ("NC", "IOREF", "NRST", "3V3", "5V", "GND", "GND", "VIN")),
    "J4": ("ANALOG", H1X06, ("A0", "A1", "A2", "A3", "A4", "A5")),
    "J5": ("DIGITAL 0-7", H1X08, ("D0", "D1", "D2", "D3", "D4", "D5", "D6", "D7")),
    "J6": (
        "DIGITAL 8-15",
        H1X10,
        ("D8", "D9", "D10", "D11", "D12", "D13", "GND", "AREF", "D14", "D15"),
    ),
}
# Pad of the Arduino_UNO_R3 footprint that carries pin 1 of each row, and
# the direction the row runs in that footprint's frame.
UNO_ROW_ORIGIN = {"J3": ("1", 1), "J4": ("9", 1), "J5": ("15", -1), "J6": ("23", -1)}
UNO_FOOTPRINT = "Module:Arduino_UNO_R3"
# the Uno outline (68.58 x 53.34) sits flush west and centred vertically
UNO_OFFSET = (27.94, 3.87)

# Shield nets of the Nucleo power pins: the shield takes 3.3 V from the
# Nucleo for the quadrant logic and shares its ground; its own 5 V never
# feeds the Nucleo (the ST-Link USB does) and VIN of the Nucleo stays open.
POWER_PIN_NETS = {"3V3": "3V3", "GND": GND}


def header_nets(cfg: BoardConfig, ref: str) -> tuple[dict[str, str], tuple[str, ...]]:
    """Pin number to net of one header, and its open pins."""
    by_label = {label: signal for signal, label in cfg.bench.signals.items()}
    _title, _part, labels = HEADERS[ref]
    pins: dict[str, str] = {}
    nc: list[str] = []
    for i, label in enumerate(labels, start=1):
        if label in by_label:
            pins[str(i)] = by_label[label]
        elif label in POWER_PIN_NETS:
            pins[str(i)] = POWER_PIN_NETS[label]
        else:
            nc.append(str(i))
    return pins, tuple(nc)


def build_bench_circuit(cfg: BoardConfig) -> Circuit:
    ckt = Circuit()

    def r(ref, value, a, b, part=R):
        ckt.add(ref, part, value, {"1": a, "2": b})

    def c(ref, value, a, b, part=C):
        ckt.add(ref, part, value, {"1": a, "2": b})

    # ---------------- 12 V input: jack, reverse diode, TVS, fuse, reserve ----------------
    ckt.add("J1", JACK, "12V", {"1": "VIN_JACK", "2": GND, "3": GND})
    ckt.add("D1", DSS34, "SS34", {"1": "VIN_RAW", "2": "VIN_JACK"})  # 1 = K, 2 = A
    ckt.add("D2", DTVS, "SMBJ15A", {"1": GND, "2": "VIN_RAW"})
    ckt.add("F1", FUSE, "1A", {"1": "VIN_RAW", "2": "VIN"})
    ckt.add("C1", CP, "100u/25V", {"1": "VIN", "2": GND})  # pulse reserve, as on the brain
    c("C2", "10u/25V", "VIN", GND, part=C1206)
    c("C3", "100n", "VIN", GND)

    # ---------------- 5 V buck for the LEDs (the brain's block, VBAT -> VIN) ----------------
    ckt.add(
        "U1",
        BUCK3A,
        "TPS62130",
        pins_by_name(
            BUCK3A,
            {
                "SW": "SW",
                "PG": "BUCK_PG",
                "FB": "BUCK_FB",
                "GND": GND,
                "FSW": GND,
                "DEF": "5V",
                "SS/TR": "BUCK_SS",
                "VIN": "VIN",
                "EN": "BUCK_EN",
                "VOS": "5V",
            },
        ),
    )
    r("R1", "100k", "BUCK_EN", "VIN")
    c("C4", "3n3", "BUCK_SS", GND)
    r("R2", "100k", "BUCK_PG", "5V")
    ckt.add("L1", LBUCK, "2u2", {"1": "SW", "2": "5V"})
    r("R3", "523k", "5V", "BUCK_FB")
    r("R4", "100k", "BUCK_FB", GND)
    c("C5", "22u/10V", "5V", GND, part=C1206)
    c("C6", "22u/10V", "5V", GND, part=C1206)
    ckt.add("F2", FUSE, "2A", {"1": "5V", "2": "5V_LED"})
    ckt.add("C7", CP, "100u/10V", {"1": "5V_LED", "2": GND})

    # ---------------- 5VA analog island: LDO, or the buck through JP1 for M8 ----------------
    ckt.add(
        "U2", LDO, "LP2985-5.0", {"1": "VIN", "2": GND, "3": "VIN", "4": "LDO_BP", "5": "5VA_LDO"}
    )
    c("C8", "10n", "LDO_BP", GND)
    c("C9", "2u2", "5VA_LDO", GND)
    ckt.add("JP1", H1X03, "5VA: 1 LDO / 3 BUCK", {"1": "5VA_LDO", "2": "5VA_RAW", "3": "5V"})
    ckt.add("FB1", FB, "BLM21PG221", {"1": "5VA_RAW", "2": "5VA"})
    c("C10", "10u/10V", "5VA", GND, part=C1206)
    c("C11", "100n", "5VA", GND)

    # ---------------- LED buffer and the quadrant link ----------------
    ckt.add(
        "U3",
        BUF5,
        "74AHCT1G125",
        {"1": GND, "2": "LED_DIN_MCU", "3": GND, "4": "LED_DINB", "5": "5V"},
    )
    r("R5", "470R", "LED_DINB", "LED_DIN1")
    c("C12", "100n", "5V", GND)
    nets = link_pinout(cfg, 1, "LED_DIN1", "LED_END")
    ckt.add("J2", FPC16, "QUADRANT", {str(i + 1): n for i, n in enumerate(nets)})
    r("R6", "49R9", "AMP_OUT1", "ADC1")  # the brain's RC in front of the converter
    c("C13", "1n", "ADC1", GND)
    c("C14", "100n", "3V3", GND)

    # ---------------- Nucleo connectors ----------------
    for ref, (title, part, _labels) in HEADERS.items():
        pins, nc = header_nets(cfg, ref)
        ckt.add(ref, part, title, pins, nc=nc)

    # ---------------- test points (the bus is probed on the Nucleo Morpho pins) ----------------
    points = (
        ("TP1", "LED_END"),
        ("TP2", "5VA"),
        ("TP3", "5V"),
        ("TP4", "3V3"),
        ("TP5", GND),
        ("TP6", "VIN"),
        ("TP7", "ADC1"),
    )
    for ref, net in points:
        ckt.add(ref, TP, net, {"1": net})
    return ckt


SPEC = Spec(
    name="bench",
    title="Damier LC, banc Nucleo",
    width=80.0,
    height=56.0,
    layers=2,
    clearance=0.15,
    track=0.3,
    power_track=0.6,
    via_pad=0.8,
    via_drill=0.4,
    gnd_layer="B.Cu",
    power_nets=(
        "VIN_JACK",
        "VIN_RAW",
        "VIN",
        "5V",
        "5V_LED",
        "5VA_LDO",
        "5VA_RAW",
        "5VA",
        "3V3",
        "SW",
    ),
)


def header_placements() -> dict[str, tuple[float, float, float]]:
    """Pin 1 of every row on the Uno footprint's pad, the row running the
    way the Uno runs it (rotation 90 lays a vertical header along +x)."""
    uno = load_footprint(UNO_FOOTPRINT)
    pads = {p.number: (p.dx, p.dy) for p in uno.pads}
    ox, oy = UNO_OFFSET
    out = {}
    for ref, (pad, direction) in UNO_ROW_ORIGIN.items():
        px, py = pads[pad]
        out[ref] = (round(ox + px, 3), round(oy + py, 3), 90.0 if direction > 0 else 270.0)
    return out


def bench_placements(ckt: Circuit) -> dict[str, tuple[float, float, float]]:
    """Floor plan: the Uno rows north and south; the jack north-east and
    the FPC link south-east (cable leaving south), its fine pads facing
    the free east strip so the sixteen escapes fan out there; the LED
    buffer in that strip by the jack; the 12 V input and the analog
    island in the centre column next to the link; the buck in the west
    column, where the Uno pattern leaves the shield empty."""
    out: dict[str, tuple[float, float, float]] = {}
    out.update(header_placements())
    out["J1"] = (66.0, 13.5, 180.0)  # plug from the east
    out["J2"] = (72.75, 50.5, 0.0)  # cable leaves south, pads face north
    # east strip: LED buffer and the LED_END test point under the jack
    out.update(shelf(["U3", "R5", "C12", "TP1"], ckt, 64.0, 79.5, 20.0, upright=True))
    # centre column: ADC filter under A0, 12 V input under the jack, analog island by the link
    out.update(shelf(["R6", "C13", "TP7"], ckt, 44.0, 63.0, 8.0, upright=True))
    out.update(shelf(["C1", "D2", "D1"], ckt, 40.0, 63.0, 12.5, upright=True))
    out.update(shelf(["F1", "C2", "C3", "TP6"], ckt, 40.0, 63.0, 24.5, upright=True))
    out.update(shelf(["U2", "C8", "C9", "JP1", "FB1", "C10"], ckt, 40.0, 63.5, 32.0, upright=True))
    out.update(shelf(["C11", "TP2"], ckt, 40.0, 63.0, 43.0, upright=True))
    # west column: the buck and the LED rail, then the 3.3 V decoupling and rail test points
    out.update(shelf(["L1", "U1", "C5", "C6", "C4", "F2"], ckt, 4.0, 38.0, 9.0, upright=True))
    out.update(shelf(["C7", "R1", "R2", "R3", "R4", "TP3"], ckt, 4.0, 38.0, 18.0, upright=True))
    out.update(shelf(["C14", "TP4", "TP5"], ckt, 4.0, 38.0, 30.0, upright=True))
    return out


def build_bench(cfg: BoardConfig):
    ckt = build_bench_circuit(cfg)
    if (
        tuple(cfg.bench.shield.board_mm) != (SPEC.width, SPEC.height)
        or cfg.bench.shield.layers != SPEC.layers
    ):
        raise ValueError("bench.shield.board_mm / layers disagree with boardgen.bench.SPEC")
    gb = GenericBoard(SPEC, ckt, bench_placements(ckt), generator="boardgen")
    gb.place_all()
    gb.route_all()
    return gb.finish(
        texts=[
            ("DAMIER LC / BANC NUCLEO", 20.0, 40.0, "F.SilkS", 1.5),
            ("embases males vers le bas, Nucleo dessous", 20.0, 43.0, "F.SilkS", 1.0),
        ]
    )


def schematic_groups() -> list[tuple[str, float, list[str]]]:
    return [
        ("12 V INPUT", 40.0, ["J1", "D1", "D2", "F1", "C1", "C2", "C3"]),
        (
            "5 V BUCK, LED RAIL",
            100.0,
            ["U1", "R1", "C4", "R2", "L1", "R3", "R4", "C5", "C6", "F2", "C7"],
        ),
        ("5VA ANALOG ISLAND", 170.0, ["U2", "C8", "C9", "JP1", "FB1", "C10", "C11"]),
        ("QUADRANT LINK", 230.0, ["U3", "R5", "C12", "J2", "R6", "C13", "C14"]),
        ("NUCLEO", 300.0, ["J3", "J4", "J5", "J6"]),
        (
            "TEST POINTS",
            360.0,
            ["TP1", "TP2", "TP3", "TP4", "TP5", "TP6", "TP7"],
        ),
    ]
