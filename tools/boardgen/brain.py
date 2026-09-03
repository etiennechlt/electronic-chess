"""The brain board (ADR 0010): STM32G474 soldered, four quadrant links,
LED chain driver, 5 V buck (2.5 MHz forced PWM), 3.3 V logic LDO, analog
LDO island for the quadrants, isolated UART to an ESP32-S3 module or a
Pi header, motion and power connectors, buzzer, status LEDs, USB-C, SWD.

Every pin assignment lives in config/board.yaml (plateau.brain.mcu_pins)
and is applied here by pin name against the official KiCad symbol.
120 x 80 mm, 4 layers: F.Cu parts and signals, In1 ground pour, In2
power and long signals, B.Cu signals.
"""

from __future__ import annotations

from analoggen.circuit import (
    C1206,
    CP,
    DDUAL,
    DSS34,
    FB,
    ISO,
    LDO,
    NFET,
    PFET,
    TP,
    C,
    Circuit,
    Part,
    R,
)
from analoggen.symlib import load_symbol

from chessboard_calc.config import BoardConfig

from .core import GenericBoard, Spec, pins_by_name, shelf

GND = "GND"

# ESP32-S3-WROOM-1 placed with rotation 270: its body runs from x - 12.75
# to x + 12.75, the antenna occupies the last 6 mm (x + 6.75 onward), the
# pad rows sit at y - 9 and y + 9. On the brain the antenna hangs past the
# east edge, the module sits 1 mm inside the south edge.
ESP32_X, ESP32_Y = 113.25, 70.0
ESP32_ANTENNA_FROM, ESP32_ANTENNA_TO, ESP32_HALF = 6.75, 12.75, 9.5
# GenericBoard options shared by the build and the tests
BOARD_OPTIONS = {"overhang": ("U5",)}

MCU = Part(
    "MCU_ST_STM32G4",
    "STM32G474RETx",
    "Package_QFP:LQFP-64_10x10mm_P0.5mm",
    mpn="STM32G474RET6",
    lcsc="C528140",
)
BUCK3A = Part(
    "Regulator_Switching",
    "TPS62130",
    "Package_DFN_QFN:QFN-16-1EP_3x3mm_P0.5mm_EP1.75x1.75mm",
    mpn="TPS62130RGTR",
    lcsc="C74016",
)
LBUCK = Part("Device", "L", "Inductor_SMD:L_Bourns_SRN6045TA", mpn="SRN6045TA-2R2M", lcsc="C167219")
LDO33 = Part(
    "Regulator_Linear",
    "AP2112K-3.3",
    "Package_TO_SOT_SMD:SOT-23-5",
    mpn="AP2112K-3.3TRG1",
    lcsc="C51118",
)
LDO33_1A = Part(
    "Regulator_Linear",
    "AMS1117-3.3",
    "Package_TO_SOT_SMD:SOT-223-3_TabPin2",
    mpn="AMS1117-3.3",
    lcsc="C6186",
)
ESP32 = Part(
    "RF_Module",
    "ESP32-S3-WROOM-1",
    "RF_Module:ESP32-S3-WROOM-1",
    mpn="ESP32-S3-WROOM-1-N8",
    lcsc="C2913204",
)
USBC = Part(
    "Connector",
    "USB_C_Receptacle_USB2.0_16P",
    "Connector_USB:USB_C_Receptacle_GCT_USB4085",
    mpn="USB4085-GF-A",
    lcsc="C2988369",
)
ESD = Part(
    "Power_Protection",
    "USBLC6-2SC6",
    "Package_TO_SOT_SMD:SOT-23-6",
    mpn="USBLC6-2SC6",
    lcsc="C7519",
)
BUF5 = Part(
    "74xGxx", "74AHCT1G125", "Package_TO_SOT_SMD:SOT-23-5", mpn="SN74AHCT1G125DBVR", lcsc="C350557"
)
FPC16 = Part(
    "Connector_Generic",
    "Conn_01x16",
    "Connector_FFC-FPC:Hirose_FH12-16S-0.5SH_1x16-1MP_P0.50mm_Horizontal",
    mpn="FH12-16S-0.5SH(55)",
    lcsc="C2837584",
)
SWD = Part(
    "Connector_Generic",
    "Conn_02x05_Odd_Even",
    "Connector_PinHeader_1.27mm:PinHeader_2x05_P1.27mm_Vertical",
)
H2X10 = Part(
    "Connector_Generic",
    "Conn_02x10_Odd_Even",
    "Connector_PinHeader_2.54mm:PinHeader_2x10_P2.54mm_Vertical",
)
H2X04 = Part(
    "Connector_Generic",
    "Conn_02x04_Odd_Even",
    "Connector_PinHeader_2.54mm:PinHeader_2x04_P2.54mm_Vertical",
)
H1X06 = Part(
    "Connector_Generic", "Conn_01x06", "Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical"
)
H1X03 = Part(
    "Connector_Generic", "Conn_01x03", "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical"
)
SW = Part(
    "Switch", "SW_Push", "Button_Switch_SMD:SW_SPST_PTS645", mpn="PTS645SM43SMTR92", lcsc="C221929"
)
LED = Part("Device", "LED", "LED_SMD:LED_0603_1608Metric", mpn="19-217/GHC-YR1S2/3T", lcsc="C72043")
BUZ = Part("Device", "Buzzer", "Buzzer_Beeper:Buzzer_12x9.5RM7.6", mpn="", lcsc="")
FUSE = Part("Device", "Fuse", "Fuse:Fuse_1206_3216Metric", mpn="", lcsc="")
HOLE = Part("Mechanical", "MountingHole_Pad", "MountingHole:MountingHole_3.2mm_M3_Pad")
C10U = Part("Device", "C", "Capacitor_SMD:C_1206_3216Metric")


def link_pinout(cfg: BoardConfig, k: int, led_in: str, led_out: str) -> list[str]:
    """Quadrant k link, the same order as the quadrant's own connector."""
    base = list(cfg.plateau.quadrant.link.pinout)
    out = []
    for net in base:
        if net == "AMP_OUT":
            out.append(f"AMP_OUT{k}")
        elif net == "LED_DIN":
            out.append(led_in)
        elif net == "LED_DOUT":
            out.append(led_out)
        else:
            out.append(net)
    return out


def build_brain_circuit(cfg: BoardConfig) -> Circuit:
    pins = cfg.plateau.brain.mcu_pins
    ckt = Circuit()

    def r(ref, value, a, b, part=R):
        ckt.add(ref, part, value, {"1": a, "2": b})

    def c(ref, value, a, b, part=C):
        ckt.add(ref, part, value, {"1": a, "2": b})

    # ---------------- MCU ----------------
    # PG10 is NRST and PB8 doubles as BOOT0 on the STM32G4 (no dedicated pins)
    mcu = {
        "VBAT": "3V3",
        "VDD": "3V3",
        "VDDA": "3V3A",
        "VREF+": "3V3A",
        "VSS": GND,
        "VSSA": GND,
        "PG10": "NRST",
        "PB8": "BOOT0",
    }
    # every GPIO of the pin table; the rest is left unconnected on purpose
    for signal, pin in pins.items():
        mcu[pin] = signal
    mapped = pins_by_name(MCU, mcu)
    all_pins = {p.number for p in load_symbol(MCU.lib, MCU.symbol).pins}
    ckt.add("U1", MCU, "STM32G474RE", mapped, nc=tuple(sorted(all_pins - set(mapped))))
    for i in range(1, 6):
        c(f"C{i}", "100n", "3V3", GND)
    c("C6", "4u7", "3V3", GND)
    r("R1", "0R", "3V3", "3V3A")  # ferrite-free island for VDDA
    c("C7", "1u", "3V3A", GND)
    c("C8", "10n", "3V3A", GND)
    r("R2", "10k", "BOOT0", GND)
    ckt.add("SW1", SW, "BOOT", {"1": "BOOT0", "2": "3V3"})
    c("C9", "100n", "NRST", GND)
    ckt.add("SW2", SW, "RESET", {"1": "NRST", "2": GND})
    # Cortex debug 10-pin: 6 (SWO) and 8 (TDI on JTAG probes) stay open, a
    # probe driving them must never reach the reset line
    ckt.add(
        "J6",
        SWD,
        "SWD",
        {
            "1": "3V3",
            "2": "SWDIO",
            "3": GND,
            "4": "SWCLK",
            "5": GND,
            "7": GND,
            "9": GND,
            "10": "NRST",
        },
        nc=("6", "8"),
    )
    # USB device: data through the ESD array, CC pulled down (UFP), VBUS
    # unused (the board runs from the pack), SBU pins unconnected
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
    ckt.add("J5", USBC, "USB-C", usb_pins, nc=tuple(sorted(usb_all - set(usb_pins))))
    r("R3", "5k1", "CC1", GND)
    r("R4", "5k1", "CC2", GND)
    ckt.add(
        "U9",
        ESD,
        "USBLC6-2",
        {"1": "USB_DM_C", "6": "USB_DM", "3": "USB_DP_C", "4": "USB_DP", "5": "VBUS", "2": GND},
    )
    r("R5", "22R", "USB_DM", "USB_DM_MCU")
    r("R6", "22R", "USB_DP", "USB_DP_MCU")

    # ---------------- Power: 5 V buck, 3.3 V LDO, analog island ----------------
    ckt.add("F1", FUSE, "2A", {"1": "VBAT_IN", "2": "VBAT"})
    c("C10", "10u/25V", "VBAT", GND, part=C10U)
    c("C11", "10u/25V", "VBAT", GND, part=C10U)
    ckt.add(
        "U2",
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
                "VIN": "VBAT",
                "EN": "BUCK_EN",
                "VOS": "5V",
            },
        ),
    )
    r("R7", "100k", "BUCK_EN", "VBAT")
    c("C12", "3n3", "BUCK_SS", GND)
    r("R8", "100k", "BUCK_PG", "5V")
    ckt.add("L1", LBUCK, "2u2", {"1": "SW", "2": "5V"})
    r("R9", "523k", "5V", "BUCK_FB")
    r("R10", "100k", "BUCK_FB", GND)
    c("C13", "22u/10V", "5V", GND, part=C10U)
    c("C14", "22u/10V", "5V", GND, part=C10U)
    ckt.add("U3", LDO33, "AP2112K-3.3", {"1": "5V", "2": GND, "3": "5V", "5": "3V3"}, nc=("4",))
    c("C15", "1u", "5V", GND)
    c("C16", "1u", "3V3", GND)
    ckt.add(
        "U4", LDO, "LP2985-5.0", {"1": "VBAT", "2": GND, "3": "VBAT", "4": "LDO_BP", "5": "5VA_RAW"}
    )
    c("C17", "10n", "LDO_BP", GND)
    c("C18", "2u2", "5VA_RAW", GND)
    ckt.add("FB1", FB, "BLM21PG221", {"1": "5VA_RAW", "2": "5VA"})
    c("C19", "10u/10V", "5VA", GND, part=C1206)
    c("C20", "100n", "5VA", GND)
    # LED rail: the buck output through its own fuse, bulk capacitor
    ckt.add("F2", FUSE, "2A", {"1": "5V", "2": "5V_LED"})
    ckt.add("C21", CP, "100u/10V", {"1": "5V_LED", "2": GND})
    # pulse rail for the quadrants: VBAT through a fuse and a bulk capacitor
    ckt.add("F3", FUSE, "1A", {"1": "VBAT", "2": "VIN"})
    ckt.add("C22", CP, "100u/25V", {"1": "VIN", "2": GND})

    # ---------------- LED chain driver ----------------
    ckt.add(
        "U8",
        BUF5,
        "74AHCT1G125",
        {"1": GND, "2": "LED_DIN_MCU", "3": GND, "4": "LED_DINB", "5": "5V"},
    )
    r("R11", "470R", "LED_DINB", "LED_DIN1")
    c("C23", "100n", "5V", GND)

    # ---------------- Quadrant links ----------------
    chain = ["LED_DIN1", "LED_L12", "LED_L23", "LED_L34", "LED_END"]
    for k in range(1, 5):
        nets = link_pinout(cfg, k, chain[k - 1], chain[k])
        ckt.add(f"J{k}", FPC16, f"QUADRANT {k}", {str(i + 1): n for i, n in enumerate(nets)})
    ckt.add("TP1", TP, "LED_END", {"1": "LED_END"})
    for k in range(1, 5):
        r(f"R{20 + k}", "49R9", f"AMP_OUT{k}", f"ADC{k}")
        c(f"C{30 + k}", "1n", f"ADC{k}", GND)

    # ---------------- Comms: isolated UART to the ESP32-S3 or a Pi ----------------
    ckt.add(
        "U6",
        ISO,
        "ADuM1201",
        {
            "1": "3V3",
            "4": GND,
            "3": "MCU_TX",
            "2": "MCU_RX",
            "8": "COMM_3V3",
            "5": GND,
            "6": "COMM_RXD",
            "7": "COMM_TXD",
        },
    )
    c("C24", "100n", "3V3", GND)
    c("C25", "100n", "COMM_3V3", GND)
    # load switch on the 5 V of the comms module (ADR 0003, 0005)
    ckt.add("Q1", PFET, "AO3401A", {"1": "Q1_G", "2": "5V", "3": "COMM_5V"})
    r("R12", "100k", "Q1_G", "5V")
    ckt.add("Q2", NFET, "AO3400A", {"1": "COMM_EN", "2": GND, "3": "Q1_G"})
    r("R13", "100k", "COMM_EN", GND)
    ckt.add("U7", LDO33_1A, "AMS1117-3.3", {"1": GND, "2": "ESP_3V3", "3": "COMM_5V"})
    c("C26", "10u/10V", "COMM_5V", GND, part=C1206)
    c("C27", "10u/10V", "ESP_3V3", GND, part=C1206)
    ckt.add(
        "JP1", H1X03, "COMM_3V3: 1 ESP / 3 PI", {"1": "ESP_3V3", "2": "COMM_3V3", "3": "PI_3V3"}
    )
    esp = {
        "GND": GND,
        "3V3": "ESP_3V3",
        "EN": "ESP_EN",
        "IO0": "ESP_IO0",
        "TXD0": "ESP_TXD",
        "RXD0": "ESP_RXD",
    }
    esp_pins = pins_by_name(ESP32, esp)
    esp_all = {p.number for p in load_symbol(ESP32.lib, ESP32.symbol).pins}
    ckt.add("U5", ESP32, "ESP32-S3-WROOM-1", esp_pins, nc=tuple(sorted(esp_all - set(esp_pins))))
    r("R14", "10k", "ESP_EN", "ESP_3V3")
    c("C28", "1u", "ESP_EN", GND)
    r("R15", "10k", "ESP_IO0", "ESP_3V3")
    ckt.add("SW3", SW, "ESP BOOT", {"1": "ESP_IO0", "2": GND})
    ckt.add("SW4", SW, "ESP EN", {"1": "ESP_EN", "2": GND})
    # COMM_TXD feeds the isolator input (pin 7), COMM_RXD is its output
    # (pin 6): the module transmits into COMM_TXD and listens on COMM_RXD;
    # the zero ohm links come off when a Pi drives the header instead
    r("R16", "0R", "ESP_TXD", "COMM_TXD")
    r("R17", "0R", "COMM_RXD", "ESP_RXD")
    ckt.add(
        "J7",
        H1X06,
        "ESP PROG",
        {"1": "ESP_3V3", "2": GND, "3": "ESP_EN", "4": "ESP_IO0", "5": "ESP_TXD", "6": "ESP_RXD"},
    )
    ckt.add(
        "J8",
        H2X04,
        "PI ZERO",
        {
            "1": "COMM_5V",
            "2": "COMM_5V",
            "3": GND,
            "4": GND,
            "5": "PI_3V3",
            "6": "COMM_RXD",
            "7": "COMM_TXD",
            "8": GND,
        },
    )

    # ---------------- Motion and power boards ----------------
    ckt.add(
        "J9",
        H2X10,
        "MOTION",
        {
            "1": "VBAT",
            "2": "VBAT",
            "3": GND,
            "4": GND,
            "5": "STEP1",
            "6": "DIR1",
            "7": "STEP2",
            "8": "DIR2",
            "9": "MOT_EN",
            "10": "TMC_TX",
            "11": "TMC_RX",
            "12": "ENDSTOP_X",
            "13": "ENDSTOP_Y",
            "14": "SERVO",
            "15": "5V",
            "16": "3V3",
            "17": GND,
            "18": GND,
            "19": "MOT_ALARM",
            "20": "MOT_DIAG",
        },
    )
    ckt.add(
        "J10",
        H2X04,
        "POWER",
        {
            "1": "VBAT_IN",
            "2": "VBAT_IN",
            "3": GND,
            "4": GND,
            "5": "I2C_SCL",
            "6": "I2C_SDA",
            "7": "CHG_STAT",
            "8": "PWR_KEY",
        },
    )
    r("R18", "4k7", "I2C_SCL", "3V3")
    r("R19", "4k7", "I2C_SDA", "3V3")
    r("R20", "10k", "ENDSTOP_X", "3V3")
    r("R26", "10k", "ENDSTOP_Y", "3V3")

    # ---------------- Human interface ----------------
    ckt.add("BZ1", BUZ, "12 mm", {"1": "5V", "2": "BUZ_DRV"})
    ckt.add("Q3", NFET, "AO3400A", {"1": "BUZZER", "2": GND, "3": "BUZ_DRV"})
    r("R27", "100k", "BUZZER", GND)
    ckt.add("D1", DSS34, "SS34", {"1": "5V", "2": "BUZ_DRV"})  # flyback across the buzzer coil
    for i, net in enumerate(("LED_STAT1", "LED_STAT2", "LED_STAT3", "LED_STAT4"), start=2):
        ckt.add(f"D{i}", LED, "LED", {"1": f"LED{i}_K", "2": "3V3"})
        r(f"R{30 + i}", "1k", f"LED{i}_K", net)
    ckt.add("SW5", SW, "USER", {"1": "USER_BTN", "2": GND})
    r("R40", "10k", "USER_BTN", "3V3")
    ckt.add("D6", DDUAL, "BAV99", {"1": GND, "3": "PWR_KEY", "2": "3V3"})
    for ref, net in (("TP2", "5VA"), ("TP3", "5V"), ("TP4", "3V3"), ("TP5", GND), ("TP6", "VIN")):
        ckt.add(ref, TP, net, {"1": net})
    for i in range(1, 5):
        ckt.add(f"H{i}", HOLE, "M3", {"1": GND})
    return ckt


SPEC = Spec(
    name="brain",
    title="Damier LC, cerveau",
    width=120.0,
    height=80.0,
    layers=4,
    clearance=0.15,
    track=0.3,
    power_track=0.8,
    via_pad=0.8,
    via_drill=0.4,
    gnd_layer="In1.Cu",
    power_nets=(
        "VBAT",
        "VBAT_IN",
        "VIN",
        "5V",
        "5V_LED",
        "5VA",
        "5VA_RAW",
        "3V3",
        "COMM_5V",
        "ESP_3V3",
        "SW",
    ),
)


def antenna_keepout(gb: GenericBoard, at: tuple[float, float, float], width: float) -> None:
    """No copper on any layer under the part of the module antenna that
    lies over the board (rotation 270: antenna toward +x); nothing to do
    when the antenna hangs entirely past the edge."""
    ux, uy, _rot = at
    x0, x1 = ux + ESP32_ANTENNA_FROM, min(width, ux + ESP32_ANTENNA_TO)
    if x1 - x0 > 0.5:
        gb.keepout_rect(x0, uy - ESP32_HALF, x1, uy + ESP32_HALF, "antenna")


def brain_placements(ckt: Circuit) -> dict[str, tuple[float, float, float]]:
    W, H = SPEC.width, SPEC.height
    out: dict[str, tuple[float, float, float]] = {}
    # north edge: the four quadrant links, cables leaving north
    for k in range(1, 5):
        out[f"J{k}"] = (16.0 + (k - 1) * 22.0, 5.4, 180.0)
    out["TP1"] = (106.0, 4.0, 0.0)
    # west column: USB-C (cable west), ESD, SWD, buttons
    out["J5"] = (5.6, 24.0, 90.0)
    out["U9"] = (18.0, 24.0, 0.0)
    out["J6"] = (19.0, 14.0, 0.0)
    out["SW2"] = (14.0, 36.0, 0.0)
    out["SW1"] = (14.0, 46.0, 0.0)
    out["SW5"] = (14.0, 56.0, 0.0)
    # MCU in the west half, decoupling packed right under it, ADC filters above
    out["U1"] = (38.0, 40.0, 0.0)
    out.update(
        shelf(
            [
                "C1",
                "C2",
                "C3",
                "C4",
                "C5",
                "C6",
                "C7",
                "C8",
                "R1",
                "R2",
                "C9",
                "R5",
                "R6",
                "R3",
                "R4",
            ],
            ckt,
            24.0,
            56.0,
            49.5,
            upright=True,
        )
    )
    out.update(
        shelf(
            ["R21", "R22", "R23", "R24", "C31", "C32", "C33", "C34"],
            ckt,
            26.0,
            56.0,
            13.0,
            upright=True,
        )
    )
    # LED driver, isolator, load switch, ESP regulator in the middle band
    out.update(
        shelf(
            ["U8", "R11", "C23", "U6", "C24", "C25", "Q1", "Q2", "R12", "R13", "R16", "R17"],
            ckt,
            58.0,
            84.0,
            12.0,
        )
    )
    out["U7"] = (64.0, 30.0, 0.0)
    out.update(
        shelf(
            ["C26", "C27", "JP1", "R14", "C28", "R15", "R18", "R19", "R20", "R26"],
            ckt,
            58.0,
            84.0,
            36.0,
            upright=True,
        )
    )
    # analog island and test points
    out.update(
        shelf(
            ["U4", "C17", "C18", "FB1", "C19", "C20", "TP2", "TP3", "TP4", "TP5", "TP6"],
            ckt,
            58.0,
            84.0,
            50.0,
            upright=True,
        )
    )
    # power block, north-east: buck, LDO, fuses, bulk capacitors
    out.update(
        shelf(
            [
                "U2",
                "L1",
                "C10",
                "C11",
                "C13",
                "C14",
                "R7",
                "C12",
                "R8",
                "R9",
                "R10",
                "U3",
                "C15",
                "C16",
                "F1",
                "F2",
                "F3",
                "C21",
                "C22",
            ],
            ckt,
            86.0,
            118.0,
            10.0,
        )
    )
    # comms: ESP32 module on the east edge, its antenna (the last 6 mm of
    # the module) past the board edge as Espressif recommends; the KiCad
    # courtyard is the 15 mm antenna clearance and keeps every other part
    # off the south-east corner. Pi header north of it, buttons and header
    # west of it.
    out["U5"] = (ESP32_X, ESP32_Y, 270.0)
    out["J8"] = (106.0, 32.0, 0.0)
    out["J7"] = (80.0, 62.0, 0.0)
    out["SW3"] = (70.0, 75.0, 0.0)
    out["SW4"] = (58.0, 75.0, 0.0)
    # south edge: motion and power connectors, buzzer, LEDs
    out["J9"] = (27.0, 74.5, 90.0)
    out["J10"] = (94.0, 77.5, 180.0)
    out["BZ1"] = (14.0, 66.0, 0.0)
    out.update(
        shelf(
            ["Q3", "R27", "D1", "D2", "D3", "D4", "D5", "R32", "R33", "R34", "R35", "R40", "D6"],
            ckt,
            36.0,
            76.0,
            60.0,
        )
    )
    # the fourth hole leaves the south-east corner to the radio module
    for i, (x, y) in enumerate(((5.0, 5.0), (W - 5.0, 5.0), (5.0, H - 5.0), (W - 5.0, 42.5)), 1):
        out[f"H{i}"] = (x, y, 0.0)
    return out


def build_brain(cfg: BoardConfig):
    ckt = build_brain_circuit(cfg)
    placements = brain_placements(ckt)
    if (
        tuple(cfg.plateau.brain.board_mm) != (SPEC.width, SPEC.height)
        or cfg.plateau.brain.layers != SPEC.layers
    ):
        raise ValueError("plateau.brain.board_mm / layers disagree with boardgen.brain.SPEC")
    gb = GenericBoard(SPEC, ckt, placements, generator="boardgen", **BOARD_OPTIONS)
    gb.place_all()
    antenna_keepout(gb, placements["U5"], SPEC.width)
    gb.route_all()
    return gb.finish(
        texts=[
            ("DAMIER LC / CERVEAU", 60.0, 78.5, "F.SilkS", 1.5),
            ("quadrants 1..4", 50.0, 10.5, "F.SilkS", 1.0),
        ]
    )


def schematic_groups() -> list[tuple[str, float, list[str]]]:
    return [
        (
            "MCU",
            40.0,
            [
                "U1",
                "C1",
                "C2",
                "C3",
                "C4",
                "C5",
                "C6",
                "R1",
                "C7",
                "C8",
                "R2",
                "SW1",
                "C9",
                "SW2",
                "J6",
            ],
        ),
        ("USB", 100.0, ["J5", "R3", "R4", "U9", "R5", "R6"]),
        (
            "POWER",
            150.0,
            [
                "F1",
                "C10",
                "C11",
                "U2",
                "R7",
                "C12",
                "R8",
                "L1",
                "R9",
                "R10",
                "C13",
                "C14",
                "U3",
                "C15",
                "C16",
                "U4",
                "C17",
                "C18",
                "FB1",
                "C19",
                "C20",
                "F2",
                "C21",
                "F3",
                "C22",
            ],
        ),
        (
            "QUADRANT LINKS",
            210.0,
            [
                "U8",
                "R11",
                "C23",
                "J1",
                "J2",
                "J3",
                "J4",
                "TP1",
                "R21",
                "C31",
                "R22",
                "C32",
                "R23",
                "C33",
                "R24",
                "C34",
            ],
        ),
        (
            "COMMS",
            280.0,
            [
                "U6",
                "C24",
                "C25",
                "Q1",
                "R12",
                "Q2",
                "R13",
                "U7",
                "C26",
                "C27",
                "JP1",
                "U5",
                "R14",
                "C28",
                "R15",
                "SW3",
                "SW4",
                "R16",
                "R17",
                "J7",
                "J8",
            ],
        ),
        ("MOTION AND POWER BOARDS", 350.0, ["J9", "J10", "R18", "R19", "R20", "R26"]),
        (
            "INTERFACE",
            400.0,
            [
                "BZ1",
                "Q3",
                "R27",
                "D1",
                "D2",
                "R32",
                "D3",
                "R33",
                "D4",
                "R34",
                "D5",
                "R35",
                "SW5",
                "R40",
                "D6",
                "TP2",
                "TP3",
                "TP4",
                "TP5",
                "TP6",
                "H1",
                "H2",
                "H3",
                "H4",
            ],
        ),
    ]
