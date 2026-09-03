"""Power board: 3S pack management. BQ24610 synchronous charger fed by a
20 V USB-C PD trigger module (or a 19 V adapter), BQ76920 analog front
end with low-side protection FETs, INA219 gauge on the pack output,
push button for wake-up, links to the brain and to the cells.
100 x 60 mm, 2 layers. The board never sees more than 1.5 A: AO3400A
everywhere, AO3401A for the two P-channel input FETs that the active
low ACDRV output of the BQ24610 drives.

Charger set points (BQ24610 datasheet, to confirm on the sheet before
fabrication): ICHG = V(ISET1) / (20 RSR), IPRE = ITERM = V(ISET2) /
(10 RSR), IIN = V(ACSET) / (20 RAC), VBAT = 2.1 V (1 + R14 / R15); the
TS window follows the 103AT example of the datasheet (RT1 5.24 k from
VREF, RT2 30.31 k to ground, 10 k NTC).
"""

from __future__ import annotations

from analoggen.circuit import C1206, NFET, PFET, TP, C, Circuit, Part, R
from analoggen.symlib import load_symbol

from chessboard_calc.config import BoardConfig

from .brain import H2X04, SW
from .core import GenericBoard, Spec, pins_by_name, shelf

GND = "GND"  # pack negative after the protection FETs (system ground)
BATN = "BAT-"  # cell 1 negative, AFE reference

CHG = Part(
    "Battery_Management",
    "BQ24610",
    "Package_DFN_QFN:QFN-24-1EP_4x4mm_P0.5mm_EP2.7x2.7mm",
    mpn="BQ24610RGER",
    lcsc="C130050",
)
AFE = Part(
    "Battery_Management",
    "BQ76920PW",
    "Package_SO:TSSOP-20_4.4x6.5mm_P0.65mm",
    mpn="BQ76920PWR",
    lcsc="C130052",
)
GAUGE = Part(
    "Sensor_Energy",
    "INA219BxD",
    "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
    mpn="INA219BIDR",
    lcsc="C138092",
)
LCHG = Part("Device", "L", "Inductor_SMD:L_Bourns_SRN6045TA", mpn="SRN6045TA-100M", lcsc="C167222")
RSENSE = Part("Device", "R", "Resistor_SMD:R_1206_3216Metric")
DTVS = Part("Device", "D_TVS", "Diode_SMD:D_SMB", mpn="SMBJ24A", lcsc="C113966")
XH2 = Part("Connector_Generic", "Conn_01x02", "Connector_JST:JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical")
XH4 = Part("Connector_Generic", "Conn_01x04", "Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical")
FUSE = Part("Device", "Fuse", "Fuse:Fuse_1206_3216Metric")
NTC = Part("Device", "Thermistor_NTC", "Resistor_SMD:R_0603_1608Metric", mpn="NCP18XH103F03RB")
HOLE = Part("Mechanical", "MountingHole_Pad", "MountingHole:MountingHole_3.2mm_M3_Pad")


def build_power_circuit(cfg: BoardConfig) -> Circuit:
    ckt = Circuit()

    def r(ref, value, a, b, part=R):
        ckt.add(ref, part, value, {"1": a, "2": b})

    def c(ref, value, a, b, part=C):
        ckt.add(ref, part, value, {"1": a, "2": b})

    # ---------------- Input: 20 V from the PD trigger module ----------------
    ckt.add("J1", XH2, "PD 20V IN", {"1": "VAD", "2": GND})
    ckt.add("D1", DTVS, "SMBJ24A", {"1": GND, "2": "VAD"})
    c("C1", "10u/50V", "VAD", GND, part=C1206)
    # input current sense and the back to back P-channel input FETs (common
    # drain, sources at ACN and at the charger input) that ~ACDRV pulls low
    r("R1", "10m", "VAD", "ACN", part=RSENSE)
    ckt.add("Q1", PFET, "AO3401A", {"1": "ACDRV", "2": "ACN", "3": "ACMID"})
    ckt.add("Q2", PFET, "AO3401A", {"1": "ACDRV", "2": "VCHG_IN", "3": "ACMID"})
    c("C2", "10u/50V", "VCHG_IN", GND, part=C1206)
    r("R2", "10R", "VAD", "VCC")
    c("C3", "1u", "VCC", GND)

    # ---------------- BQ24610 charger ----------------
    chg_pins = pins_by_name(
            CHG,
            {
                "ACN": "ACN",
                "ACP": "VAD",
                "~{ACDRV}": "ACDRV",
                "CE": "CHG_CE",
                "STAT1": "CHG_STAT",
                "TS": "TS",
                "TTC": "TTC",
                "~{PG}": "CHG_PG",
                "STAT2": "CHG_STAT2",
                "VREF": "VREF",
                "ISET1": "ISET1",
                "VFB": "VFB",
                "SRN": "SRN",
                "SRP": "SRP",
                "ISET2": "ISET2",
                "ACSET": "ACSET",
                "GND": GND,
                "REGN": "REGN",
                "LODRV": "LODRV",
                "PH": "PH",
                "HIDRV": "HIDRV",
                "BTST": "BTST",
                "VCC": "VCC",
            },
        )
    # no power path: the system runs from the pack, BATDRV stays unconnected
    chg_all = {p.number for p in load_symbol(CHG.lib, CHG.symbol).pins}
    ckt.add("U1", CHG, "BQ24610", chg_pins, nc=tuple(sorted(chg_all - set(chg_pins))))
    c("C4", "1u", "REGN", GND)
    c("C5", "1u", "VREF", GND)
    c("C6", "100n", "BTST", "PH")
    r("R3", "10k", "CHG_CE", "REGN")
    r("R4", "10k", "CHG_STAT", "3V3_BMS")
    r("R5", "10k", "CHG_STAT2", "3V3_BMS")
    r("R6", "10k", "CHG_PG", "3V3_BMS")
    c("C7", "100n", "TTC", GND)
    # TS window 0 to 45 C with a 10 k NTC: the datasheet's 103AT network
    # from VREF (RT1 5.24 k, RT2 30.31 k), nearest E96 values
    r("R7", "5k23", "VREF", "TS")
    r("R39", "30k1", "TS", GND)
    ckt.add("RT1", NTC, "10k NTC", {"1": "TS", "2": GND})
    # 50 mOhm sense: 1 A gives 50 mV, the range the ISET pins are made for
    r("R8", "100k", "VREF", "ISET1")  # 0.995 V: ICHG = 1.0 A
    r("R9", "43k2", "ISET1", GND)
    r("R10", "100k", "VREF", "ISET2")  # 0.101 V: precharge and termination 0.2 A
    r("R11", "3k16", "ISET2", GND)
    r("R12", "100k", "VREF", "ACSET")  # 0.499 V: input limit 2.5 A (20 V, 3 A source)
    r("R13", "17k8", "ACSET", GND)
    r("R14", "100k", "PACK+", "VFB")  # 12.6 V regulation: 2.1 V at VFB
    r("R15", "20k", "VFB", GND)
    c("C8", "100n", "VFB", GND)
    ckt.add("Q3", NFET, "AO3400A", {"1": "HIDRV", "2": "PH", "3": "VCHG_IN"})  # high side
    ckt.add("Q4", NFET, "AO3400A", {"1": "LODRV", "2": GND, "3": "PH"})
    ckt.add("L1", LCHG, "10u", {"1": "PH", "2": "SRP"})
    c("C9", "10u/25V", "SRP", GND, part=C1206)
    r("R17", "50m", "SRP", "SRN", part=RSENSE)
    c("C10", "10u/25V", "SRN", GND, part=C1206)
    r("R18", "0R", "SRN", "PACK+")

    # ---------------- BQ76920 analog front end, low side protection ----------------
    afe_pins = pins_by_name(
            AFE,
            {
                "DSG": "DSG",
                "CHG": "CHG",
                "VSS": BATN,
                "SDA": "SDA",
                "SCL": "SCL",
                "TS1": "TS1",
                "CAP1": "CAP1",
                "REGOUT": "3V3_BMS",
                "REGSRC": "REGSRC",
                "BAT": "BAT_F",
                "VC5": "CELL3_F",
                "VC4": "CELL3_F",
                "VC3": "CELL3_F",
                "VC2": "CELL2_F",
                "VC1": "CELL1_F",
                "VC0": BATN,
                "SRP": "AFE_SRP",
                "SRN": "AFE_SRN",
                "ALERT": "ALERT",
            },
        )
    afe_all = {p.number for p in load_symbol(AFE.lib, AFE.symbol).pins}
    ckt.add("U2", AFE, "BQ76920", afe_pins, nc=tuple(sorted(afe_all - set(afe_pins))))
    for i, cell in ((1, "CELL1"), (2, "CELL2"), (3, "CELL3")):
        r(f"R{20 + i}", "1k", cell, f"{cell}_F")
        c(f"C{10 + i}", "100n", f"{cell}_F", BATN if i == 1 else f"CELL{i - 1}_F")
    r("R24", "1k", "CELL3", "BAT_F")
    c("C14", "1u", "BAT_F", BATN)
    r("R25", "100R", "CELL3", "REGSRC")
    c("C15", "1u", "REGSRC", BATN)
    c("C16", "1u", "CAP1", BATN)
    c("C17", "1u", "3V3_BMS", BATN)
    r("R26", "10k", "TS1", "3V3_BMS")
    ckt.add("RT2", NTC, "10k NTC", {"1": "TS1", "2": BATN})
    r("R27", "5m", BATN, "PACK-PRE", part=RSENSE)  # AFE current sense
    r("R28", "1k", BATN, "AFE_SRP")
    r("R29", "1k", "PACK-PRE", "AFE_SRN")
    c("C18", "100n", "AFE_SRP", "AFE_SRN")
    # BQ76920 low side pair: the DSG FET's source sits on the cell side (its
    # driver is referenced to VSS), the CHG FET's source on PACK-; discharge
    # current flows through the CHG body diode and is blocked by DSG only,
    # charge current the other way round
    ckt.add("Q5", NFET, "AO3400A", {"1": "DSG_G", "2": "PACK-PRE", "3": "DSG_MID"})
    ckt.add("Q6", NFET, "AO3400A", {"1": "CHG_G", "2": GND, "3": "DSG_MID"})
    r("R30", "1k", "DSG", "DSG_G")
    r("R31", "1k", "CHG", "CHG_G")
    r("R32", "1M", "DSG_G", "PACK-PRE")
    r("R33", "1M", "CHG_G", GND)
    r("R34", "10k", "ALERT", "3V3_BMS")

    # ---------------- Gauge on the pack output, wake button, links ----------------
    r("R35", "10m", "CELL3", "PACK+", part=RSENSE)
    ckt.add(
        "U3",
        GAUGE,
        "INA219",
        {
            "1": BATN,
            "2": BATN,
            "3": "SDA",
            "4": "SCL",
            "5": "3V3_BMS",
            "6": BATN,
            "7": "PACK+",
            "8": "CELL3",
        },
    )
    c("C19", "100n", "3V3_BMS", BATN)
    r("R36", "4k7", "SDA", "3V3_BMS")
    r("R37", "4k7", "SCL", "3V3_BMS")
    ckt.add("F1", FUSE, "2A", {"1": "PACK+", "2": "VBAT_OUT"})
    ckt.add("J2", XH2, "POWER SWITCH", {"1": "VBAT_OUT", "2": "VBAT_SW"})
    ckt.add("SW1", SW, "WAKE", {"1": "PWR_KEY", "2": GND})
    r("R38", "100k", "PWR_KEY", "3V3_BMS")
    ckt.add(
        "J3",
        H2X04,
        "BRAIN",
        {
            "1": "VBAT_SW",
            "2": "VBAT_SW",
            "3": GND,
            "4": GND,
            "5": "SCL",
            "6": "SDA",
            "7": "CHG_STAT",
            "8": "PWR_KEY",
        },
    )
    ckt.add("J4", XH4, "CELLS", {"1": BATN, "2": "CELL1", "3": "CELL2", "4": "CELL3"})
    for ref, net in (("TP1", "PACK+"), ("TP2", GND), ("TP3", BATN), ("TP4", "3V3_BMS")):
        ckt.add(ref, TP, net, {"1": net})
    for i in range(1, 5):
        ckt.add(f"H{i}", HOLE, "M3", {"1": GND})
    return ckt


SPEC = Spec(
    name="power",
    title="Damier LC, carte puissance",
    width=100.0,
    height=60.0,
    layers=2,
    clearance=0.15,
    track=0.3,
    power_track=1.0,
    via_pad=0.8,
    via_drill=0.4,
    gnd_layer="B.Cu",
    power_nets=(
        "VAD",
        "ACN",
        "ACMID",
        "VCHG_IN",
        "PH",
        "SRP",
        "SRN",
        "PACK+",
        "VBAT_OUT",
        "VBAT_SW",
        "CELL3",
        "CELL2",
        "CELL1",
        "BAT-",
        "PACK-PRE",
        "DSG_MID",
    ),
)


def power_placements(ckt: Circuit) -> dict[str, tuple[float, float, float]]:
    W, H = SPEC.width, SPEC.height
    out = {}
    out["J1"] = (12.0, 12.0, 0.0)  # 20 V in, west
    out["J4"] = (11.0, 41.0, 0.0)  # cells, south-west
    out["J3"] = (90.0, 30.0, 90.0)  # brain link, east
    out["J2"] = (84.0, 10.0, 0.0)
    out["SW1"] = (84.0, 52.0, 0.0)
    out["U1"] = (36.0, 18.0, 0.0)  # charger
    out["L1"] = (54.0, 12.0, 0.0)
    out["U2"] = (36.0, 44.0, 0.0)  # AFE
    out["U3"] = (66.0, 44.0, 0.0)  # gauge
    out.update(
        shelf(
            [
                "D1",
                "C1",
                "R1",
                "Q1",
                "Q2",
                "C2",
                "R2",
                "C3",
                "C4",
                "C5",
                "C6",
                "R3",
                "R4",
                "R5",
                "R6",
                "C7",
                "R7",
                "RT1",
                "R8",
                "R9",
                "R10",
                "R11",
                "R12",
                "R13",
                "R14",
                "R15",
                "C8",
                "R39",
                "Q3",
                "Q4",
                "C9",
                "R17",
                "C10",
                "R18",
            ],
            ckt,
            14.0,
            84.0,
            22.0,
            upright=True,
        )
    )
    out.update(
        shelf(
            [
                "R21",
                "R22",
                "R23",
                "C11",
                "C12",
                "C13",
                "R24",
                "C14",
                "R25",
                "C15",
                "C16",
                "C17",
                "R26",
                "RT2",
                "R27",
                "R28",
                "R29",
                "C18",
                "Q5",
                "Q6",
                "R30",
                "R31",
                "R32",
                "R33",
                "R34",
                "R35",
                "C19",
                "R36",
                "R37",
                "F1",
                "R38",
                "TP1",
                "TP2",
                "TP3",
                "TP4",
            ],
            ckt,
            18.0,
            78.0,
            50.0,
            upright=True,
        )
    )
    for i, (x, y) in enumerate(((5.0, 5.0), (W - 5.0, 5.0), (5.0, H - 5.0), (W - 5.0, H - 5.0)), 1):
        out[f"H{i}"] = (x, y, 0.0)
    return out


def build_power(cfg: BoardConfig):
    ckt = build_power_circuit(cfg)
    gb = GenericBoard(SPEC, ckt, power_placements(ckt), generator="boardgen")
    gb.place_all()
    gb.route_all()
    return gb.finish(texts=[("DAMIER LC / PUISSANCE 3S", 50.0, 58.5, "F.SilkS", 1.2)])


def schematic_groups() -> list[tuple[str, float, list[str]]]:
    return [
        (
            "INPUT AND CHARGER",
            40.0,
            [
                "J1",
                "D1",
                "C1",
                "R1",
                "Q1",
                "Q2",
                "C2",
                "R2",
                "C3",
                "U1",
                "C4",
                "C5",
                "C6",
                "R3",
                "R4",
                "R5",
                "R6",
                "C7",
                "R7",
                "RT1",
                "R8",
                "R9",
                "R10",
                "R11",
                "R12",
                "R13",
                "R14",
                "R15",
                "C8",
                "R39",
                "Q3",
                "Q4",
                "L1",
                "C9",
                "R17",
                "C10",
                "R18",
            ],
        ),
        (
            "PROTECTION AFE",
            130.0,
            [
                "U2",
                "R21",
                "R22",
                "R23",
                "C11",
                "C12",
                "C13",
                "R24",
                "C14",
                "R25",
                "C15",
                "C16",
                "C17",
                "R26",
                "RT2",
                "R27",
                "R28",
                "R29",
                "C18",
                "Q5",
                "Q6",
                "R30",
                "R31",
                "R32",
                "R33",
                "R34",
            ],
        ),
        (
            "GAUGE, SWITCH, LINKS",
            210.0,
            [
                "R35",
                "U3",
                "C19",
                "R36",
                "R37",
                "F1",
                "J2",
                "SW1",
                "R38",
                "J3",
                "J4",
                "TP1",
                "TP2",
                "TP3",
                "TP4",
                "H1",
                "H2",
                "H3",
                "H4",
            ],
        ),
    ]
