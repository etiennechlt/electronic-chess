"""Complete netlist of the mockup analog board.

Single source of the circuit: every generator (schematic, PCB, BOM,
SPICE) consumes this description. Pin numbers follow the official
KiCad symbols, which were probed for every part; the builder validates
each mapping against the symbol so a typo fails loudly.

Topology summary (ADR 0008):
- coil joint -> per-coil cell: bleed biasing to VREF, series clamp
  resistors and BAV99 to the analog rails in front of the mux, bus
  diode + low-side FET excitation from a shared switched 12 V rail,
  SS34 flyback clamp, P-FET + resistor active damping (also the idle
  load of unselected coils);
- 74HC4052 dual 4:1 differential mux -> AC coupling -> AD8421 (G 20)
  -> Sallen-Key HP 200 kHz -> SK LP 650 kHz -> output gain stage
  -> RC + clamp -> MCU header;
- power: 12 V jack -> TPS62150 buck 2.5 MHz (DEF jumper for forced
  PWM) -> filtered rail, or LP2985 LDO; jumper selects the analog
  source (measurement 8);
- ADuM1201 isolated UART to a Pi Zero header, with 0 ohm bypasses.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from chessboard_calc.config import BoardConfig

from .filters import ChainDesign, design_chain
from .symlib import Symbol, load_symbol

GND = "GND"


@dataclass(frozen=True)
class Part:
    lib: str
    symbol: str
    footprint: str
    mpn: str = ""
    lcsc: str = ""


@dataclass
class Component:
    ref: str
    part: Part
    value: str
    pins: dict[str, str]           # pin number -> net name
    nc: tuple[str, ...] = ()       # pin numbers deliberately unconnected
    dnp: bool = False
    sym: Symbol | None = None


@dataclass
class Circuit:
    components: list[Component] = field(default_factory=list)
    nets: dict[str, list[tuple[str, str]]] = field(default_factory=dict)

    def add(self, ref: str, part: Part, value: str, pins: dict[str, str],
            nc: tuple[str, ...] = (), dnp: bool = False) -> Component:
        sym = load_symbol(part.lib, part.symbol)
        known = {p.number for p in sym.pins}
        mapped = set(pins) | set(nc)
        if not set(pins) <= known:
            raise ValueError(f"{ref}: unknown pins {set(pins) - known} for {sym.lib_id}")
        if mapped != known:
            raise ValueError(f"{ref}: unmapped pins {known - mapped} for {sym.lib_id}")
        comp = Component(ref=ref, part=part, value=value, pins=dict(pins),
                         nc=tuple(nc), dnp=dnp, sym=sym)
        self.components.append(comp)
        for number, net in pins.items():
            self.nets.setdefault(net, []).append((ref, number))
        return comp


# Parts catalog: lib symbol, footprint, purchasable references.
FP_R0603 = "Resistor_SMD:R_0603_1608Metric"
FP_C0603 = "Capacitor_SMD:C_0603_1608Metric"
FP_C1206 = "Capacitor_SMD:C_1206_3216Metric"

R = Part("Device", "R", FP_R0603)
R2512 = Part("Device", "R", "Resistor_SMD:R_2512_6332Metric")
C = Part("Device", "C", FP_C0603)
C1206 = Part("Device", "C", FP_C1206)
CP = Part("Device", "C_Polarized_US", "Capacitor_SMD:CP_Elec_6.3x7.7")
FB = Part("Device", "FerriteBead", "Resistor_SMD:R_0805_2012Metric",
          mpn="BLM21PG221SN1D", lcsc="C18305")
LBUCK = Part("Device", "L", "Inductor_SMD:L_Bourns-SRN4018",
             mpn="SRN4018TA2R2M", lcsc="C2827538")

BUCK = Part("Regulator_Switching", "TPS62150",
            "Package_DFN_QFN:QFN-16-1EP_3x3mm_P0.5mm_EP1.75x1.75mm",
            mpn="TPS62150RGTR", lcsc="C72631")
LDO = Part("Regulator_Linear", "LP2985-5.0", "Package_TO_SOT_SMD:SOT-23-5",
           mpn="LP2985AIM5-5.0", lcsc="C129541")
# HCT and not HC: TTL input thresholds keep the 3.3 V MCU valid against
# the 5 V analog supply of the mux.
MUX = Part("4xxx", "4052", "Package_SO:TSSOP-16_4.4x5mm_P0.65mm",
           mpn="74HCT4052PW", lcsc="C57078")
INA = Part("Amplifier_Instrumentation", "AD8421ARZ",
           "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", mpn="AD8421ARZ", lcsc="C462186")
OPA = Part("Amplifier_Operational", "OPA2156xD",
           "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", mpn="OPA2810IDR", lcsc="C2059830")
ISO = Part("Isolator", "ADuM1201AR", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
           mpn="ADuM1201ARZ", lcsc="C123211")
NFET = Part("Transistor_FET", "AO3400A", "Package_TO_SOT_SMD:SOT-23",
            mpn="AO3400A", lcsc="C20917")
PFET = Part("Transistor_FET", "AO3401A", "Package_TO_SOT_SMD:SOT-23",
            mpn="AO3401A", lcsc="C15127")
DSS34 = Part("Diode", "SS34", "Diode_SMD:D_SMA", mpn="SS34", lcsc="C8678")
DBUS = Part("Device", "D_Schottky", "Diode_SMD:D_SOD-123", mpn="B5819W", lcsc="C8598")
DDUAL = Part("Diode", "BAV99", "Package_TO_SOT_SMD:SOT-23", mpn="BAV99", lcsc="C2500")
DTVS = Part("Device", "D_TVS", "Diode_SMD:D_SMB", mpn="SMBJ15A", lcsc="C113962")

JACK = Part("Connector", "Barrel_Jack_Switch",
            "Connector_BarrelJack:BarrelJack_Horizontal",
            mpn="DC-005-5.5x2.1", lcsc="C381118")
H1X3 = Part("Connector_Generic", "Conn_01x03",
            "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical")
H1X10 = Part("Connector_Generic", "Conn_01x10",
             "Connector_PinHeader_2.54mm:PinHeader_1x10_P2.54mm_Vertical")
H2X10 = Part("Connector_Generic", "Conn_02x10_Odd_Even",
             "Connector_PinHeader_2.54mm:PinHeader_2x10_P2.54mm_Vertical")
H2X04 = Part("Connector_Generic", "Conn_02x04_Odd_Even",
             "Connector_PinHeader_2.54mm:PinHeader_2x04_P2.54mm_Vertical")
TP = Part("Connector", "TestPoint", "TestPoint:TestPoint_Pad_1.5x1.5mm")
HOLE = Part("Mechanical", "MountingHole_Pad",
            "MountingHole:MountingHole_3.2mm_M3_Pad")

# The coil joint pad order must match coilgen.board.PAD_PLAN.
JOINT_ORDER = [GND, "C1_A", "C1_B", "C3_A", "C3_B", "C4_A", "C4_B", "C2_A", "C2_B", GND]


def build_circuit(cfg: BoardConfig) -> tuple[Circuit, ChainDesign]:
    drv = cfg.mockup.drive
    chain = design_chain(cfg)
    ckt = Circuit()

    def r(ref, value, a, b, part=R, dnp=False):
        ckt.add(ref, part, value, {"1": a, "2": b}, dnp=dnp)

    def c(ref, value, a, b, part=C):
        ckt.add(ref, part, value, {"1": a, "2": b})

    # ---------------- Power input and rails ----------------
    ckt.add("J1", JACK, "12V", {"1": "VIN_JACK", "2": GND, "3": GND})
    ckt.add("D1", DSS34, "SS34", {"1": "VIN", "2": "VIN_JACK"})  # 1=K 2=A
    ckt.add("D2", DTVS, "SMBJ15A", {"1": GND, "2": "VIN"})       # 1=A? checked below
    ckt.add("C1", CP, "47u/25V", {"1": "VIN", "2": GND})
    c("C2", "10u/25V", "VIN", GND, part=C1206)
    c("C3", "100n", "VIN", GND)

    ckt.add("U1", BUCK, "TPS62150", {
        "1": "SW", "2": "SW", "3": "SW",
        "4": "BUCK_PG", "5": "BUCK_FB",
        "6": GND, "15": GND, "16": GND, "17": GND,
        "7": GND,               # FSW low: highest switching frequency
        "8": "BUCK_DEF",        # PWM/PFM selection via JP3
        "9": "BUCK_SS",
        "10": "VIN", "11": "VIN", "12": "VIN",
        "13": "BUCK_EN", "14": "5V_BUCK",
    })
    r("R1", "100k", "BUCK_EN", "VIN")
    c("C4", "3n3", "BUCK_SS", GND)
    r("R2", "100k", "BUCK_PG", "5V_BUCK")
    ckt.add("L1", LBUCK, "2u2", {"1": "SW", "2": "5V_BUCK"})
    r("R3", "523k", "5V_BUCK", "BUCK_FB")
    r("R4", "100k", "BUCK_FB", GND)
    c("C5", "22u/10V", "5V_BUCK", GND, part=C1206)
    c("C6", "22u/10V", "5V_BUCK", GND, part=C1206)
    ckt.add("JP3", H1X3, "DEF: 1 PFM / 3 FPWM", {"1": GND, "2": "BUCK_DEF", "3": "5V_BUCK"})

    ckt.add("FB1", FB, "BLM21PG221", {"1": "5V_BUCK", "2": "5V_BUCK_FILT"})
    c("C7", "10u/10V", "5V_BUCK_FILT", GND, part=C1206)
    c("C8", "100n", "5V_BUCK_FILT", GND)

    ckt.add("U2", LDO, "LP2985-5.0", {
        "1": "VIN", "2": GND, "3": "VIN", "4": "LDO_BP", "5": "5V_LDO",
    })
    c("C9", "10n", "LDO_BP", GND)
    c("C10", "2u2", "5V_LDO", GND)
    c("C11", "1u", "VIN", GND)

    ckt.add("JP1", H1X3, "5VA: 1 buck / 3 LDO", {
        "1": "5V_BUCK_FILT", "2": "5VA", "3": "5V_LDO",
    })
    c("C12", "10u/10V", "5VA", GND, part=C1206)

    # VREF bias generator and buffer (U6 unit A).
    r("R5", "20k5", "5VA", "VREF_DIV")
    r("R6", "10k", "VREF_DIV", GND)
    c("C13", "1u", "VREF_DIV", GND)

    # ---------------- Per-coil cells ----------------
    ckt.add("Q1", PFET, "AO3401A", {"1": "Q1_G", "2": "VIN", "3": "PULSE_RAIL"})
    r("R7", "10k", "Q1_G", "VIN")
    ckt.add("Q2", NFET, "AO3400A", {"1": "PULSE_EN", "2": GND, "3": "Q1_G"})
    r("R8", "100k", "PULSE_EN", GND)
    r("R9", "10R", "PULSE_RAIL", "DRIVE_BUS", part=R2512)
    r("R10", "100k", "DRIVE_BUS", GND)

    for k in range(1, 5):
        a, b = f"C{k}_A", f"C{k}_B"
        ma, mb = f"M{k}_A", f"M{k}_B"
        base = 10 + 10 * k  # R21.., R31.., R41.., R51..
        r(f"R{base + 1}", "10k", a, "VREF")
        r(f"R{base + 2}", "10k", b, "VREF")
        r(f"R{base + 3}", "330R", a, ma)
        r(f"R{base + 4}", "330R", b, mb)
        ckt.add(f"D{k + 10}", DDUAL, "BAV99", {"1": GND, "3": ma, "2": "5VA"})
        ckt.add(f"D{k + 20}", DDUAL, "BAV99", {"1": GND, "3": mb, "2": "5VA"})
        ckt.add(f"D{k + 30}", DBUS, "B5819W", {"1": a, "2": "DRIVE_BUS"})   # 1=K 2=A
        ckt.add(f"D{k + 40}", DSS34, "SS34", {"1": "VIN", "2": b})          # flyback
        ckt.add(f"Q{k + 10}", NFET, "AO3400A", {"1": f"DRIVE{k}", "2": GND, "3": b})
        r(f"R{base + 5}", "100k", f"DRIVE{k}", GND)
        ckt.add(f"Q{k + 20}", PFET, "AO3401A",
                {"1": f"DAMP{k}_N", "2": a, "3": f"DMP{k}"})
        r(f"R{base + 6}", str(int(drv.damp_r_ohm)) + "R", f"DMP{k}", b,
          part=Part("Device", "R", "Resistor_SMD:R_0805_2012Metric"))
        r(f"R{base + 7}", "100k", f"DAMP{k}_N", "5VA")

    # ---------------- Mux and amplifier chain ----------------
    ckt.add("U3", MUX, "74HC4052", {
        "12": "M1_A", "14": "M2_A", "15": "M3_A", "11": "M4_A",
        "1": "M1_B", "5": "M2_B", "2": "M3_B", "4": "M4_B",
        "13": "MUXA_OUT", "3": "MUXB_OUT",
        "10": "MUX_A0", "9": "MUX_A1", "6": "MUX_INH",
        "16": "5VA", "8": GND, "7": GND,
    })
    r("R11", "100k", "MUX_INH", "5VA")  # inhibited until the MCU drives

    c("C14", "100n", "MUXA_OUT", "INA_INP")
    c("C15", "100n", "MUXB_OUT", "INA_INM")
    r("R12", "100k", "INA_INP", "VREF")
    r("R13", "100k", "INA_INM", "VREF")
    ckt.add("U4", INA, "AD8421", {
        "1": "INA_INM", "4": "INA_INP", "2": "RG_A", "3": "RG_B",
        "5": GND, "8": "5VA", "6": "VREF", "7": "INA_OUT",
    })
    r("R14", "523R", "RG_A", "RG_B")
    c("C16", "100n", "5VA", GND)  # at U4

    hp, lp = chain.hp, chain.lp

    def fmt_r(v):
        return f"{v / 1000:.3g}k" if v >= 1000 else f"{v:.3g}R"

    def fmt_c(v):
        return f"{v * 1e9:.3g}n" if v >= 1e-9 else f"{v * 1e12:.3g}p"

    # SK high-pass, U5 unit A (pins 1,2,3).
    c("C17", fmt_c(hp.c_f), "INA_OUT", "HP_N1")
    c("C18", fmt_c(hp.c_f), "HP_N1", "HP_IN")
    r("R15", fmt_r(hp.r_ohm), "HP_N1", "HP_OUT")
    r("R16", fmt_r(hp.r_ohm), "HP_IN", "VREF")
    r("R17", fmt_r(hp.rf_ohm), "HP_OUT", "HP_FB")
    r("R18", fmt_r(hp.rg_ohm), "HP_FB", "VREF")
    # SK low-pass, U5 unit B (pins 5,6,7).
    r("R19", fmt_r(lp.r_ohm), "HP_OUT", "LP_N1")
    r("R20", fmt_r(lp.r_ohm), "LP_N1", "LP_IN")
    c("C19", fmt_c(lp.c_f), "LP_N1", "LP_OUT")
    c("C20", fmt_c(lp.c_f), "LP_IN", "VREF")
    r("R61", fmt_r(lp.rf_ohm), "LP_OUT", "LP_FB")
    r("R62", fmt_r(lp.rg_ohm), "LP_FB", "VREF")
    ckt.add("U5", OPA, "OPA2810", {
        "3": "HP_IN", "2": "HP_FB", "1": "HP_OUT",
        "5": "LP_IN", "6": "LP_FB", "7": "LP_OUT",
        "8": "5VA", "4": GND,
    })
    c("C21", "100n", "5VA", GND)  # at U5

    # U6: unit A = VREF buffer, unit B = output gain stage.
    r("R63", fmt_r(chain.out_rf_ohm), "OUT_STAGE", "OUT_FB")
    r("R64", fmt_r(chain.out_rg_ohm), "OUT_FB", "VREF")
    ckt.add("U6", OPA, "OPA2810", {
        "3": "VREF_DIV", "2": "VREF", "1": "VREF",
        "5": "LP_OUT", "6": "OUT_FB", "7": "OUT_STAGE",
        "8": "5VA", "4": GND,
    })
    c("C22", "100n", "5VA", GND)  # at U6
    c("C23", "1u", "VREF", GND)

    r("R65", "49R9", "OUT_STAGE", "AMP_OUT")
    c("C24", "1n", "AMP_OUT", GND)
    ckt.add("D3", DDUAL, "BAV99", {"1": GND, "3": "AMP_OUT", "2": "3V3_NUCLEO"})

    # ---------------- UART isolation and Pi header ----------------
    ckt.add("U7", ISO, "ADuM1201", {
        "1": "3V3_NUCLEO", "4": GND,
        "3": "MCU_TX", "2": "MCU_RX",
        "8": "PI_3V3", "5": GND,
        "6": "PI_RXD", "7": "PI_TXD",
    })
    c("C25", "100n", "3V3_NUCLEO", GND)
    c("C26", "100n", "PI_3V3", GND)
    r("R66", "0R", "MCU_TX", "PI_RXD", dnp=True)
    r("R67", "0R", "PI_TXD", "MCU_RX", dnp=True)
    ckt.add("J5", H2X04, "PI ZERO", {
        "1": "5V_BUCK", "2": "5V_BUCK", "3": GND, "4": GND,
        "5": "PI_3V3", "6": "PI_TXD", "7": "PI_RXD", "8": GND,
    })

    # ---------------- Headers, test points, mechanics ----------------
    ckt.add("J2", H1X10, "COIL JOINT",
            {str(i + 1): net for i, net in enumerate(JOINT_ORDER)})
    ckt.add("J4", H2X10, "MCU", {
        "1": "3V3_NUCLEO", "2": GND,
        "3": "AMP_OUT", "4": GND,
        "5": "MUX_A0", "6": "MUX_A1",
        "7": "MUX_INH", "8": "PULSE_EN",
        "9": "DRIVE1", "10": "DRIVE2",
        "11": "DRIVE3", "12": "DRIVE4",
        "13": "DAMP1_N", "14": "DAMP2_N",
        "15": "DAMP3_N", "16": "DAMP4_N",
        "17": "MCU_TX", "18": "MCU_RX",
        "19": GND, "20": "INA_OUT",
    })
    for ref, net in [("TP1", "INA_OUT"), ("TP2", "AMP_OUT"), ("TP3", "VREF"),
                     ("TP4", "5VA"), ("TP5", GND), ("TP6", "DRIVE_BUS")]:
        ckt.add(ref, TP, net, {"1": net})
    for i in range(1, 5):
        ckt.add(f"H{i}", HOLE, "M3", {"1": GND})
    return ckt, chain
