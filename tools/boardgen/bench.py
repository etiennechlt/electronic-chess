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
from quadgen.escape import FANOUT_VIA_DRILL_MM, FANOUT_VIA_PAD_MM, STUB_BEYOND_MM, STUB_WIDTH_MM

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
    out.update(shelf(["U3", "R5", "C12"], ckt, 64.0, 79.5, 20.0, upright=True))
    out["TP1"] = (78.5, 40.0, 0.0)  # LED_END, by the FPC: its lane reaches it from the fan
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


# The FPC row is fanned out by hand (no fanout via in the ground pour):
BOARD_OPTIONS = {"plain_fanout": ("J2",)}
FAN_PITCH_MM = 0.6  # lane pitch of the fans: 0.3 mm tracks, 0.3 mm apart
FAN_STAGGER_MM = 1.2  # a lane ends this much past the one below: room for a via at its end
FAN_GND_VIA_MM = 47.4  # the ground pins drop to the pour at their runway end
FAN_VIA_ROWS_MM = (46.9, 46.2)  # the fanout via rows of the escape module, past the stubs
# west fan on the top layer: pin, first lane, first lane end
FAN_WEST = ((2, 4, 5, 10), 46.8, 66.0)
# east fan on the top layer, then north along the east strip
FAN_EAST = ((14, 13, 12, 11), 45.6, 78.2)
FAN_EAST_PITCH_MM = 0.75  # a via fits at every lane end
# south fan on the back layer, under the connector, to the digital header
FAN_SOUTH = ((6, 8, 9, 15), 49.8, 66.2, 53.4)
FAN_SOUTH_ROW = {6: 0, 8: 0, 9: 1, 15: 0}  # via row of each pin
J4_ROW_Y_MM = 2.4  # a lane north of the analog header pads, above the row
VIN_LANE_Y_MM = 30.0  # VIN crosses the board on the back, between the link and the input
LED_DIN1_UP_MM = 32.0  # LED_DIN1 comes back to the top layer here, under the VIN lane
U1_5V_EXIT_MM = 2.15  # the 5 V pad of the north side leaves along its corridor


def hand_routes(gb: GenericBoard) -> None:
    """Escapes the router cannot find, drawn before it runs (seeds); the
    router starts from them and finishes every net. What a human draws in
    pcbnew, kept in the generator so every build redraws and checks it.

    J2, sixteen FPC pads at 0.5 mm facing north. Every pin leaves its
    stub on a 0.2 mm column. West pins turn into 0.3 mm lanes heading
    west, the outermost first and the next a lane higher, so no lane
    crosses a column; the lanes end staggered so a via fits past each
    end. The pins bound for the digital header get a small via at the
    fanout rows and run south on the back layer, under the connector,
    then along the board edge below the header into their pads; VIN and
    LED_DIN1 likewise north. The pins bound for the analog header and
    the test point fan out east, then north along the east strip:
    MUX_EN_L along the pad row into the last pin, MUX_EN_H above the row
    on the top layer, PULSE_EN on the back layer (the two would cross
    otherwise), LED_END into its test point by the connector. The ground
    pins drop to the pour at their runway end.

    The long links the router loses once the rest is routed, on the top
    layer so the pour stays whole: 3V3 up west of C9, under the headers
    into J3, then west and down between C6 and R3 to its test point and
    capacitor; 5V_LED and AMP_OUT1 one lane lower each, to the LED fuse
    and the ADC filter (5V_LED hops to the back layer past the 3V3
    rise); VIN across the board on the back layer to its test point.

    U1, the QFN of the buck: a 0.2 mm bar across the stub ends ties the
    three SW pads, another the three VIN pads (the wide power track the
    router draws along a runway brushes the neighbouring stub). SW leaves
    from its fanout via on the back layer to the inductor, VIN from its
    fanout via east to a via by C4 and on to the input capacitor, the
    5 V pad of the north side along its exit corridor, thin where it
    passes the fanout vias; the ground pins are bridged to the thermal
    pad. U2: its two VIN pins tied around the ground pin, LDO_BP around
    the bead to its capacitor. The ground pads of U2 and R4, walled in
    by their neighbours, get a short stub and a small via to the pour.
    """
    pads = {(p.ref, p.number): p for p in gb.res.pads}
    thin, lane, back = STUB_WIDTH_MM, gb.spec.track, gb.spec.gnd_layer
    small = (FANOUT_VIA_PAD_MM, FANOUT_VIA_DRILL_MM)

    def T(net, layer, pts, width):
        gb.seed(net, layer, [(round(x, 3), round(y, 3)) for x, y in pts], width)

    def V(net, x, y, size=None):
        gb.seed_via(net, round(x, 3), round(y, 3), *(size or (None, None)))

    # ---- J2 fans
    j2 = {int(p.number): p for (ref, _n), p in pads.items() if ref == "J2" and p.number.isdigit()}
    top = {k: p.y - (p.h / 2.0 + STUB_BEYOND_MM) for k, p in j2.items()}  # stub ends
    for k, p in j2.items():
        if p.net == GND:
            T(GND, "F.Cu", [(p.x, top[k]), (p.x, FAN_GND_VIA_MM)], thin)
            V(GND, p.x, FAN_GND_VIA_MM, small)
    ends = {}  # lane end of every fanned pin, by net
    pins, y0, x0 = FAN_WEST
    for i, k in enumerate(pins):
        p, y = j2[k], y0 - FAN_PITCH_MM * i
        T(p.net, "F.Cu", [(p.x, top[k]), (p.x, y)], thin)
        T(p.net, "F.Cu", [(p.x, y), (x0 - FAN_STAGGER_MM * i, y)], lane)
        ends[p.net] = (x0 - FAN_STAGGER_MM * i, y)
    pins, y0, x_turn0, y_low0 = FAN_SOUTH
    header = {p.net: p for (ref, _n), p in pads.items() if ref == "J5"}
    for i, k in enumerate(pins):
        p = j2[k]
        y_via = FAN_VIA_ROWS_MM[FAN_SOUTH_ROW[k]]
        y_lane, x_turn, y_low = (v + FAN_PITCH_MM * i for v in (y0, x_turn0, y_low0))
        T(p.net, "F.Cu", [(p.x, top[k]), (p.x, y_via)], thin)
        V(p.net, p.x, y_via, small)
        T(p.net, back, [(p.x, y_via), (p.x, y_lane)], thin)
        h = header[p.net]
        T(
            p.net,
            back,
            [(p.x, y_lane), (x_turn, y_lane), (x_turn, y_low), (h.x, y_low), (h.x, h.y)],
            lane,
        )
    p16 = j2[16]  # VIN: a small via at the second row, north then west on the back
    T(p16.net, "F.Cu", [(p16.x, top[16]), (p16.x, FAN_VIA_ROWS_MM[1])], thin)
    V(p16.net, p16.x, FAN_VIA_ROWS_MM[1], small)
    tp6 = pads[("TP6", "1")]  # layer to its test point, by the input filter
    x_tp6 = round(tp6.x + 1.0, 3)
    T(
        p16.net,
        back,
        [(p16.x, FAN_VIA_ROWS_MM[1]), (p16.x, VIN_LANE_Y_MM), (x_tp6, VIN_LANE_Y_MM)],
        0.4,
    )
    V(p16.net, x_tp6, VIN_LANE_Y_MM)
    T(p16.net, "F.Cu", [(x_tp6, VIN_LANE_Y_MM), (tp6.x, tp6.y + 0.4)], 0.4)
    p7 = j2[7]  # LED_DIN1: a small via at the second row, north on the back layer,
    # then on the top layer past C12 into R5 (the west lanes cross its column)
    T(p7.net, "F.Cu", [(p7.x, top[7]), (p7.x, FAN_VIA_ROWS_MM[1])], thin)
    V(p7.net, p7.x, FAN_VIA_ROWS_MM[1], small)
    T(p7.net, back, [(p7.x, FAN_VIA_ROWS_MM[1]), (p7.x, LED_DIN1_UP_MM)], lane)
    V(p7.net, p7.x, LED_DIN1_UP_MM)
    r5 = pads[("R5", "2")]
    x_r5 = round(r5.x + r5.h / 2.0 + 1.0, 3)  # between R5 and C12
    T(
        p7.net,
        "F.Cu",
        [
            (p7.x, LED_DIN1_UP_MM),
            (p7.x, 26.0),
            (x_r5, 26.0 - (p7.x - x_r5)),
            (x_r5, r5.y),
            (r5.x, r5.y),
        ],
        lane,
    )
    pins, y0, x0 = FAN_EAST
    for i, k in enumerate(pins):
        p, y, x_end = j2[k], y0 - FAN_EAST_PITCH_MM * i, x0 - FAN_PITCH_MM * i
        T(p.net, "F.Cu", [(p.x, top[k]), (p.x, y)], thin)
        T(p.net, "F.Cu", [(p.x, y), (x_end, y)], lane)
        ends[p.net] = (x_end, y)
    analog = {p.net: p for (ref, _n), p in pads.items() if ref == "J4"}
    x, y = ends["PULSE_EN"]  # back layer along the east edge, above the row, into its pin
    V("PULSE_EN", x, y)
    h = analog["PULSE_EN"]
    T(
        "PULSE_EN",
        back,
        [(x, y), (x + 0.3, y - 0.3), (x + 0.3, J4_ROW_Y_MM), (h.x, J4_ROW_Y_MM), (h.x, h.y)],
        lane,
    )
    x, y = ends["MUX_EN_H"]
    h = analog["MUX_EN_H"]
    T("MUX_EN_H", "F.Cu", [(x, y), (x, J4_ROW_Y_MM), (h.x, J4_ROW_Y_MM), (h.x, h.y)], lane)
    x, y = ends["MUX_EN_L"]
    h = analog["MUX_EN_L"]  # the last pin of the row, entered along the row
    T("MUX_EN_L", "F.Cu", [(x, y), (x, h.y), (h.x, h.y)], lane)
    x, y = ends["LED_END"]
    tp = pads[("TP1", "1")]
    T("LED_END", "F.Cu", [(x, y), (x, tp.y + 1.5), (tp.x, tp.y + 0.6)], lane)
    # ---- U1, the buck
    sw = [pads[("U1", n)] for n in ("1", "2", "3")]  # west side, stubs run west
    x_bar = round(sw[0].x - sw[0].w / 2.0 - STUB_BEYOND_MM + 0.09, 3)  # on the stub end caps
    T("SW", "F.Cu", [(x_bar, sw[0].y), (x_bar, sw[-1].y)], thin)
    sw_via = (round(x_bar - 0.09 - 1.5, 3), sw[-1].y)  # fanout via of pad 3 (runway 1.5 mm)
    inductor = pads[("L1", "1")]
    y_sw = 13.25  # between the 5 V and the LED rail the router lays on the back
    x_up = round(inductor.x + inductor.h / 2.0 + 1.3, 3)  # a via east of the inductor pad
    T("SW", back, [sw_via, (sw_via[0] - 0.6, y_sw), (x_up, y_sw)], 0.4)
    V("SW", x_up, y_sw)
    T("SW", "F.Cu", [(x_up, y_sw), (inductor.x + inductor.h / 2.0 - 0.2, y_sw)], 0.4)
    vin = [pads[("U1", n)] for n in ("10", "11", "12")]  # east side, stubs run east
    x_bar = round(vin[0].x + vin[0].w / 2.0 + STUB_BEYOND_MM - 0.09, 3)
    T("VIN", "F.Cu", [(x_bar, vin[-1].y), (x_bar, vin[0].y)], thin)
    vin_via = (round(x_bar + 0.09 + 0.8, 3), vin[-1].y)  # fanout via of pad 12 (runway 0.8 mm)
    c4 = pads[("C4", "2")]
    x_out = round(c4.x + c4.h / 2.0 + 0.9, 3)  # east of C4
    T("VIN", back, [vin_via, (x_out, vin_via[1])], 0.4)
    V("VIN", x_out, vin_via[1])
    c1 = pads[("C1", "1")]  # then to the input capacitor, along its north edge
    y_c1 = round(c1.y - c1.w / 2.0, 3)
    T(
        "VIN",
        "F.Cu",
        [(x_out, vin_via[1]), (x_out, y_c1), (c1.x, y_c1), (c1.x, c1.y)],
        gb.spec.power_track,
    )
    p14 = pads[("U1", "14")]  # north side, stub runs north, via 0.8 mm past the stub
    v14 = (p14.x, round(p14.y - p14.h / 2.0 - STUB_BEYOND_MM - 0.8, 3))
    y_top = round(v14[1] - U1_5V_EXIT_MM, 3)
    T("5V", back, [v14, (v14[0], y_top)], thin)
    T("5V", back, [(v14[0], y_top), (v14[0] - 5.0, y_top)], 0.4)
    # ---- VIN: the two input pins of the LDO, either side of its ground pin,
    # tied by a bar south of the package
    u2_1, u2_3 = pads[("U2", "1")], pads[("U2", "3")]
    y_bar = round(u2_1.y + u2_1.w / 2.0 + 0.85, 3)
    T("VIN", "F.Cu", [(u2_1.x, u2_1.y), (u2_1.x, y_bar), (u2_3.x, y_bar), (u2_3.x, u2_3.y)], 0.4)
    # ---- 3V3: from its lane end north between C9 and the input diodes, then
    # under the analog header into J3, and west under the analog island to
    # its test point and its capacitor
    x_3v3, y_3v3 = ends["3V3"]
    c9 = pads[("C9", "1")]
    x_up = round(c9.x - c9.h / 2.0 - 0.6, 3)
    j3 = pads[("J3", "4")]
    y_row = round(j3.y + j3.h / 2.0 + 1.3, 3)
    T(
        "3V3",
        "F.Cu",
        [(x_3v3, y_3v3), (x_up, y_3v3), (x_up, y_row), (j3.x, y_row), (j3.x, j3.y)],
        lane,
    )
    tp4, c14, tp5 = pads[("TP4", "1")], pads[("C14", "1")], pads[("TP5", "1")]
    c6 = pads[("C6", "2")]
    x_west = round(c6.x + c6.h / 2.0 + 0.55, 3)  # down between C6 and R3
    y_tp = round(tp5.y + tp5.h / 2.0 + 0.75, 3)  # below the ground test point
    T(
        "3V3",
        "F.Cu",
        [(j3.x, y_row), (x_west, y_row), (x_west, y_tp), (tp4.x, y_tp), (tp4.x, tp4.y)],
        lane,
    )
    T("3V3", "F.Cu", [(tp4.x, y_tp), (c14.x, y_tp), (c14.x, c14.y)], lane)
    # ---- 5V_LED and AMP_OUT1: from their lane ends north along the link side
    # of the board, then west under the headers (5V_LED to the LED fuse, the
    # analog signal to its filter), on the top layer: the ground pour under
    # the analog header stays whole
    x_led, y_led = ends["5V_LED"]
    x_led_up = round(c9.x + c9.h / 2.0 + 0.6, 3)  # east of C9
    y_led_row = round(y_row + 0.78, 3)
    wide = gb.spec.power_track
    # the 3V3 rise stands between the LED rail and its fuse: a hop on the back
    x_hop = (round(x_up + 0.85, 3), round(x_up - 1.55, 3))
    T(
        "5V_LED",
        "F.Cu",
        [(x_led, y_led), (x_led_up, y_led), (x_led_up, y_led_row), (x_hop[0], y_led_row)],
        wide,
    )
    V("5V_LED", x_hop[0], y_led_row)
    T("5V_LED", back, [(x_hop[0], y_led_row), (x_hop[1], y_led_row)], wide)
    V("5V_LED", x_hop[1], y_led_row)
    f2 = pads[("F2", "2")]
    T("5V_LED", "F.Cu", [(x_hop[1], y_led_row), (f2.x, y_led_row), (f2.x, f2.y)], wide)
    x_amp, y_amp = ends["AMP_OUT1"]  # its lane lies under the 3V3 lane: west of the 3V3 rise
    x_amp_up = round(x_up - 0.6, 3)
    y_amp_row = round(y_led_row + 0.8, 3)
    r6 = pads[("R6", "1")]
    x_r6 = round(r6.x - r6.h / 2.0 - 0.7, 3)  # west of R6, past its ADC pad
    T(
        "AMP_OUT1",
        "F.Cu",
        [
            (x_amp, y_amp),
            (x_amp_up, y_amp),
            (x_amp_up, y_amp_row),
            (x_r6, y_amp_row),
            (x_r6, r6.y),
            (r6.x, r6.y),
        ],
        lane,
    )
    # ---- LDO_BP: the bypass pin of the LDO to its capacitor, around the bead
    u2_4, c8 = pads[("U2", "4")], pads[("C8", "1")]
    fb1 = pads[("FB1", "1")]
    y_over = round(pads[("FB1", "2")].y - pads[("FB1", "2")].h / 2.0 - 0.5, 3)
    x_pass = round(fb1.x + fb1.h / 2.0 + 0.7, 3)
    y_under = round(c8.y + c8.h / 2.0 + 0.7, 3)
    T(
        "LDO_BP",
        "F.Cu",
        [
            (u2_4.x, u2_4.y),
            (u2_4.x, y_over),
            (x_pass, y_over),
            (x_pass, y_under),
            (c8.x, y_under),
            (c8.x, c8.y),
        ],
        lane,
    )
    # ---- the ground pins of the QFN reach its thermal pad by a short bridge
    # (their fanout vias sit in pockets the buck's tracks cut out of the pour)
    ep = pads[("U1", "17")]
    for num in ("6", "7", "15", "16"):
        p = pads[("U1", num)]
        T(GND, "F.Cu", [(p.x, p.y), (p.x, ep.y)], thin)
    # ---- ground pads walled in by their neighbours
    for ref, num, dy in (("U2", "2", -1.15), ("R4", "2", -1.05)):
        p = pads[(ref, num)]
        T(GND, "F.Cu", [(p.x, p.y), (p.x, p.y + dy)], thin)
        V(GND, p.x, p.y + dy, small)


def build_bench(cfg: BoardConfig):
    ckt = build_bench_circuit(cfg)
    if (
        tuple(cfg.bench.shield.board_mm) != (SPEC.width, SPEC.height)
        or cfg.bench.shield.layers != SPEC.layers
    ):
        raise ValueError("bench.shield.board_mm / layers disagree with boardgen.bench.SPEC")
    gb = GenericBoard(SPEC, ckt, bench_placements(ckt), generator="boardgen", **BOARD_OPTIONS)
    gb.place_all()
    hand_routes(gb)
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
