"""The Hall plus RFID technology demonstrator (`hallrfid-demo`, note 27):
one row of two squares at the mockup pitch, each with a square NFC loop
drawn on the board, an MFRC522 reader with its matching network in the
strip under the loop, analog Hall sensors inside the loop openings (one
at the centre of each square, four more around the centre of A1), a
CD74HC4067 multiplexer, an ESP32-S3-WROOM-1 module with native USB, a
3.3 V linear regulator, and the measurement fittings of note 25: TVDD
sense resistors, test points, U.FL footprints and 0 ohm isolators for
the NanoVNA, a MISO buffer with its bypass, a switched sensor rail with
its bypass jumper, an escape header for a DevKitC.

100 x 100 mm, two layers: the play area (y < p) carries the loops and
the sensors, no ground; the strip past it carries everything else over
a ground pour that starts the ground keepout past the loops. Geometry
from chessboard_calc.hallrfid_demo, values from the matching model
(chessboard_calc.nfc) and the yaml; the drawing of a loop from
boardgen.nfcloop.
"""

from __future__ import annotations

from analoggen.circuit import FP_C0603, FP_R0603, PFET, TP, Circuit, Part
from analoggen.fplib import load_footprint
from analoggen.symlib import load_symbol

from chessboard_calc import nfc
from chessboard_calc.config import BoardConfig
from chessboard_calc.hallrfid_demo import DemoLayout, layout

from .brain import (
    ESD,
    ESP32,
    ESP32_ANTENNA_FROM,
    ESP32_ANTENNA_TO,
    ESP32_HALF,
    H1X03,
    H2X10,
    LDO33_1A,
    LED,
    SW,
    USBC,
)
from .core import GenericBoard, Spec, pins_by_name, shelf
from .nfcloop import LoopDrawing, router_blocks, seed_loop, square_loop

GND = "GND"

# ------------------------------------------------------------ parts
# LCSC codes of the basic passives (JLCPCB assembly): checked in the order
# preview on order day, like every code of the repository (note 23, 5)
R_CODES = {"10k": "C25804", "1k": "C21190", "0R": "C21189", "5k1": "C23186"}
C_CODES = {
    "100n": "C14663",
    "10n": "C57112",
    "1u": "C15849",
    "15p": "C1644",
    "1n": "C1588",
    "220p": "C1653",
}


def r_part(value: str) -> Part:
    return Part("Device", "R", FP_R0603, lcsc=R_CODES.get(value, ""))


def c_part(value: str) -> Part:
    return Part("Device", "C", FP_C0603, lcsc=C_CODES.get(value, ""))


C10U = Part("Device", "C", "Capacitor_SMD:C_1206_3216Metric", lcsc="C13585")
CTANT = Part(
    "Device",
    "C_Polarized_US",
    "Capacitor_Tantalum_SMD:CP_EIA-3528-21_Kemet-B",
    mpn="TAJB226K010RNJ",
)
MUX16 = Part("74xx", "CD74HC4067SM", "Package_SO:SSOP-24_5.3x8.2mm_P0.65mm")
BUF4 = Part(
    "74xx", "74LVC125", "Package_SO:TSSOP-14_4.4x5mm_P0.65mm", mpn="74LVC125APW,118", lcsc="C6059"
)
XTAL = Part(
    "Device",
    "Crystal_GND24",
    "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm",
    mpn="X32252712MMB4SI",
    lcsc="C29975",
)
L0805 = Part("Device", "L", "Inductor_SMD:L_0805_2012Metric", mpn="FHW0805UCR56JGT", lcsc="C139264")
UFL = Part(
    "Connector",
    "Conn_Coaxial",
    "Connector_Coaxial:U.FL_Hirose_U.FL-R-SMT-1_Vertical",
    mpn="U.FL-R-SMT-1(10)",
)
JP_BRIDGED = Part(
    "Jumper", "SolderJumper_2_Bridged", "Jumper:SolderJumper-2_P1.3mm_Bridged_Pad1.0x1.5mm"
)
JP_OPEN = Part("Jumper", "SolderJumper_2_Open", "Jumper:SolderJumper-2_P1.3mm_Open_Pad1.0x1.5mm")
LOOP = Part("Device", "L", "hallrfid:NetTie_NFC_Loop")
H1X02 = Part(
    "Connector_Generic", "Conn_01x02", "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical"
)
H1X06 = Part(
    "Connector_Generic", "Conn_01x06", "Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical"
)
FIDUCIAL_FP = "Fiducial:Fiducial_1mm_Mask2mm"

# the ESP32 module keeps its body courtyard only; the antenna end sits on
# the board edge and gets a copper keepout instead of the library's wide
# clearance area (the clock board does the same)
ESP32_DEMO_COURTYARD = (-9.75, -12.95, 9.75, 13.45)
BOARD_OPTIONS = {"overhang": ("J1",), "courtyards": {"U4": ESP32_DEMO_COURTYARD}}

READER_ROT = 180.0  # TX1 and TX2 face the loop: the HVQFN32 pins 9 to 16 run along the north edge


def reader_part(cfg: BoardConfig) -> Part:
    rd = cfg.hall_rfid.demo.reader
    return Part(
        "hallrfid",
        "MFRC522",
        "Package_DFN_QFN:HVQFN-32-1EP_5x5mm_P0.5mm_EP3.1x3.1mm",
        mpn=rd.mpn,
        lcsc=rd.lcsc,
    )


def hall_part(cfg: BoardConfig) -> Part:
    sensor = cfg.hall_rfid.sensor(cfg.hall_rfid.mockup.hall.sensor)
    return Part(
        "Sensor_Magnetic",
        "DRV5055A3xDBZxQ1",
        "Package_TO_SOT_SMD:SOT-23",
        mpn=sensor.mpn,
        lcsc=sensor.lcsc or "",
    )


def mux_part(cfg: BoardConfig) -> Part:
    mux = cfg.hall_rfid.mux
    return Part(MUX16.lib, MUX16.symbol, MUX16.footprint, mpn=mux.mpn, lcsc=mux.lcsc)


def regulator_part(cfg: BoardConfig) -> Part:
    reg = cfg.hall_rfid.mockup.power.regulator
    return Part(LDO33_1A.lib, LDO33_1A.symbol, LDO33_1A.footprint, mpn=reg.part, lcsc=reg.lcsc)


# ------------------------------------------------------------ values
def fmt_r(ohm: float) -> str:
    """Resistor value the way the other boards write it: 0R68, 1R, 3k9, 10k."""
    if ohm >= 1e3:
        v = ohm / 1e3
        return f"{int(v)}k" if v == int(v) else f"{v:.1f}".replace(".", "k")
    if ohm >= 1.0:
        return f"{ohm:g}R" if ohm == int(ohm) else f"{ohm:.2f}".replace(".", "R").rstrip("0")
    return f"0R{ohm:.2f}".replace("0R0.", "0R").replace("0R.", "0R")[:5].rstrip("0")


def fmt_c(pf: float) -> str:
    """Capacitor value: 5p6, 56p, 220p, 1n, 10n, 100n, 1u."""
    if pf >= 1e6:
        return f"{pf / 1e6:g}u"
    if pf >= 1e3:
        v = pf / 1e3
        return f"{v:g}n" if v == int(v) else f"{v:.1f}".replace(".", "n")
    return f"{pf:g}p" if pf == int(pf) else f"{pf:.1f}".replace(".", "p")


def fmt_l(nh: float) -> str:
    return f"{nh:g}n" if nh < 1e3 else f"{nh / 1e3:g}u"


class ReaderValues:
    """The matching, receive and sense values of one reader, from the model."""

    def __init__(self, cfg: BoardConfig, lay: DemoLayout, square: str) -> None:
        lp = lay.loop(square)
        mt = nfc.matching(cfg, lay.pitch_mm, lp.kind, cfg.hall_rfid.mockup.matching.tune_tag)
        self.rq = fmt_r(mt.rq_ohm)
        self.l0 = fmt_l(mt.l0_nH)
        self.c0 = fmt_c(mt.c0_pF)
        self.c1_main, self.c1_trim = (fmt_c(v) for v in mt.c1_pF)
        self.c2_main, self.c2_trim = (fmt_c(v) for v in mt.c2_pF)
        self.r1 = fmt_r(mt.r1_ohm)
        self.r2 = fmt_r(mt.r2_ohm)
        self.r_sense = fmt_r(cfg.hall_rfid.mockup.reader.r_sense_ohm)
        self.c_rx = fmt_c(cfg.hall_rfid.mockup.matching.rx_coupling_nF * 1e3)
        self.loop_kind = lp.kind


# ------------------------------------------------------------ circuit
def signal_nets(cfg: BoardConfig) -> dict[str, str]:
    """Signal name of the yaml pin map -> net name on the board."""
    return {sig: sig for sig in cfg.hall_rfid.demo.esp32.pins}


def build_hallrfid_circuit(cfg: BoardConfig) -> Circuit:
    dm = cfg.hall_rfid.demo
    mk = cfg.hall_rfid.mockup
    lay = layout(cfg)
    ckt = Circuit()

    def r(ref, value, a, b, dnp=False):
        ckt.add(ref, r_part(value), value, {"1": a, "2": b}, dnp=dnp)

    def c(ref, value, a, b, part=None, dnp=False):
        ckt.add(ref, part or c_part(value), value, {"1": a, "2": b}, dnp=dnp)

    # ---------------- USB-C, protection, bench supply pads, 3.3 V regulator ----------------
    usb_pins = pins_by_name(
        USBC,
        {
            "GND": GND,
            "SHIELD": GND,
            "VBUS": "VBUS",
            "CC1": "CC1",
            "CC2": "CC2",
            "D+": "USB_DP_C",
            "D-": "USB_DM_C",
        },
    )
    usb_all = {p.number for p in load_symbol(USBC.lib, USBC.symbol).pins}
    ckt.add("J1", USBC, "USB-C", usb_pins, nc=tuple(sorted(usb_all - set(usb_pins))))
    r("R61", "5k1", "CC1", GND)
    r("R62", "5k1", "CC2", GND)
    ckt.add(
        "U5",
        ESD,
        "USBLC6-2",
        {"1": "USB_DM_C", "6": "USB_DM", "3": "USB_DP_C", "4": "USB_DP", "5": "VBUS", "2": GND},
    )
    ckt.add("J2", H1X02, "5V BENCH", {"1": "VBUS", "2": GND})
    ckt.add("U6", regulator_part(cfg), mk.power.regulator.part, {"1": GND, "2": "3V3", "3": "VBUS"})
    c("C61", "10u/25V", "VBUS", GND, part=C10U)
    ckt.add("C62", CTANT, "22u/10V tantale", {"1": "3V3", "2": GND})
    c("C63", "100n", "3V3", GND)

    # ---------------- ESP32-S3 module, its buttons, LED, console test points ----------------
    esp_map = {"GND": GND, "3V3": "3V3", "EN": "ESP_EN", "IO0": "ESP_IO0"}
    for sig, gpio in dm.esp32.pins.items():
        name = {43: "TXD0", 44: "RXD0"}.get(gpio, f"IO{gpio}")
        esp_map[name] = sig
    esp_pins = pins_by_name(ESP32, esp_map)
    esp_all = {p.number for p in load_symbol(ESP32.lib, ESP32.symbol).pins}
    ckt.add("U4", ESP32, mk.esp32.module, esp_pins, nc=tuple(sorted(esp_all - set(esp_pins))))
    c("C51", "10u/25V", "3V3", GND, part=C10U)
    c("C52", "100n", "3V3", GND)
    r("R51", "10k", "ESP_EN", "3V3")
    c("C53", "1u", "ESP_EN", GND)
    r("R52", "10k", "ESP_IO0", "3V3")
    ckt.add("SW1", SW, "BOOT", {"1": "ESP_IO0", "2": GND})
    ckt.add("SW2", SW, "EN", {"1": "ESP_EN", "2": GND})
    r("R53", "1k", "LED", "LED_A")
    ckt.add("D1", LED, "LED", {"1": GND, "2": "LED_A"})  # 1 = K, 2 = A
    r("R71", "10k", "RFID_IRQ", "3V3")

    # ---------------- Hall sensors: one per square centre, four around the centre of A1 ----
    hall = hall_part(cfg)
    sensor = cfg.hall_rfid.sensor(mk.hall.sensor)
    r_filter = fmt_r(mk.hall.filter_r_ohm)
    c_filter = fmt_c(mk.hall.filter_c_nF * 1e3)
    c_dec = fmt_c(mk.hall.decoupling_nF * 1e3)
    for i, site in enumerate(lay.hall_sites, start=1):
        ref = f"U{10 + i}"
        out = site.direct_signal or f"HC{site.mux_channel}"  # the filtered net
        raw = f"HOUT_{out}"
        ckt.add(ref, hall, sensor.part, {"1": "HALL_VCC", "2": raw, "3": GND})
        c(f"C{10 + i}", c_dec, "HALL_VCC", GND)
        r(f"R{10 + i}", r_filter, raw, out)
        c(f"C{20 + i}", c_filter, out, GND)

    # ---------------- multiplexer, references on its spare channels, extension header ----
    ch = dm.mux_channels
    mux_map = {
        "COM": "MUX_OUT",
        "S0": "MUX_S0",
        "S1": "MUX_S1",
        "S2": "MUX_S2",
        "S3": "MUX_S3",
        "E": "MUX_EN",
        "VCC": "3V3",
        "GND": GND,
    }
    for site in lay.hall_sites:
        mux_map[f"I{site.mux_channel}"] = site.direct_signal or f"HC{site.mux_channel}"
    mux_map[f"I{ch.ground}"] = GND
    mux_map[f"I{ch.rail_half}"] = "RAIL_HALF"
    mux_map[f"I{ch.led_step}"] = "LED_STEP"
    for k in ch.grounded:
        mux_map[f"I{k}"] = GND
    for k in ch.extension:
        mux_map[f"I{k}"] = f"EXT{k}"
    mux = mux_part(cfg)
    ckt.add("U3", mux, cfg.hall_rfid.mux.part, pins_by_name(mux, mux_map))
    c("C31", "100n", "3V3", GND)
    r("R31", "0R", "MUX_EN", GND)
    r("R32", "10k", "HALL_VCC", "RAIL_HALF")
    r("R33", "10k", "RAIL_HALF", GND)
    r("R34", "10k", "LED", "LED_STEP")
    r("R35", "10k", "LED_STEP", GND)
    c("C32", "10n", "LED_STEP", GND)
    ext = {str(i + 1): f"EXT{k}" for i, k in enumerate(ch.extension)}
    ext[str(len(ch.extension) + 1)] = GND
    ckt.add("J3", H1X06, "MUX EXT", ext)

    # ---------------- switched sensor rail ----------------
    ckt.add("Q1", PFET, "AO3401A", {"1": "ROW_EN1", "2": "3V3", "3": "HALL_VCC"})
    r("R41", "10k", "ROW_EN1", "3V3")
    ckt.add("JP1", JP_OPEN, "HALL_VCC bypass", {"1": "3V3", "2": "HALL_VCC"})
    c("C41", "1u", "HALL_VCC", GND)
    c("C42", "100n", "HALL_VCC", GND)

    # ---------------- MISO buffer: one gate per reader, enabled by its NSS ----------------
    ckt.add(
        "U7",
        BUF4,
        "74LVC125",
        {
            "1": "NSS_A1",
            "2": "MISO_A1",
            "3": "SPI_MISO",
            "4": "NSS_B1",
            "5": "MISO_B1",
            "6": "SPI_MISO",
            "10": "3V3",
            "9": GND,
            "13": "3V3",
            "12": GND,
            "7": GND,
            "14": "3V3",
        },
        nc=("8", "11"),
    )
    c("C71", "100n", "3V3", GND)

    # ---------------- the two readers, their loops and matching networks ----------------
    reader = reader_part(cfg)
    for n, sq in enumerate(dm.squares(), start=1):
        v = ReaderValues(cfg, lay, sq)
        tx1, tx2, tvdd, vmid, rx = (f"{s}_{sq}" for s in ("TX1", "TX2", "TVDD", "VMID", "RX"))
        xi, xo, nss, nrst, miso = (f"{s}_{sq}" for s in ("XI", "XO", "NSS", "NRSTPD", "MISO"))
        loop_1, loop_2 = f"LOOP_{sq}_1", f"LOOP_{sq}_2"
        ckt.add(
            f"U{n}",
            reader,
            reader.mpn,
            {
                "1": GND,  # I2C low: SPI with EA high
                "2": "3V3",
                "3": "3V3",
                "4": GND,
                "5": GND,
                "6": nrst,
                "7": GND,  # MFIN unused: to PVSS
                "9": "3V3",
                "10": GND,
                "11": tx1,
                "12": tvdd,
                "13": tx2,
                "14": GND,
                "15": "3V3",
                "16": vmid,
                "17": rx,
                "18": GND,
                "21": xi,
                "22": xo,
                "23": "RFID_IRQ",
                "24": nss,
                "29": "SPI_SCK",
                "30": "SPI_MOSI",
                "31": miso,
                "32": "3V3",
                "33": GND,
            },
            nc=("8", "19", "20", "25", "26", "27", "28"),
        )
        ckt.add(f"L{n}", LOOP, f"boucle {v.loop_kind}", {"1": loop_1, "2": loop_2})
        ckt.add(f"Y{n}", XTAL, "27.12MHz", {"1": xi, "3": xo, "2": GND, "4": GND})
        c(f"C{n}01", "15p", xi, GND)
        c(f"C{n}02", "15p", xo, GND)
        c(f"C{n}03", "100n", "3V3", GND)
        c(f"C{n}04", "100n", "3V3", GND)
        c(f"C{n}05", "100n", "3V3", GND)
        c(f"C{n}06", "100n", vmid, GND)
        r(f"R{n}01", v.r_sense, "3V3", tvdd)
        c(f"C{n}07", "10u/25V", tvdd, GND, part=C10U)
        c(f"C{n}08", "100n", tvdd, GND)
        c(f"C{n}09", "1u", "3V3", GND)
        # two matching branches: east to TX1 (loop end 2, the bridge),
        # west to TX2 (loop end 1, the top-side start)
        for side, tx, loop_end, base in (("E", tx1, loop_2, 10), ("W", tx2, loop_1, 20)):
            nf, na, nb = (f"N{side}{s}_{sq}" for s in ("F", "A", "B"))
            r(f"R{n}{base + 1}", "0R", tx, nf)
            ckt.add(f"J{n}0{1 if side == 'E' else 2}", UFL, "U.FL", {"1": nf, "2": GND}, dnp=True)
            ckt.add(f"L{n}{base + 1}", L0805, v.l0, {"1": nf, "2": na})
            c(f"C{n}{base + 1}", v.c0, na, GND)
            c(f"C{n}{base + 2}", v.c1_main, na, nb)
            c(f"C{n}{base + 3}", v.c1_trim, na, nb)
            c(f"C{n}{base + 4}", "retouche", na, nb, dnp=True)
            c(f"C{n}{base + 5}", v.c2_main, nb, GND)
            c(f"C{n}{base + 6}", v.c2_trim, nb, GND)
            c(f"C{n}{base + 7}", "retouche", nb, GND, dnp=True)
            r(f"R{n}{base + 2}", v.rq, nb, loop_end)
        # receive divider from the C0 node of the west branch (D15: a second
        # R1 in series, bridged by a solder jumper opened for full-power tests)
        r(f"R{n}31", v.r1, f"NWA_{sq}", f"RXD_{sq}")
        r(f"R{n}32", v.r1, f"RXD_{sq}", f"RXC_{sq}", dnp=True)
        ckt.add(f"JP{n}01", JP_BRIDGED, "R1b bypass", {"1": f"RXD_{sq}", "2": f"RXC_{sq}"})
        c(f"C{n}31", v.c_rx, f"RXC_{sq}", rx)
        r(f"R{n}33", v.r2, rx, vmid)
        r(f"R{n}41", "10k", nss, "3V3")
        r(f"R{n}42", "10k", nrst, GND)
        r(f"R{n}43", "0R", miso, "SPI_MISO", dnp=True)
        for k, net in enumerate((tx1, tx2, rx, tvdd, GND), start=1):
            ckt.add(f"TP{n}0{k}", TP, net, {"1": net})

    # ---------------- headers and test points ----------------
    esc = {
        str(i + 1): (sig if sig in (GND, "3V3") else sig) for i, sig in enumerate(dm.escape_header)
    }
    ckt.add("J4", H2X10, "ESCAPE", esc, dnp=True)
    ckt.add("J5", H1X03, "PICKUP", {"1": "PICKUP", "2": GND, "3": "3V3"})
    c("C54", "10n", "PICKUP", GND)
    for ref, net in (
        ("TP1", "3V3"),
        ("TP2", GND),
        ("TP3", "VBUS"),
        ("TP4", "HALL_VCC"),
        ("TP5", "UART0_TX"),
        ("TP6", "UART0_RX"),
        ("TP7", GND),
    ):
        ckt.add(ref, TP, net, {"1": net})
    return ckt


# ------------------------------------------------------------ board
def demo_spec(cfg: BoardConfig) -> Spec:
    dm = cfg.hall_rfid.demo
    lay = layout(cfg)
    w, h = dm.board.size_mm
    return Spec(
        name="hallrfid-demo",
        title="Demonstrateur Hall + RFID, 2 cases",
        width=w,
        height=h,
        layers=dm.board.layers,
        clearance=0.15,
        track=0.3,
        power_track=0.5,
        via_pad=0.8,
        via_drill=0.4,
        gnd_layer="In1.Cu" if dm.board.layers == 4 else "B.Cu",
        power_nets=("3V3", "HALL_VCC"),  # VBUS: a short run under 0.5 A, thin like a signal
        pour_region=lay.pour,
        h_weight=2.5,  # long routes from the loops to the far side of the strip: greedy search
    )


SPEC: Spec | None = None  # filled by build_hallrfid from the config (the size is the yaml's)


def loop_drawings(cfg: BoardConfig, lay: DemoLayout) -> dict[str, LoopDrawing]:
    return {
        lp.square: square_loop(
            (lp.outline[0] + lp.outline[2]) / 2.0,
            (lp.outline[1] + lp.outline[3]) / 2.0,
            lp.side_mm,
            lp.turns,
            lp.track_mm,
            lp.gap_mm,
        )
        for lp in lay.loops
    }


def _stack(out, refs, ckt, x0, x1, y0, upright=True):
    """Shelf-pack refs from y0 down inside [x0, x1]; returns the lowest
    courtyard edge, so the next group starts under this one."""
    from quadgen.strip import placed_box

    placed = shelf(refs, ckt, x0, x1, y0, upright=upright)
    out.update(placed)
    by_ref = {c.ref: c for c in ckt.components}
    bottom = y0
    for ref, (x, y, rot) in placed.items():
        _x0, _y0, _x1, y1 = placed_box(load_footprint(by_ref[ref].part.footprint), x, y, rot)
        bottom = max(bottom, y1)
    return bottom


def _stack_right(out, refs, ckt, x0, x1, y0):
    """Like _stack, the group pushed east against x1 (the shelf packs
    from x0): the parts land beside the chip, not at the zone's edge."""
    from quadgen.strip import placed_box

    placed = shelf(refs, ckt, x0, x1, y0, upright=True)
    by_ref = {c.ref: c for c in ckt.components}
    right, bottom = x0, y0
    boxes = {}
    for ref, (x, y, rot) in placed.items():
        boxes[ref] = placed_box(load_footprint(by_ref[ref].part.footprint), x, y, rot)
        right = max(right, boxes[ref][2])
        bottom = max(bottom, boxes[ref][3])
    shift = x1 - right
    for ref, (x, y, rot) in placed.items():
        out[ref] = (round(x + shift, 3), y, rot)
    return bottom


ROW_GAP_MM = 0.8  # between two stacked groups of parts: a track and its clearance pass
FANOUT_RING_MM = 5.2  # no part nearer a fine-pitch chip's centre: escape vias at 3.6 and 4.3
ROW_PITCH_MM = 2.2  # the matching capacitors: 1.2 mm between two 0603 pads, a via fits
MATCH_ROW_MM = 5.9  # the matching capacitors' row centre, past the loop's outer copper edge
NEAR_SHELF_MM = 15.5  # the decoupling shelf east of a reader chip reaches this far from it


def hallrfid_placements(
    ckt: Circuit, cfg: BoardConfig | None = None
) -> dict[str, tuple[float, float, float]]:
    """Floor plan. Play area: the sensors inside the loop openings with
    their capacitor east and resistor west, the net tie of each loop at
    its inner end. Under each loop, from the feed down: the two series
    resistors, then one row per branch of C0, the three C2 and the three
    C1 (series parts and ground side of the network together, the row of
    A1 still inside the keepout, its ground vias past it), the EMC filter
    and the isolators, the reader (rotated so TX1 and TX2 face north),
    its quartz and receive parts west, its supplies east, the digital
    pulls and test points south. Strip: mux and filters west, references
    and switched rail beside them, buffer and regulator in the middle,
    USB-C on the south edge in the centre column with its protection
    west of it, the module east with its antenna on the edge, buttons
    under it, LED and console test points west of it, headers along the
    south edge."""
    from chessboard_calc.config import load_config

    cfg = cfg or load_config()
    dm = cfg.hall_rfid.demo
    lay = layout(cfg)
    draw = loop_drawings(cfg, lay)
    out: dict[str, tuple[float, float, float]] = {}

    # ---- play area: sensors and loop ties
    for i, site in enumerate(lay.hall_sites, start=1):
        sx, sy = site.centre_mm
        out[f"U{10 + i}"] = (sx, sy, 0.0)
        out[f"C{10 + i}"] = (sx + 2.9, sy, 90.0)
        out[f"R{10 + i}"] = (sx - 2.9, sy, 90.0)
    for n, sq in enumerate(dm.squares(), start=1):
        d = draw[sq]
        out[f"L{n}"] = (d.tie_at[0], d.tie_at[1], 0.0)

    # ---- under each loop: the reader block
    for n, sq in enumerate(dm.squares(), start=1):
        lp = lay.loop(sq)
        x0, x1 = lp.outline[0], lp.outline[2]
        cx = (x0 + x1) / 2.0
        y_f = lp.outline[3]  # outer copper edge, south side
        rq_y = y_f + 2.6
        # pad 2 (the loop end) on top, where the loop's feed arrives
        out[f"R{n}22"] = (cx - 1.2, rq_y, 90.0)  # west branch: loop end 1
        out[f"R{n}12"] = (cx + 1.2, rq_y, 90.0)  # east branch: loop end 2
        # one row per branch, inner to outer: C1 main, trim, spare, C2 main,
        # trim, spare, C0; upright 0603 at a pitch that leaves a via and its
        # clearance between two neighbours (the nets of the row alternate
        # between the top and the bottom pads)
        y_row = y_f + MATCH_ROW_MM
        west = [f"C{n}22", f"C{n}23", f"C{n}24", f"C{n}25", f"C{n}26", f"C{n}27", f"C{n}21"]
        east = [f"C{n}12", f"C{n}13", f"C{n}14", f"C{n}15", f"C{n}16", f"C{n}17", f"C{n}11"]
        for k, ref in enumerate(west):
            out[ref] = (cx - 2.6 - ROW_PITCH_MM * k, y_row, 90.0)
        for k, ref in enumerate(east):
            out[ref] = (cx + 2.6 + ROW_PITCH_MM * k, y_row, 90.0)
        # EMC filter, isolators, TX test points and U.FL taps in one row, a
        # via row's worth under the capacitors and clear of the reader's
        # north escape vias (3.6 and 4.3 mm from its centre)
        y_l0 = y_row + 5.9
        out[f"L{n}21"] = (cx - 3.6, y_l0, 90.0)
        out[f"L{n}11"] = (cx + 3.6, y_l0, 90.0)
        out[f"R{n}21"] = (cx - 1.3, y_l0, 90.0)
        out[f"R{n}11"] = (cx + 1.3, y_l0, 90.0)
        out[f"TP{n}02"] = (cx - 6.9, y_l0, 0.0)  # TX2
        out[f"TP{n}01"] = (cx + 6.9, y_l0, 0.0)  # TX1
        out[f"J{n}02"] = (cx - 11.0, y_l0, 0.0)  # U.FL west (not fitted)
        out[f"J{n}01"] = (cx + 11.0, y_l0, 0.0)
        y_u = y_l0 + 5.6
        out[f"U{n}"] = (cx, y_u, READER_ROT)
        # the shelves beside the chip use the room past the loop's width:
        # the board edge side and the corridor between the two zones
        zx0, zx1 = (5.0, 51.0) if n == 1 else (51.0, 97.0)
        # against the chip: the crystal and its two capacitors west, the
        # supply decoupling east; the receive parts and the TVDD sense
        # under them, out to the zone's edge
        near_w = [f"Y{n}", f"C{n}01", f"C{n}02"]
        far_w = [f"R{n}31", f"R{n}32", f"JP{n}01", f"C{n}31", f"C{n}06", f"R{n}33"]
        near_e = [f"C{n}03", f"C{n}04", f"C{n}05", f"C{n}09"]
        far_e = [f"R{n}01", f"C{n}07", f"C{n}08", f"TP{n}04"]
        south = [f"R{n}41", f"R{n}42", f"R{n}43", f"TP{n}03", f"TP{n}05"]
        if cx - FANOUT_RING_MM - zx0 < 6 * 2.9:
            # a west zone too narrow for one row of six: the jumper moves south
            far_w.remove(f"JP{n}01")
            south.append(f"JP{n}01")
        top = y_u - 3.1
        ring = FANOUT_RING_MM
        b_w = _stack_right(out, near_w, ckt, zx0, cx - ring, top)
        b_w = _stack(out, far_w, ckt, zx0, cx - ring, b_w + ROW_GAP_MM)
        b_e = _stack(out, near_e, ckt, cx + ring, cx + ring + NEAR_SHELF_MM - 3.6, top)
        b_e = _stack(out, far_e, ckt, cx + ring, zx1, b_e + ROW_GAP_MM)
        # the digital pulls and the RX and ground test points, under the east shelf
        _stack(out, south, ckt, cx + ring, zx1, max(b_e, y_u + ring) + ROW_GAP_MM)

    # ---- strip, west: multiplexer, filters, references, switched rail
    out["U3"] = (18.5, 70.5, 0.0)
    _stack(out, ["C21", "C22", "C23", "C24", "C25", "C26"], ckt, 8.0, 25.5, 75.5)
    b = _stack(out, ["R31", "C31", "R32", "R33", "R34", "R35", "C32"], ckt, 24.5, 36.0, 69.0)
    _stack(out, ["Q1", "R41", "JP1", "C41", "C42", "TP4"], ckt, 24.5, 36.0, b + ROW_GAP_MM)
    out["J4"] = (3.6, 69.5, 0.0)  # 2 x 10, pins run south, clear of the corner hole
    _stack(out, ["TP1", "TP2", "TP3", "TP7"], ckt, 8.0, 16.0, 79.0)
    out["J3"] = (12.0, 96.5, 90.0)  # 1 x 6 along the south edge, pin 1 west
    # ---- strip, centre: buffer, regulator, USB-C on the south edge with its protection west
    b = _stack(out, ["U7"], ckt, 37.0, 48.5, 69.0)
    _stack(out, ["C71", "R71"], ckt, 37.0, 48.5, b + 2.2)  # past the buffer's escape vias
    _stack(out, ["U6", "C63", "C61", "C62"], ckt, 49.0, 60.5, 70.0)
    _stack(out, ["R61", "U5", "R62"], ckt, 36.5, 44.5, 88.5)
    out["J1"] = (47.0, 90.85, 0.0)
    out["J2"] = (30.0, 95.0, 90.0)
    # ---- strip, east: the module, its antenna on the east edge
    ux, uy = 87.0, 81.5
    out["U4"] = (ux, uy, 270.0)
    b = _stack(out, ["C51", "C52", "R51", "C53", "R52"], ckt, 61.0, 72.0, 71.0)
    _stack(out, ["D1", "R53", "C54", "TP5", "TP6"], ckt, 61.0, 72.0, b + ROW_GAP_MM)
    _stack(out, ["SW1", "SW2"], ckt, 69.5, 93.0, 92.5, upright=False)  # clear of the corner hole
    out["J5"] = (62.0, 96.5, 90.0)
    return out


def play_area_blocks(
    width: float, pour_top: float, loop_boxes: list[tuple[float, float, float, float]]
) -> list[tuple[float, float, float, float, str]]:
    """The play area outside the loop bands, closed to the router: the
    margins along the edges and the gaps between the loops would be
    highways around the loops, copper under the playing surface that a
    signal has no business on. Every signal of a loop opening leaves by
    its corridor; the strip starts at the pour."""
    boxes = sorted(loop_boxes)
    blocks = [(0.0, 0.0, width, max(b[1] for b in boxes), "play")]
    edges = [0.0] + [x for b in boxes for x in (b[0], b[2])] + [width]
    for x0, x1 in zip(edges[0::2], edges[1::2], strict=True):
        if x1 - x0 > 0.0:
            blocks.append((x0, 0.0, x1, pour_top, "play"))
    return blocks


CORRIDOR_PITCH_MM = 0.75  # between the seed stubs of a corridor: 0.3 mm tracks, 0.45 mm apart


def corridor_nets(lay: DemoLayout, square: str) -> list[str]:
    """The nets that leave the opening of `square` by its corridor: the
    sensor rail and ground, then the output of every sensor inside."""
    outs = [s.direct_signal or f"HC{s.mux_channel}" for s in lay.hall_sites if s.square == square]
    return ["HALL_VCC", "GND", *outs]


def hand_routes(gb: GenericBoard, cfg: BoardConfig, lay: DemoLayout) -> None:
    """The copper drawn before the router runs: the two loops (turns, net
    tie, bridge, feeds to their series resistors), and in each corridor
    one short stub per net that leaves the opening, on the back layer: a
    stepping stone the router reaches from inside the opening in a short
    search and leaves toward the strip in another, instead of one long
    search that spends its budget inside the opening."""
    draw = loop_drawings(cfg, lay)
    pads = {(p.ref, p.number): p for p in gb.res.pads}
    back = gb.layers[-1]
    for sq, (x0, _y0, x1, y1) in lay.trio_corridors.items():
        nets = corridor_nets(lay, sq)
        span = CORRIDOR_PITCH_MM * (len(nets) - 1)
        if span > (x1 - x0) - 2.0 * gb.spec.track:
            raise ValueError(f"the corridor of {sq} is too narrow for {len(nets)} stubs")
        xs = (x0 + x1) / 2.0 - span / 2.0
        outer = lay.loop(sq).outline[3]
        top = outer - 1.0  # under the outer turn
        # the stubs stop above the matching capacitors' row (its top is
        # 1.5 mm over the row's centre, MATCH_ROW_MM past the outer turn)
        bottom = min(y1 - 0.5, outer + MATCH_ROW_MM - 1.5 - 0.9)
        for k, net in enumerate(nets):
            x = round(xs + CORRIDOR_PITCH_MM * k, 3)
            gb.seed(net, back, [(x, round(top, 3)), (x, round(bottom, 3))], gb.spec.track)
    for n, sq in enumerate(cfg.hall_rfid.demo.squares(), start=1):
        d = draw[sq]
        west = pads[(f"R{n}22", "2")]
        east = pads[(f"R{n}12", "2")]
        if {west.net, east.net} != {f"LOOP_{sq}_1", f"LOOP_{sq}_2"}:
            raise ValueError(f"the loop of {sq} expects pad 2 of its damping resistors")
        if west.y > pads[(f"R{n}22", "1")].y or east.y > pads[(f"R{n}12", "1")].y:
            raise ValueError(f"the loop ends of {sq} must be the upper pads of Rq")
        seed_loop(gb, d, f"LOOP_{sq}_1", f"LOOP_{sq}_2", (west.x, west.y), (east.x, east.y))


def build_hallrfid(cfg: BoardConfig):
    global SPEC
    SPEC = spec = demo_spec(cfg)
    lay = layout(cfg)
    ckt = build_hallrfid_circuit(cfg)
    placements = hallrfid_placements(ckt, cfg)
    gb = GenericBoard(spec, ckt, placements, generator="boardgen", **BOARD_OPTIONS)
    gb.place_all()
    draw = loop_drawings(cfg, lay)
    loop_boxes = []
    for sq, d in draw.items():
        blocks = router_blocks(d, lay.keepout_mm, lay.trio_corridors[sq])
        for block in blocks:
            gb.router_block(*block)
        loop_boxes.append(
            (
                min(b[0] for b in blocks),
                min(b[1] for b in blocks),
                max(b[2] for b in blocks),
                max(b[3] for b in blocks),
            )
        )
    for block in play_area_blocks(spec.width, lay.pour[1], loop_boxes):
        gb.router_block(*block)
    # the antenna of the module: no copper under it, on either layer
    ux, uy, _rot = placements["U4"]
    x0, x1 = ux + ESP32_ANTENNA_FROM, min(spec.width, ux + ESP32_ANTENNA_TO)
    gb.keepout_rect(x0, uy - ESP32_HALF, x1, uy + ESP32_HALF, "antenna")
    for hole in lay.holes:
        gb.hole(hole.centre_mm[0], hole.centre_mm[1], hole.d_mm, "H")
    for i, fid in enumerate(lay.fiducials, start=1):
        gb.fiducial(fid.centre_mm[0], fid.centre_mm[1], FIDUCIAL_FP, f"FID{i}")
    hand_routes(gb, cfg, lay)
    hall_nets = [s.direct_signal or f"HC{s.mux_channel}" for s in lay.hall_sites]
    gb.route_all(first=tuple(hall_nets))
    w, h = spec.width, spec.height
    return gb.finish(
        texts=[
            ("DEMONSTRATEUR HALL + RFID", w / 2.0, h - 1.6, "F.SilkS", 1.2),
            ("A1", 25.0, 47.5, "F.SilkS", 1.0),
            ("B1", 75.0, 47.5, "F.SilkS", 1.0),
        ]
    )


def schematic_groups() -> list[tuple[str, float, list[str]]]:
    readers = []
    for n in (1, 2):
        refs = [f"U{n}", f"L{n}", f"Y{n}"]
        refs += [f"C{n}0{k}" for k in range(1, 10)]
        refs += [f"R{n}01", f"R{n}11", f"R{n}12", f"R{n}21", f"R{n}22", f"J{n}01", f"J{n}02"]
        refs += [f"L{n}11", f"L{n}21"]
        refs += [f"C{n}1{k}" for k in range(1, 8)] + [f"C{n}2{k}" for k in range(1, 8)]
        refs += [
            f"R{n}31",
            f"R{n}32",
            f"JP{n}01",
            f"C{n}31",
            f"R{n}33",
            f"R{n}41",
            f"R{n}42",
            f"R{n}43",
        ]
        refs += [f"TP{n}0{k}" for k in range(1, 6)]
        readers.append(
            (f"READER {'A1' if n == 1 else 'B1'}, LOOP, MATCHING", 40.0 + 220.0 * (n - 1), refs)
        )
    hall = [f"U{10 + i}" for i in range(1, 7)] + [f"C{10 + i}" for i in range(1, 7)]
    hall += [f"R{10 + i}" for i in range(1, 7)] + [f"C{20 + i}" for i in range(1, 7)]
    return [
        *readers,
        ("HALL SENSORS", 480.0, hall),
        (
            "MULTIPLEXER, REFERENCES, SWITCHED RAIL",
            580.0,
            [
                "U3",
                "C31",
                "R31",
                "R32",
                "R33",
                "R34",
                "R35",
                "C32",
                "J3",
                "Q1",
                "R41",
                "JP1",
                "C41",
                "C42",
            ],
        ),
        (
            "ESP32-S3, USB, 3.3 V",
            680.0,
            [
                "U4",
                "C51",
                "C52",
                "R51",
                "C53",
                "R52",
                "SW1",
                "SW2",
                "R53",
                "D1",
                "R71",
                "J1",
                "R61",
                "R62",
                "U5",
                "J2",
                "U6",
                "C61",
                "C62",
                "C63",
            ],
        ),
        (
            "MISO BUFFER, HEADERS, TEST POINTS",
            800.0,
            ["U7", "C71", "J4", "J5", "C54", "TP1", "TP2", "TP3", "TP4", "TP5", "TP6", "TP7"],
        ),
    ]
