"""Drawn schematic of the quadrant: one sheet per functional block of
note 17, wires drawn from fixed templates, global labels for the rails,
the address bus and the nets shared between sheets, local labels for
the nets internal to a sheet. Built on analoggen.sheets, which checks
the drawing against the circuit before anything is written.

Template coordinates are in grid units G = 2.54 mm (half-grid values
land on KiCad's 1.27 mm grid); each block is drawn at an origin so the
same template serves the 2 x 2 and the 4 x 4 quadrant.
"""

from __future__ import annotations

import math

from analoggen.circuit import Circuit
from analoggen.filters import ChainDesign
from analoggen.sheets import Placed, Schematic, Sheet

from chessboard_calc.config import BoardConfig

from .circuit import DEC_HI_OUT, DEC_LO_OUT, MUX_NC, cell_refs, coil_count, mux_refs

G = 2.54
CELLS_PER_SHEET = 4


class _Block:
    """A sheet plus an origin, addressed in grid units."""

    def __init__(self, sheet: Sheet, by_ref: dict, ox: float, oy: float) -> None:
        self.sheet, self.by_ref, self.ox, self.oy = sheet, by_ref, ox, oy

    def p(self, x: float, y: float) -> tuple[float, float]:
        return (round((self.ox + x) * G, 4), round((self.oy + y) * G, 4))

    def place(self, ref: str, x: float, y: float, rot: int = 0, mirror: str | None = None,
              unit: int = 1, fields: str = "right") -> Placed:
        px, py = self.p(x, y)
        return self.sheet.place(self.by_ref[ref], px, py, rot, mirror, unit, fields)

    def wire(self, *pts: tuple[float, float]) -> None:
        self.sheet.wire(*[self.p(*pt) for pt in pts])

    def label(self, net: str, x: float, y: float, direction: str, kind: str = "global") -> None:
        px, py = self.p(x, y)
        self.sheet.label(net, px, py, direction, kind)

    def pin_label(self, pl: Placed, number: str, net: str | None = None, kind: str = "global",
                  length: float = 1.0) -> None:
        self.sheet.pin_label(pl, number, net, kind, length * G)

    def stub(self, pl: Placed, number: str, length: float = 1.0) -> tuple[float, float]:
        return self.sheet.stub(pl, number, length * G)

    def nc(self, pl: Placed, number: str) -> None:
        self.sheet.pin_nc(pl, number)

    def text(self, s: str, x: float, y: float, size: float = 2.0) -> None:
        px, py = self.p(x, y)
        self.sheet.text(s, px, py, size)


# ---------------------------------------------------------------- cells
def draw_cell(b: _Block, k: int) -> None:
    """One coil cell: the spiral between an A rail and a B rail, the bias,
    excitation, freewheel, flyback, damping and measurement branches."""
    cr = cell_refs(k)
    a, bnet = f"C{k}_A", f"C{k}_B"
    b.text(f"Cellule {k}, spirale C{k}", 16, -0.5)
    b.wire((2, 6), (34, 6))
    b.wire((2, 16), (34, 16))
    b.label(a, 22, 6, "r", "local")
    b.label(bnet, 22, 16, "r", "local")
    b.place(cr["tie"], 6, 11.5)  # pin 1 (6, 10) on A, pin 2 (6, 13) on B
    b.wire((6, 6), (6, 10))
    b.wire((6, 13), (6, 16))
    # bias to VREF
    ba = b.place(cr["bleed_a"], 4, 3.5, rot=180)  # pin 1 at the bottom, on A
    b.wire((4, 5), (4, 6))
    b.pin_label(ba, "2")
    bb = b.place(cr["bleed_b"], 4, 18.5)  # pin 1 at the top, on B
    b.wire((4, 16), (4, 17))
    b.pin_label(bb, "2")
    # excitation: bus diode from DRIVE_BUS into A, low-side FET on B
    bus = b.place(cr["bus"], 10, 3.5, rot=90)  # anode up, cathode (pin 1) down on A
    b.wire((10, 5), (10, 6))
    b.pin_label(bus, "2")
    free = b.place(cr["free"], 14, 8.5, rot=270)  # cathode (pin 1) up on A, anode down to GND
    b.wire((14, 6), (14, 7))
    b.pin_label(free, "2")
    nf = b.place(cr["nfet"], 20, 22)  # gate (18, 22), source (21, 24), drain (21, 20)
    b.wire((21, 16), (21, 20))
    b.pin_label(nf, "2")
    b.wire((18, 22), (14, 22), (14, 23))
    gp = b.place(cr["gate_pd"], 14, 24.5)  # pin 1 (14, 23) on the gate, pin 2 to GND
    b.pin_label(gp, "2")
    b.label(f"DRIVE{k}", 14, 22, "l")
    fly = b.place(cr["fly"], 31, 18.5, rot=90, fields="left")  # anode up on B, cathode to VIN
    b.wire((31, 16), (31, 17))
    b.pin_label(fly, "1")
    # damping: P-FET source on A, 680 ohms to B, gate from the decoder
    b.place(cr["pfet"], 27, 9, mirror="x")  # gate (25, 9), source (28, 7), drain (28, 11)
    b.wire((28, 6), (28, 7))
    b.place(cr["damp_r"], 28, 14.5)  # pin 1 (28, 13) from the drain, pin 2 (28, 16) on B
    b.wire((28, 11), (28, 13))
    b.label(f"DMP{k}", 28, 12, "r", "local")
    b.wire((25, 9), (22, 9), (22, 12))
    b.label(f"DAMP{k}_N", 22, 12, "d")
    # measurement: clamps and BAV99 in front of the mux
    b.place(cr["clamp_a"], 35.5, 6, rot=90)  # pin 1 (34, 6) on A, pin 2 (37, 6)
    b.wire((37, 6), (41, 6))
    da = b.place(cr["dual_a"], 39, 2)  # pin 3 (39, 4) down to the M line, 1 left, 2 right
    b.wire((39, 4), (39, 6))
    b.pin_label(da, "1")
    b.pin_label(da, "2")
    b.label(f"M{k}_A", 41, 6, "r")
    b.place(cr["clamp_b"], 35.5, 16, rot=90)
    b.wire((37, 16), (41, 16))
    db = b.place(cr["dual_b"], 39, 20, mirror="x")  # pin 3 (39, 18) up to the M line
    b.wire((39, 16), (39, 18))
    b.stub(db, "1")
    b.label("GND", 35, 20, "d")
    b.pin_label(db, "2")
    b.label(f"M{k}_B", 41, 16, "r")


CELL_W, CELL_H = 50.0, 33.0


def draw_cells(sheet: Sheet, by_ref: dict, first: int, last: int) -> None:
    for i, k in enumerate(range(first, last + 1)):
        row, col = divmod(i, 2)
        draw_cell(_Block(sheet, by_ref, 5 + col * CELL_W, 7 + row * CELL_H), k)


# ---------------------------------------------------------------- rails
def draw_rails(sheet: Sheet, by_ref: dict) -> None:
    b = _Block(sheet, by_ref, 2, 2)
    b.text("Découplage", 2, 1)
    for i, ref in enumerate(("C1", "C2", "C4", "C3")):
        c = b.place(ref, 4 + 4 * i, 5.5)
        b.pin_label(c, "1")
        b.pin_label(c, "2")
    b.text("Polarisation VREF", 22, 1)
    r5 = b.place("R5", 24, 3.5)  # pin 1 (24, 2) to 5VA, pin 2 (24, 5)
    b.pin_label(r5, "1")
    r6 = b.place("R6", 24, 7.5)  # pin 1 (24, 6), pin 2 (24, 9) to GND
    b.pin_label(r6, "2")
    b.wire((24, 5), (24, 6), (33, 6))
    c13 = b.place("C13", 28, 7.5)  # pin 1 (28, 6) on the divider node
    b.pin_label(c13, "2")
    b.label("VREF_DIV", 25, 6, "r", "local")
    b.place("U8", 36, 7, unit=1)  # + (33, 6), - (33, 8), out (39, 7)
    b.wire((39, 7), (50, 7))
    b.wire((41, 7), (41, 10), (31, 10), (31, 8), (33, 8))
    c23 = b.place("C23", 44, 8.5)  # pin 1 (44, 7) on VREF
    b.pin_label(c23, "2")
    b.place("TP2", 46, 7)
    b.label("VREF", 50, 7, "r")
    u8c = b.place("U8", 56, 7, unit=3)
    b.pin_label(u8c, "8")
    b.pin_label(u8c, "4")
    c22 = b.place("C22", 60, 7.5)
    b.pin_label(c22, "1")
    b.pin_label(c22, "2")
    b.text("Rail d'impulsion", 2, 13.5, 1.5)
    q2 = b.place("Q2", 12, 23)  # gate (10, 23), source (13, 25), drain (13, 21)
    b.wire((10, 23), (8, 23), (8, 24))
    b.label("PULSE_EN", 8, 23, "l")
    r8 = b.place("R8", 8, 25.5)  # pin 1 (8, 24) on PULSE_EN, pin 2 to GND
    b.pin_label(r8, "2")
    b.pin_label(q2, "2")
    q1 = b.place("Q1", 18, 15, mirror="x")  # gate (16, 15), source (19, 13) up, drain (19, 17)
    b.pin_label(q1, "2")
    r7 = b.place("R7", 13, 12.5, rot=180)  # pin 1 (13, 14) on the gate node, pin 2 (13, 11) to VIN
    b.pin_label(r7, "2")
    b.wire((13, 14), (13, 21))
    b.wire((13, 15), (16, 15))
    b.label("Q1_G", 14, 15, "r", "local")
    b.wire((19, 17), (19, 19), (24, 19))
    b.label("PULSE_RAIL", 20, 19, "r", "local")
    b.place("R9", 25.5, 19, rot=90)  # pin 1 (24, 19) rail, pin 2 (27, 19) bus
    b.wire((27, 19), (34, 19))
    r10 = b.place("R10", 30, 20.5)  # pin 1 (30, 19) on the bus
    b.pin_label(r10, "2")
    b.place("TP3", 32, 19)
    b.label("DRIVE_BUS", 34, 19, "r")
    u6 = b.place("U6", 46, 23)  # in (40, 23), out (51, 23), VCC (44, 19), GND (44, 27)
    for pin in ("2", "4", "5", "3"):
        b.pin_label(u6, pin)
    tp4 = b.place("TP4", 60, 23)
    b.pin_label(tp4, "1")
    b.text("PULSE_EN ferme Q1 par Q2 ; R7 le rouvre en moins d'une microseconde ; "
           "10 ohms vers le bus des cellules.", 2, 31, 1.5)


# ---------------------------------------------------------------- selection
def _mux(b: _Block, ref: str, x: float, y: float, n: int) -> None:
    u = b.place(ref, x, y)
    for pin in ("15", "14", "10", "16", "27", "31", "29"):
        b.pin_label(u, pin)
    b.stub(u, "25")  # the two VSS pins share one point
    b.pin_label(u, "9")
    b.label("GND", *_end(b, u, "25"), "d")
    comp = b.by_ref[ref]
    for i in range(8):
        for pin in (str(17 + i), str(8 - i)):
            if pin in comp.pins:
                b.pin_label(u, pin)
            else:
                b.nc(u, pin)
    for pin in MUX_NC:
        b.nc(u, pin)


def _end(b: _Block, pl: Placed, number: str) -> tuple[float, float]:
    """Grid position of the free end of a one-grid stub on `number`."""
    x, y = pl.pin_pos(number)
    dx, dy = pl.pin_away(number)
    return _grid(b, x + dx * G, y + dy * G)


def _grid(b: _Block, x: float, y: float) -> tuple[float, float]:
    return (x / G - b.ox, y / G - b.oy)


def draw_select(sheet: Sheet, by_ref: dict, n: int) -> None:
    b = _Block(sheet, by_ref, 2, 2)
    b.text("Décodeurs d'adresse", 2, 1)
    b.text("Excitation : 74HC4514, actif haut, inhibé hors PULSE_EN. "
           "Amortissement : 74HC154, actif bas, validé par DAMP_EN_N.", 2, 33, 1.5)
    b.text("Bit 3 d'adresse : MUX_EN_H (bobines 9 à 16).", 2, 35, 1.5)
    u1 = b.place("U1", 16, 14)
    for pin in ("1", "2", "3", "21", "22", "23", "24", "12"):
        b.pin_label(u1, pin)
    for i, pin in DEC_HI_OUT.items():
        if i < n:
            b.pin_label(u1, pin)
        else:
            b.nc(u1, pin)
    u2 = b.place("U2", 44, 14)
    for pin in ("23", "22", "21", "20", "18", "19", "24", "12"):
        b.pin_label(u2, pin)
    for i, pin in DEC_LO_OUT.items():
        if i < n:
            b.pin_label(u2, pin)
        else:
            b.nc(u2, pin)
    for i, ref in enumerate(("C5", "C6")):
        c = b.place(ref, 24 + 4 * i, 28.5)
        b.pin_label(c, "1")
        b.pin_label(c, "2")
    b.text("Multiplexeurs", 58, 1)
    b.text("Multiplexeurs : les deux bornes de la bobine adressée vers l'INA, "
           "sorties en parallèle, un enable par boîtier.", 2, 37, 1.5)
    for idx, (ref, _first, _en) in enumerate(mux_refs(n)):
        _mux(b, ref, 70, 16 + 36 * idx, n)
        c = b.place("C7" if idx == 0 else "C8", 84, 16 + 36 * idx)
        b.pin_label(c, "1")
        b.pin_label(c, "2")


# ---------------------------------------------------------------- chain
def draw_chain(sheet: Sheet, by_ref: dict, chain: ChainDesign) -> None:
    b = _Block(sheet, by_ref, 2, 2)
    b.text("Chaîne d'amplification", 2, 1)
    b.text(
        f"AD8421 G = {chain.ina_gain:g}, passe-haut {chain.hp.fc_hz / 1e3:.0f} kHz, "
        f"passe-bas {chain.lp.fc_hz / 1e3:.0f} kHz, sortie x {chain.out_gain:g}, "
        f"gain total {chain.total_gain:.0f} à mi-bande, centré sur VREF.",
        2,
        28,
        1.5,
    )
    c15 = b.place("C15", 7.5, 8, rot=90)  # pin 1 (6, 8) from the mux, pin 2 (9, 8)
    b.pin_label(c15, "1")
    b.wire((9, 8), (17, 8))
    r13 = b.place("R13", 12, 6.5, rot=180, fields="left")  # pin 1 (12, 8), pin 2 up to VREF
    b.pin_label(r13, "2")
    c14 = b.place("C14", 7.5, 12, rot=90)
    b.pin_label(c14, "1")
    b.wire((9, 12), (17, 12))
    r12 = b.place("R12", 12, 13.5, fields="left")  # pin 1 (12, 12), pin 2 down to VREF
    b.pin_label(r12, "2")
    b.label("INA_INM", 13, 8, "r", "local")
    b.label("INA_INP", 10, 12, "r", "local")
    u5 = b.place("U5", 20, 10)  # -IN (17, 8), RG (17, 9) (17, 11), +IN (17, 12), out (25, 10)
    b.place("R14", 14, 10, fields="left")  # pins (14, 8.5) and (14, 11.5)
    b.wire((17, 9), (14, 9), (14, 8.5))
    b.wire((17, 11), (14, 11), (14, 11.5))
    b.label("RG_A", 15, 9, "r", "local")
    b.label("RG_B", 15, 11, "r", "local")
    b.pin_label(u5, "8")
    b.pin_label(u5, "5")
    b.wire((22, 13), (22, 14), (24, 14))
    b.label("VREF", 24, 14, "r")
    c16 = b.place("C16", 27, 5)
    b.pin_label(c16, "1")
    b.pin_label(c16, "2")
    b.wire((25, 10), (31, 10))
    b.label("INA_OUT", 26, 10, "r", "local")
    # Sallen-Key high-pass
    b.place("C17", 32.5, 10, rot=90)  # pins (31, 10) (34, 10)
    b.wire((34, 10), (37, 10))
    b.label("HP_N1", 34.5, 10, "r", "local")
    b.place("R15", 34, 7.5, rot=180)  # pin 1 (34, 9) on HP_N1, pin 2 (34, 6) on HP_OUT
    b.wire((34, 9), (34, 10))
    b.place("C18", 38.5, 10, rot=90)  # pins (37, 10) (40, 10)
    b.wire((40, 10), (43, 10))
    b.label("HP_IN", 40, 10, "r", "local")
    r16 = b.place("R16", 41, 11.5)  # pin 1 (41, 10), pin 2 (41, 13) to VREF
    b.pin_label(r16, "2")
    b.place("U7", 46, 11, unit=1)  # + (43, 10), - (43, 12), out (49, 11)
    b.wire((49, 11), (53, 11))
    b.wire((52, 11), (52, 5), (34, 5), (34, 6))
    b.label("HP_OUT", 40, 5, "r", "local")
    b.wire((52, 11), (52, 16), (47, 16))
    b.place("R17", 45.5, 16, rot=270)  # pin 1 (47, 16) HP_OUT, pin 2 (44, 16) HP_FB
    b.wire((43, 12), (43, 16), (44, 16))
    r18 = b.place("R18", 43, 17.5, fields="left")  # pin 1 (43, 16), pin 2 (43, 19) to VREF
    b.pin_label(r18, "2")
    b.label("HP_FB", 43, 14, "r", "local")
    # Sallen-Key low-pass
    b.place("R19", 54.5, 11, rot=90)  # pins (53, 11) (56, 11)
    b.wire((56, 11), (60, 11))
    b.label("LP_N1", 57, 11, "r", "local")
    b.place("C19", 56, 8.5, rot=180)  # pin 1 (56, 10) on LP_N1, pin 2 (56, 7) on LP_OUT
    b.wire((56, 10), (56, 11))
    b.place("R20", 61.5, 11, rot=90)  # pins (60, 11) (63, 11)
    b.wire((63, 11), (66, 11))
    b.label("LP_IN", 63, 11, "r", "local")
    c20 = b.place("C20", 64, 12.5)  # pin 1 (64, 11), pin 2 (64, 14) to VREF
    b.pin_label(c20, "2")
    b.place("U7", 69, 12, unit=2)  # + (66, 11), - (66, 13), out (72, 12)
    b.wire((72, 12), (78, 12))
    b.wire((75, 12), (75, 6), (56, 6), (56, 7))
    b.label("LP_OUT", 62, 6, "r", "local")
    b.wire((75, 12), (75, 17), (70, 17))
    b.place("R21", 68.5, 17, rot=270)  # pin 1 (70, 17) LP_OUT, pin 2 (67, 17) LP_FB
    b.wire((66, 13), (66, 17), (67, 17))
    r22 = b.place("R22", 66, 18.5, fields="left")
    b.pin_label(r22, "2")
    b.label("LP_FB", 66, 15, "r", "local")
    # output stage, RC and clamp to the ADC
    b.place("U8", 81, 13, unit=2)  # + (78, 12), - (78, 14), out (84, 13)
    b.wire((78, 14), (78, 18), (79, 18))
    r24 = b.place("R24", 78, 19.5, fields="left")
    b.pin_label(r24, "2")
    b.label("OUT_FB", 78, 16, "r", "local")
    b.place("R23", 80.5, 18, rot=270)  # pin 1 (82, 18) OUT_STAGE, pin 2 (79, 18) OUT_FB
    b.wire((82, 18), (87, 18), (87, 13))
    b.wire((84, 13), (91, 13))
    b.label("OUT_STAGE", 87, 15, "r", "local")
    b.place("R25", 92.5, 13, rot=90)  # pins (91, 13) (94, 13)
    b.wire((94, 13), (100, 13))
    c24 = b.place("C24", 95, 14.5)
    b.pin_label(c24, "2")
    d3 = b.place("D3", 98, 9)  # pin 3 (98, 11) down to AMP_OUT
    b.wire((98, 11), (98, 13))
    b.pin_label(d3, "1")
    b.pin_label(d3, "2")
    b.place("TP1", 100, 13)
    b.label("AMP_OUT", 100, 13, "d")
    u7c = b.place("U7", 46, 22, unit=3)
    b.pin_label(u7c, "8")
    b.pin_label(u7c, "4")
    c21 = b.place("C21", 50, 22.5)
    b.pin_label(c21, "1")
    b.pin_label(c21, "2")


# ---------------------------------------------------------------- LEDs
def draw_leds(sheet: Sheet, by_ref: dict, n_led: int) -> None:
    b = _Block(sheet, by_ref, 2, 2)
    b.text("LED de camp", 2, 1)
    per_row, step, row_h = 8, 12, 14
    rows = math.ceil(n_led / per_row)
    b.text("WS2812B, deux par case, chaînées dans l'ordre du serpentin des rangées.",
           2, rows * row_h + 5, 1.5)
    for i in range(1, n_led + 1):
        row, col = divmod(i - 1, per_row)
        cx, cy = 8 + col * step, 6 + row * row_h
        ld = b.place(f"LD{i}", cx, cy)  # VDD up, DOUT right, VSS down, DIN left
        b.pin_label(ld, "1")
        b.pin_label(ld, "3")
        if i == 1:
            b.pin_label(ld, "4")
        elif col == 0:
            b.stub(ld, "4", 4.0)
            b.label(f"LED_L{i - 1}", cx - 7, cy, "r", "local")
        if i == n_led:
            b.pin_label(ld, "2")
        elif col == per_row - 1:
            b.stub(ld, "2", 4.0)
            b.label(f"LED_L{i}", cx + 3, cy, "r", "local")
        else:
            b.wire((cx + 3, cy), (cx + 9, cy))
            b.label(f"LED_L{i}", cx + 4, cy, "r", "local")
        c = b.place(f"CL{i}", cx + 6, cy + 6)
        b.pin_label(c, "1")
        b.pin_label(c, "2")


# ---------------------------------------------------------------- root
def quadrant_schematic(
    cfg: BoardConfig, ckt: Circuit, chain: ChainDesign, project: str
) -> Schematic:
    n = coil_count(cfg)
    s = cfg.plateau.quadrant.squares
    by_ref = {c.ref: c for c in ckt.components}
    root = Sheet(project, f"Quadrant {s} x {s}", paper="A4")
    rails = Sheet("rails", "Alimentations, VREF et rail d'impulsion", "A4")
    draw_rails(rails, by_ref)
    cells: list[Sheet] = []
    for i in range(math.ceil(n / CELLS_PER_SHEET)):
        first, last = i * CELLS_PER_SHEET + 1, min((i + 1) * CELLS_PER_SHEET, n)
        sh = Sheet(f"cells-{i + 1}", f"Cellules de bobine {first} à {last}", "A3")
        draw_cells(sh, by_ref, first, last)
        cells.append(sh)
    select = Sheet("select", "Sélection : décodeurs et multiplexeurs", "A4")
    draw_select(select, by_ref, n)
    amp = Sheet("chain", "Chaîne d'amplification", "A4")
    draw_chain(amp, by_ref, chain)
    leds = Sheet("leds", "LED de camp", "A4")
    draw_leds(leds, by_ref, 2 * n)

    b = _Block(root, by_ref, 2, 2)
    b.text(f"Quadrant {s} x {s} : liaison au cerveau (J1) et feuilles par fonction", 2, 2, 3.0)
    b.text("Étiquettes globales : rails, bus d'adresse et nets partagés entre feuilles ; "
           "étiquettes locales : nets internes à une feuille.", 2, 5, 1.5)
    j1 = b.place("J1", 12, 24)  # pins at x = 10, y = 17 .. 32
    for i in range(16):
        b.pin_label(j1, str(i + 1))
    for idx, sh in enumerate([rails, *cells, select, amp, leds]):
        x, y = b.p(30, 8 + idx * 7)
        root.subsheet(sh, x, y, 46 * G, 5 * G)
    return Schematic(project, root)
