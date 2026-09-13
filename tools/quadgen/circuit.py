"""Complete netlist of the quadrant board (ADR 0010, note 17).

Single source for the schematic, the strip placement, the BOM and the
SPICE bench. Every part comes from the official KiCad symbols (pin
numbers validated by the Circuit builder) so a typo fails loudly.

Topology, per quadrant of n = squares^2 coils (16, or 4 for the reduced
development quadrant, plateau.quadrant.reduced):
- n coil cells reproduced from the mockup analog board (ADR 0008):
  bleed to VREF, 330 ohm clamps and BAV99 in front of the mux, bus
  diode plus low-side FET excitation from the shared switched rail,
  flyback diode to VIN, freewheel diode from GND (note 17, point 1: the
  coil current closes through it when the low-side FET opens, whatever
  the state of the rail switch), P-FET plus resistor damping driven
  straight by the decoder (note 17, point 2: no pull-up, a push-pull
  3.3 V output never lets the gate reach VIN);
- gates from two 4 to 16 decoders: 74HC4514 (active high) inhibited
  by PULSE_EN through an inverter for the excitation, 74HC154 (active
  low) enabled by DAMP_EN_N for the damping; outputs beyond n are
  left unconnected;
- one ADG1607 dual 8:1 mux per eight coils, outputs paralleled, one
  enable each (coils 1 to 8, 9 to 16), instead of the ADG726 the brief
  named; the reduced quadrant has the first one only;
- AD8421 (G 20), Sallen-Key high-pass and low-pass, output stage, RC
  and clamp to 3V3, exactly the validated mockup chain;
- the coils themselves are net ties on the board: the spiral copper is
  C{k}_A, the B.Cu escape C{k}_B, joined at the stacked terminal; the
  schematic draws them as inductors.
"""

from __future__ import annotations

from analoggen.circuit import (
    C1206,
    DBUS,
    DDUAL,
    INA,
    NFET,
    OPA,
    PFET,
    TP,
    C,
    Circuit,
    Part,
    R,
)
from analoggen.filters import ChainDesign, design_chain

from chessboard_calc.config import BoardConfig

GND = "GND"
NET_5V_LED = "5V_LED"

DFLY = Part("Diode", "SS34", "Diode_SMD:D_SOD-123F", mpn="SS34FL", lcsc="C2480216")
MUX8 = Part(
    "Analog_Switch",
    "ADG1607xCP",
    "Package_CSP:LFCSP-32-1EP_5x5mm_P0.5mm_EP3.1x3.1mm",
    mpn="ADG1607BCPZ",
    lcsc="",
)
DEC_HI = Part(
    "4xxx_IEEE", "4514", "Package_SO:TSSOP-24_4.4x7.8mm_P0.65mm", mpn="74HC4514PW", lcsc="C5615"
)
DEC_LO = Part(
    "74xx", "74LS154", "Package_SO:TSSOP-24_4.4x7.8mm_P0.65mm", mpn="74HC154PW", lcsc="C5613"
)
INV = Part(
    "74xGxx", "74LVC1G04", "Package_TO_SOT_SMD:SOT-23-5", mpn="SN74LVC1G04DBVR", lcsc="C7477"
)
LED = Part(
    "LED", "WS2812B", "LED_SMD:LED_WS2812B_PLCC4_5.0x5.0mm_P3.2mm", mpn="WS2812B", lcsc="C2761795"
)
# The spiral: an inductor on the schematic, a net tie footprint on the board.
COIL = Part("Device", "L", "quadgen:COIL_TIE")
R0402 = Part("Device", "R", "Resistor_SMD:R_0402_1005Metric")
R2010 = Part("Device", "R", "Resistor_SMD:R_2010_5025Metric")
FPC16 = Part("Connector_Generic", "Conn_01x16", "")  # footprint from the yaml
HOLE = Part("Mechanical", "MountingHole", "MountingHole:MountingHole_3.2mm_M3")

# 74HC4514 output pin per decoded index, 74HC154 likewise.
DEC_HI_OUT = {
    0: "11", 1: "9", 2: "10", 3: "8", 4: "7", 5: "6", 6: "5", 7: "4",
    8: "18", 9: "17", 10: "20", 11: "19", 12: "14", 13: "13", 14: "16", 15: "15",
}  # fmt: skip
DEC_LO_OUT = {i: str(i + 1) for i in range(11)} | {i: str(i + 2) for i in range(11, 16)}
MUX_NC = ("11", "12", "13", "26", "28", "30", "32")


def coil_count(cfg: BoardConfig) -> int:
    return cfg.plateau.quadrant.squares ** 2


def mux_refs(n: int) -> list[tuple[str, int, str]]:
    """(reference, first coil, enable net) of every ADG1607 the quadrant needs."""
    muxes = [("U3", 1, "MUX_EN_L")]
    if n > 8:
        muxes.append(("U4", 9, "MUX_EN_H"))
    return muxes


def cell_refs(k: int) -> dict[str, str]:
    """Reference designators of coil cell k (1..16): R101.., D101.., Q101.. so
    they never collide with the global parts (R1..R99)."""
    b = 100 + 10 * k
    return {
        "bleed_a": f"R{b + 1}",
        "bleed_b": f"R{b + 2}",
        "clamp_a": f"R{b + 3}",
        "clamp_b": f"R{b + 4}",
        "gate_pd": f"R{b + 5}",
        "damp_r": f"R{b + 6}",
        "dual_a": f"D{b + 1}",
        "dual_b": f"D{b + 2}",
        "bus": f"D{b + 3}",
        "fly": f"D{b + 4}",
        "free": f"D{b + 5}",
        "nfet": f"Q{b + 1}",
        "pfet": f"Q{b + 2}",
        "tie": f"NT{k}",
    }


def build_quadrant_circuit(cfg: BoardConfig) -> tuple[Circuit, ChainDesign]:
    q = cfg.plateau.quadrant
    drv = cfg.mockup.drive
    chain = design_chain(cfg)
    n = coil_count(cfg)
    ckt = Circuit()
    fpc = Part(FPC16.lib, FPC16.symbol, q.link.footprint, mpn="FH12-16S-0.5SH(55)", lcsc="C2837584")

    def r(ref, value, a, b, part=R):
        ckt.add(ref, part, value, {"1": a, "2": b})

    def c(ref, value, a, b, part=C):
        ckt.add(ref, part, value, {"1": a, "2": b})

    # ---------------- Link and rails ----------------
    ckt.add("J1", fpc, "FPC 16", {str(i + 1): net for i, net in enumerate(q.link.pinout)})
    c("C1", "10u/25V", "VIN", GND, part=C1206)
    c("C2", "10u/10V", "5VA", GND, part=C1206)
    c("C3", "100n", "3V3", GND)
    c("C4", "100n", "5VA", GND)

    # VREF bias generator, buffered by U8 unit A.
    r("R5", "20k5", "5VA", "VREF_DIV")
    r("R6", "10k", "VREF_DIV", GND)
    c("C13", "1u", "VREF_DIV", GND)

    # ---------------- Shared drive rail ----------------
    # Q1 must be off again before the listening window: R7 sets its
    # turn-off (470 ohms against the gate capacitance, under a
    # microsecond); the flyback no longer depends on it (note 17).
    ckt.add("Q1", PFET, "AO3401A", {"1": "Q1_G", "2": "VIN", "3": "PULSE_RAIL"})
    r("R7", "470R", "Q1_G", "VIN")
    ckt.add("Q2", NFET, "AO3400A", {"1": "PULSE_EN", "2": GND, "3": "Q1_G"})
    r("R8", "100k", "PULSE_EN", GND)
    r("R9", "10R", "PULSE_RAIL", "DRIVE_BUS", part=R2010)
    r("R10", "100k", "DRIVE_BUS", GND)

    # ---------------- Coil cells ----------------
    for k in range(1, n + 1):
        a, b = f"C{k}_A", f"C{k}_B"
        ma, mb = f"M{k}_A", f"M{k}_B"
        cr = cell_refs(k)
        ckt.add(cr["tie"], COIL, f"spirale C{k}", {"1": a, "2": b})
        r(cr["bleed_a"], "10k", a, "VREF", part=R0402)
        r(cr["bleed_b"], "10k", b, "VREF", part=R0402)
        r(cr["clamp_a"], "330R", a, ma, part=R0402)
        r(cr["clamp_b"], "330R", b, mb, part=R0402)
        ckt.add(cr["dual_a"], DDUAL, "BAV99", {"1": GND, "3": ma, "2": "5VA"})
        ckt.add(cr["dual_b"], DDUAL, "BAV99", {"1": GND, "3": mb, "2": "5VA"})
        ckt.add(cr["bus"], DBUS, "B5819W", {"1": a, "2": "DRIVE_BUS"})  # 1=K 2=A
        ckt.add(cr["fly"], DFLY, "SS34FL", {"1": "VIN", "2": b})  # flyback to VIN
        ckt.add(cr["free"], DBUS, "B5819W", {"1": a, "2": GND})  # freewheel from GND
        ckt.add(cr["nfet"], NFET, "AO3400A", {"1": f"DRIVE{k}", "2": GND, "3": b})
        r(cr["gate_pd"], "100k", f"DRIVE{k}", GND, part=R0402)
        ckt.add(cr["pfet"], PFET, "AO3401A", {"1": f"DAMP{k}_N", "2": a, "3": f"DMP{k}"})
        r(cr["damp_r"], str(int(drv.damp_r_ohm)) + "R", f"DMP{k}", b)

    # ---------------- Decoders ----------------
    ckt.add("U6", INV, "74LVC1G04", {"2": "PULSE_EN", "4": "PULSE_EN_N", "5": "3V3", "3": GND})
    # 74HC4514: transparent latch (EL high), outputs low while ~EN is high.
    dec_hi = {
        "1": "3V3",
        "23": "PULSE_EN_N",
        "2": "MUX_A0",
        "3": "MUX_A1",
        "21": "MUX_A2",
        "22": "MUX_EN_H",
        "24": "3V3",
        "12": GND,
    }
    nc_hi = []
    for i, pin in DEC_HI_OUT.items():
        if i < n:
            dec_hi[pin] = f"DRIVE{i + 1}"
        else:
            nc_hi.append(pin)
    ckt.add("U1", DEC_HI, q.front_end.drive_decoder, dec_hi, nc=tuple(nc_hi))
    # 74HC154: outputs active low, E0 tied low, E1 = DAMP_EN_N.
    dec_lo = {
        "18": GND,
        "19": "DAMP_EN_N",
        "23": "MUX_A0",
        "22": "MUX_A1",
        "21": "MUX_A2",
        "20": "MUX_EN_H",
        "24": "3V3",
        "12": GND,
    }
    nc_lo = []
    for i, pin in DEC_LO_OUT.items():
        if i < n:
            dec_lo[pin] = f"DAMP{i + 1}_N"
        else:
            nc_lo.append(pin)
    ckt.add("U2", DEC_LO, q.front_end.damp_decoder, dec_lo, nc=tuple(nc_lo))
    c("C5", "100n", "3V3", GND)
    c("C6", "100n", "3V3", GND)

    # ---------------- Muxes ----------------
    for ref, first, en in mux_refs(n):
        pins = {
            "27": "MUXA_OUT",
            "31": "MUXB_OUT",
            "15": "MUX_A0",
            "14": "MUX_A1",
            "10": "MUX_A2",
            "16": en,
            "29": "5VA",
            "25": GND,
            "33": GND,
            "9": GND,
        }
        nc = list(MUX_NC)
        for i in range(8):
            coil = first + i
            if coil <= n:
                pins[str(17 + i)] = f"M{coil}_A"  # S1A..S8A
                pins[str(8 - i)] = f"M{coil}_B"  # S1B..S8B
            else:
                nc += [str(17 + i), str(8 - i)]
        ckt.add(ref, MUX8, "ADG1607", pins, nc=tuple(nc))
    c("C7", "100n", "5VA", GND)
    if n > 8:
        c("C8", "100n", "5VA", GND)

    # ---------------- Amplifier chain (mockup values) ----------------
    c("C14", "100n", "MUXA_OUT", "INA_INP")
    c("C15", "100n", "MUXB_OUT", "INA_INM")
    r("R12", "100k", "INA_INP", "VREF")
    r("R13", "100k", "INA_INM", "VREF")
    ckt.add(
        "U5",
        INA,
        "AD8421",
        {
            "1": "INA_INM",
            "4": "INA_INP",
            "2": "RG_A",
            "3": "RG_B",
            "5": GND,
            "8": "5VA",
            "6": "VREF",
            "7": "INA_OUT",
        },
    )
    r("R14", "523R", "RG_A", "RG_B")
    c("C16", "100n", "5VA", GND)
    hp, lp = chain.hp, chain.lp

    def fmt_r(v):
        return f"{v / 1000:.3g}k" if v >= 1000 else f"{v:.3g}R"

    def fmt_c(v):
        return f"{v * 1e9:.3g}n" if v >= 1e-9 else f"{v * 1e12:.3g}p"

    c("C17", fmt_c(hp.c_f), "INA_OUT", "HP_N1")
    c("C18", fmt_c(hp.c_f), "HP_N1", "HP_IN")
    r("R15", fmt_r(hp.r_ohm), "HP_N1", "HP_OUT")
    r("R16", fmt_r(hp.r_ohm), "HP_IN", "VREF")
    r("R17", fmt_r(hp.rf_ohm), "HP_OUT", "HP_FB")
    r("R18", fmt_r(hp.rg_ohm), "HP_FB", "VREF")
    r("R19", fmt_r(lp.r_ohm), "HP_OUT", "LP_N1")
    r("R20", fmt_r(lp.r_ohm), "LP_N1", "LP_IN")
    c("C19", fmt_c(lp.c_f), "LP_N1", "LP_OUT")
    c("C20", fmt_c(lp.c_f), "LP_IN", "VREF")
    r("R21", fmt_r(lp.rf_ohm), "LP_OUT", "LP_FB")
    r("R22", fmt_r(lp.rg_ohm), "LP_FB", "VREF")
    ckt.add(
        "U7",
        OPA,
        "OPA2810",
        {
            "3": "HP_IN",
            "2": "HP_FB",
            "1": "HP_OUT",
            "5": "LP_IN",
            "6": "LP_FB",
            "7": "LP_OUT",
            "8": "5VA",
            "4": GND,
        },
    )
    c("C21", "100n", "5VA", GND)
    r("R23", fmt_r(chain.out_rf_ohm), "OUT_STAGE", "OUT_FB")
    r("R24", fmt_r(chain.out_rg_ohm), "OUT_FB", "VREF")
    ckt.add(
        "U8",
        OPA,
        "OPA2810",
        {
            "3": "VREF_DIV",
            "2": "VREF",
            "1": "VREF",
            "5": "LP_OUT",
            "6": "OUT_FB",
            "7": "OUT_STAGE",
            "8": "5VA",
            "4": GND,
        },
    )
    c("C22", "100n", "5VA", GND)
    c("C23", "1u", "VREF", GND)
    r("R25", "49R9", "OUT_STAGE", "AMP_OUT")
    c("C24", "1n", "AMP_OUT", GND)
    ckt.add("D3", DDUAL, "BAV99", {"1": GND, "3": "AMP_OUT", "2": "3V3"})

    # ---------------- Camp LEDs (placed by the board builder) ----------------
    n_led = 2 * n
    links = ["LED_DIN"] + [f"LED_L{i}" for i in range(1, n_led)] + ["LED_DOUT"]
    for i in range(1, n_led + 1):
        ckt.add(
            f"LD{i}", LED, "WS2812B", {"1": NET_5V_LED, "3": GND, "4": links[i - 1], "2": links[i]}
        )
        c(f"CL{i}", "100n", NET_5V_LED, GND)

    for ref, net in (("TP1", "AMP_OUT"), ("TP2", "VREF"), ("TP3", "DRIVE_BUS"), ("TP4", GND)):
        ckt.add(ref, TP, net, {"1": net})
    return ckt, chain


STRIP_REFS_PER_CELL = (
    "bleed_a",
    "bleed_b",
    "clamp_a",
    "clamp_b",
    "gate_pd",
    "damp_r",
    "dual_a",
    "dual_b",
    "bus",
    "fly",
    "free",
    "nfet",
    "pfet",
)


def schematic_groups(cfg: BoardConfig) -> list[tuple[str, float, list[str]]]:
    """Functional groups for the label-only emitter (analoggen.schematic)."""
    n = coil_count(cfg)
    groups: list[tuple[str, float, list[str]]] = [
        (
            "LINK AND RAILS",
            40.0,
            [
                "J1",
                "C1",
                "C2",
                "C3",
                "C4",
                "R5",
                "R6",
                "C13",
                "Q1",
                "R7",
                "Q2",
                "R8",
                "R9",
                "R10",
                "U6",
            ],
        ),
    ]
    y = 95.0
    for k in range(1, n + 1):
        cr = cell_refs(k)
        groups.append((f"COIL CELL {k}", y, [cr["tie"]] + [cr[r] for r in STRIP_REFS_PER_CELL]))
        y += 45.0
    groups.append(("DECODERS", y, ["U1", "U2", "C5", "C6"]))
    groups.append(("MUXES", y + 60.0, [ref for ref, _f, _e in mux_refs(n)] + ["C7", "C8"]))
    groups.append(
        (
            "AMPLIFIER CHAIN",
            y + 120.0,
            [
                "C14",
                "C15",
                "R12",
                "R13",
                "U5",
                "R14",
                "C16",
                "C17",
                "C18",
                "R15",
                "R16",
                "R17",
                "R18",
                "R19",
                "R20",
                "C19",
                "C20",
                "R21",
                "R22",
                "U7",
                "C21",
                "R23",
                "R24",
                "U8",
                "C22",
                "C23",
                "R25",
                "C24",
                "D3",
            ],
        )
    )
    leds = [f"LD{i}" for i in range(1, 2 * n + 1)] + [f"CL{i}" for i in range(1, 2 * n + 1)]
    groups.append(("CAMP LEDS", y + 175.0, leds[:32]))
    groups.append(("CAMP LEDS, DECOUPLING", y + 220.0, leds[32:]))
    groups.append(("TEST POINTS", y + 265.0, ["TP1", "TP2", "TP3", "TP4"]))
    return groups
