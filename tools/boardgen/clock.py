"""Rocker chess clock board: ESP32-S3-WROOM-1 (BLE to the board), one
18650 with a MCP73831 USB-C charger, 3.3 V LDO, 2.4 inch SPI TFT header,
rocker microswitches, rotary encoder, buzzer, EN/BOOT buttons, programming
header, battery divider. 110 x 60 mm, 2 layers.
"""

from __future__ import annotations

from analoggen.circuit import DDUAL, NFET, PFET, TP, C, Circuit, Part, R
from analoggen.fplib import load_footprint
from analoggen.symlib import load_symbol
from quadgen.strip import courtyard_box

from chessboard_calc.config import BoardConfig

from .brain import BUZ, ESP32, H1X06, LDO33, SW, USBC
from .core import GenericBoard, Spec, pins_by_name, shelf

GND = "GND"
# The clock cannot afford the 15 mm antenna clearance of the library
# courtyard on every side: the encoder and a rocker switch sit beside the
# module. Only the antenna end keeps its clearance (past the board edge):
# BLE across a table, a short range this does not compromise.
ESP32_CLOCK_COURTYARD = (-10.0, -27.75, 10.0, 13.45)
# GenericBoard options shared by the build and the tests
BOARD_OPTIONS = {"overhang": ("U1",), "courtyards": {"U1": ESP32_CLOCK_COURTYARD}}
CHG = Part(
    "Battery_Management",
    "MCP73831-2-MC",
    "Package_DFN_QFN:DFN-8-1EP_2x3mm_P0.5mm_EP0.61x2.2mm",
    mpn="MCP73831T-2ACI/MC",
    lcsc="C424093",
)
CELL = Part("Device", "Battery_Cell", "Battery:BatteryHolder_Keystone_1042_1x18650")
TFT = Part(
    "Connector_Generic", "Conn_01x14", "Connector_PinHeader_2.54mm:PinHeader_1x14_P2.54mm_Vertical"
)
ENC = Part(
    "Device",
    "RotaryEncoder_Switch",
    "Rotary_Encoder:RotaryEncoder_Alps_EC11E-Switch_Vertical_H20mm",
    mpn="EC11E15244B2",
)
SWBIG = Part("Switch", "SW_Push", "Button_Switch_THT:SW_PUSH_6mm_H4.3mm", mpn="TS-1187A")
H1X02 = Part(
    "Connector_Generic", "Conn_01x02", "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical"
)
LED = Part("Device", "LED", "LED_SMD:LED_0603_1608Metric")
HOLE = Part("Mechanical", "MountingHole_Pad", "MountingHole:MountingHole_3.2mm_M3_Pad")

# ESP32-S3 GPIO assignment of the clock (all on the module's free pins)
ESP_PINS = {
    "IO4": "TFT_CS",
    "IO5": "TFT_DC",
    "IO6": "TFT_RST",
    "IO7": "TFT_LED_N",  # backlight, through the high side P-FET, active low
    "IO15": "SPI_SCK",
    "IO16": "SPI_MOSI",
    "IO17": "SPI_MISO",
    "IO8": "T_CS",
    "IO18": "T_IRQ",
    "IO9": "ENC_A",
    "IO10": "ENC_B",
    "IO11": "ENC_SW",
    "IO12": "SW_WHITE",
    "IO13": "SW_BLACK",
    "IO14": "BUZZER",
    "IO1": "VBAT_SENSE",
    "IO2": "CHG_SENSE",  # charger STAT (0 to 5 V) through the 56k / 100k divider
}


def build_clock_circuit(cfg: BoardConfig) -> Circuit:
    ckt = Circuit()

    def r(ref, value, a, b):
        ckt.add(ref, R, value, {"1": a, "2": b})

    def c(ref, value, a, b):
        ckt.add(ref, C, value, {"1": a, "2": b})

    # USB-C power only (data and SBU pins unconnected), 1S charger, cell, 3.3 V
    usb_pins = pins_by_name(
        USBC, {"GND": GND, "SHIELD": GND, "VBUS": "VBUS", "CC1": "CC1", "CC2": "CC2"}
    )
    usb_all = {p.number for p in load_symbol(USBC.lib, USBC.symbol).pins}
    ckt.add("J1", USBC, "USB-C", usb_pins, nc=tuple(sorted(usb_all - set(usb_pins))))
    r("R1", "5k1", "CC1", GND)
    r("R2", "5k1", "CC2", GND)
    ckt.add(
        "U2",
        CHG,
        "MCP73831",
        {
            "1": "VBUS",
            "2": "VBUS",
            "3": "VCELL",
            "4": "VCELL",
            "5": "CHG_STAT",
            "6": GND,
            "8": "PROG",
        },
        nc=("7",),
    )
    r("R3", "2k", "PROG", GND)  # 500 mA charge
    c("C1", "4u7", "VBUS", GND)
    c("C2", "4u7", "VCELL", GND)
    ckt.add("D1", LED, "CHG", {"1": "LED_CHG_K", "2": "VBUS"})
    r("R4", "1k", "LED_CHG_K", "CHG_STAT")
    # STAT swings to VBUS (5 V): divided to 3.2 V for the module, read low
    # when charging, low too without USB (pulled down, STAT high impedance)
    r("R15", "56k", "CHG_STAT", "CHG_SENSE")
    r("R16", "100k", "CHG_SENSE", GND)
    ckt.add("BT1", CELL, "18650", {"1": "VCELL", "2": GND})
    ckt.add("J2", H1X02, "POWER SWITCH", {"1": "VCELL", "2": "VSW"})
    ckt.add("U3", LDO33, "AP2112K-3.3", {"1": "VSW", "2": GND, "3": "VSW", "5": "3V3"}, nc=("4",))
    c("C3", "1u", "VSW", GND)
    c("C4", "10u", "3V3", GND)
    r("R5", "100k", "VSW", "VBAT_SENSE")
    r("R6", "100k", "VBAT_SENSE", GND)
    c("C5", "100n", "VBAT_SENSE", GND)

    # ESP32-S3 module
    esp = {
        "GND": GND,
        "3V3": "3V3",
        "EN": "ESP_EN",
        "IO0": "ESP_IO0",
        "TXD0": "ESP_TXD",
        "RXD0": "ESP_RXD",
        **ESP_PINS,
    }
    esp_pins = pins_by_name(ESP32, esp)
    esp_all = {p.number for p in load_symbol(ESP32.lib, ESP32.symbol).pins}
    ckt.add("U1", ESP32, "ESP32-S3-WROOM-1", esp_pins, nc=tuple(sorted(esp_all - set(esp_pins))))
    r("R7", "10k", "ESP_EN", "3V3")
    c("C6", "1u", "ESP_EN", GND)
    r("R8", "10k", "ESP_IO0", "3V3")
    ckt.add("SW1", SW, "BOOT", {"1": "ESP_IO0", "2": GND})
    ckt.add("SW2", SW, "EN", {"1": "ESP_EN", "2": GND})
    ckt.add(
        "J3",
        H1X06,
        "PROG",
        {"1": "3V3", "2": GND, "3": "ESP_EN", "4": "ESP_IO0", "5": "ESP_TXD", "6": "ESP_RXD"},
    )
    c("C7", "100n", "3V3", GND)
    c("C8", "22u", "3V3", GND)

    # display (2.4 inch ILI9341 module with touch, the usual 14-pin header)
    ckt.add(
        "J4",
        TFT,
        "TFT 2.4",
        {
            "1": "3V3",
            "2": GND,
            "3": "TFT_CS",
            "4": "TFT_RST",
            "5": "TFT_DC",
            "6": "SPI_MOSI",
            "7": "SPI_SCK",
            "8": "TFT_LED",
            "9": "SPI_MISO",
            "10": "SPI_SCK",
            "11": "T_CS",
            "12": "SPI_MOSI",
            "13": "SPI_MISO",
            "14": "T_IRQ",
        },
    )
    # backlight: the module's LED pin draws tens of mA, more than a GPIO
    # sources; a high side P-FET switches it from 3V3 (off while the module boots)
    ckt.add("Q2", PFET, "AO3401A", {"1": "TFT_LED_N", "2": "3V3", "3": "TFT_LED"})
    r("R17", "100k", "TFT_LED_N", "3V3")
    # rocker microswitches, encoder, buzzer
    ckt.add("SW3", SWBIG, "WHITE", {"1": "SW_WHITE", "2": GND})
    ckt.add("SW4", SWBIG, "BLACK", {"1": "SW_BLACK", "2": GND})
    r("R9", "10k", "SW_WHITE", "3V3")
    r("R10", "10k", "SW_BLACK", "3V3")
    ckt.add("SW5", ENC, "EC11", {"A": "ENC_A", "B": "ENC_B", "C": GND, "S1": "ENC_SW", "S2": GND})
    r("R11", "10k", "ENC_A", "3V3")
    r("R12", "10k", "ENC_B", "3V3")
    r("R13", "10k", "ENC_SW", "3V3")
    ckt.add("BZ1", BUZ, "12 mm", {"1": "VSW", "2": "BUZ_DRV"})
    ckt.add("Q1", NFET, "AO3400A", {"1": "BUZZER", "2": GND, "3": "BUZ_DRV"})
    r("R14", "100k", "BUZZER", GND)
    ckt.add("D2", DDUAL, "BAV99", {"1": GND, "3": "BUZ_DRV", "2": "VSW"})
    for ref, net in (("TP1", "3V3"), ("TP2", GND), ("TP3", "VSW")):
        ckt.add(ref, TP, net, {"1": net})
    for i in range(1, 5):
        ckt.add(f"H{i}", HOLE, "M3", {"1": GND})
    return ckt


SPEC = Spec(
    name="clock",
    title="Damier LC, horloge",
    width=110.0,
    height=60.0,
    layers=2,
    clearance=0.15,
    track=0.3,
    power_track=0.8,
    via_pad=0.8,
    via_drill=0.4,
    gnd_layer="B.Cu",
    power_nets=("VBUS", "VCELL", "VSW", "3V3"),
)


BOARD_OFFSET = 5.0  # the board sits 5 mm inside the housing walls, y from the front


def clock_placements(
    ckt: Circuit, cfg: BoardConfig | None = None
) -> dict[str, tuple[float, float, float]]:
    """Board frame: y grows toward the rear of the housing. The rocker
    microswitches and the encoder follow the housing (clock.rocker,
    clock.encoder in the yaml, minus the board offset)."""
    out = {}
    if cfg is not None:
        ck = cfg.clock
        half = ck.rocker.length_mm / 2.0 - ck.rocker.switch_inset_mm
        y_bar = (ck.slope_end_mm + ck.body_mm[1]) / 2.0 - BOARD_OFFSET
        sw_x = (
            ck.body_mm[0] / 2.0 - half - BOARD_OFFSET,
            ck.body_mm[0] / 2.0 + half - BOARD_OFFSET,
        )
        enc = (ck.encoder.x_mm - BOARD_OFFSET, 8.0)
    else:
        y_bar, sw_x, enc = 51.0, (13.0, 97.0), (99.0, 8.0)
    by_ref = {c.ref: c for c in ckt.components}

    def centered(ref: str, cx: float, cy: float) -> tuple[float, float, float]:
        """Origin placing the courtyard center (actuator, shaft) at (cx, cy)."""
        x0, y0, x1, y1 = courtyard_box(load_footprint(by_ref[ref].part.footprint))
        return (round(cx - (x0 + x1) / 2.0, 3), round(cy - (y0 + y1) / 2.0, 3), 0.0)

    out["SW3"] = centered("SW3", sw_x[0], y_bar)  # white side microswitch
    out["SW4"] = centered("SW4", sw_x[1], y_bar)  # black side
    out["SW5"] = centered("SW5", enc[0], enc[1])  # encoder, front right
    out["BT1"] = (45.5, 34.0, 0.0)  # 18650 holder across the middle
    out["U1"] = (103.5, 30.0, 270.0)  # module, east, antenna toward the edge
    out["J4"] = (55.0, 20.0, 90.0)  # TFT header under the display
    out["J1"] = (40.0, 54.5, 180.0)  # USB-C on the rear wall
    out["SW1"] = (24.0, y_bar, 0.0)  # BOOT
    out["SW2"] = (84.0, y_bar, 0.0)  # EN
    out["J2"] = (22.0, 57.0, 90.0)  # power switch header
    out["BZ1"] = (58.0, 52.0, 0.0)
    out["J3"] = (72.0, 56.5, 90.0)  # programming header
    out.update(
        shelf(
            [
                "U2",
                "R3",
                "C1",
                "C2",
                "D1",
                "R4",
                "R15",
                "R16",
                "R1",
                "R2",
                "U3",
                "C3",
                "C4",
                "R5",
                "R6",
                "C5",
            ],
            ckt,
            12.0,
            38.0,
            3.0,
            upright=True,
        )
    )
    out.update(
        shelf(
            [
                "R7",
                "C6",
                "R8",
                "C7",
                "C8",
                "R9",
                "R10",
                "R11",
                "R12",
                "R13",
                "Q1",
                "R14",
                "D2",
                "Q2",
                "R17",
            ],
            ckt,
            60.0,
            78.0,
            4.0,
            upright=True,
        )
    )
    out["TP1"], out["TP2"], out["TP3"] = (78.0, 16.0, 0.0), (82.0, 16.0, 0.0), (86.0, 16.0, 0.0)
    # the fourth hole sits between the cell holder, the buzzer and the EN
    # button: the east edge belongs to the module's antenna clearance area
    for i, (x, y) in enumerate(((5.0, 5.0), (83.0, 5.0), (5.0, 18.0), (73.0, 50.5)), 1):
        out[f"H{i}"] = (x, y, 0.0)
    return out


def build_clock(cfg: BoardConfig):
    ckt = build_clock_circuit(cfg)
    gb = GenericBoard(SPEC, ckt, clock_placements(ckt, cfg), generator="boardgen", **BOARD_OPTIONS)
    gb.place_all()
    gb.route_all()
    return gb.finish(texts=[("DAMIER LC / HORLOGE", 55.0, 58.5, "F.SilkS", 1.2)])


def schematic_groups() -> list[tuple[str, float, list[str]]]:
    return [
        (
            "POWER",
            40.0,
            [
                "J1",
                "R1",
                "R2",
                "U2",
                "R3",
                "C1",
                "C2",
                "D1",
                "R4",
                "R15",
                "R16",
                "BT1",
                "J2",
                "U3",
                "C3",
                "C4",
                "R5",
                "R6",
                "C5",
            ],
        ),
        ("ESP32-S3", 110.0, ["U1", "R7", "C6", "R8", "SW1", "SW2", "J3", "C7", "C8"]),
        (
            "DISPLAY AND INPUTS",
            180.0,
            [
                "J4",
                "Q2",
                "R17",
                "SW3",
                "SW4",
                "R9",
                "R10",
                "SW5",
                "R11",
                "R12",
                "R13",
                "BZ1",
                "Q1",
                "R14",
                "D2",
            ],
        ),
        ("TEST AND MECHANICAL", 240.0, ["TP1", "TP2", "TP3", "H1", "H2", "H3", "H4"]),
    ]
