"""Motion board (optional, lives in the gantry base): two TMC2209
SilentStepStick sockets, motor and endstop connectors, magnet actuator
servo, bulk capacitors, IDC link to the brain. 80 x 50 mm, 2 layers.

The stepstick pinout is the Pololu-compatible one: left header EN, MS1,
MS2, PDN_UART, PDN_UART, CLK, STEP, DIR; right header VM, GND, 2B, 2A,
1A, 1B, VIO, GND. UART addresses: driver 1 MS1 = MS2 = 0, driver 2
MS1 = 1 (address 1), single wire through a 1 k resistor.
"""

from __future__ import annotations

from analoggen.circuit import CP, TP, C, Circuit, Part, R

from chessboard_calc.config import BoardConfig

from .core import GenericBoard, Spec, shelf

GND = "GND"
H1X08 = Part(
    "Connector_Generic", "Conn_01x08", "Connector_PinHeader_2.54mm:PinHeader_1x08_P2.54mm_Vertical"
)
H2X10 = Part(
    "Connector_Generic",
    "Conn_02x10_Odd_Even",
    "Connector_PinHeader_2.54mm:PinHeader_2x10_P2.54mm_Vertical",
)
XH4 = Part("Connector_Generic", "Conn_01x04", "Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical")
XH3 = Part("Connector_Generic", "Conn_01x03", "Connector_JST:JST_XH_B3B-XH-A_1x03_P2.50mm_Vertical")
CP100 = Part("Device", "C_Polarized_US", "Capacitor_SMD:CP_Elec_8x10.5")
HOLE = Part("Mechanical", "MountingHole_Pad", "MountingHole:MountingHole_3.2mm_M3_Pad")


def build_motion_circuit(cfg: BoardConfig) -> Circuit:
    ckt = Circuit()

    def r(ref, value, a, b):
        ckt.add(ref, R, value, {"1": a, "2": b})

    for d in (1, 2):
        ms1 = "3V3" if d == 2 else GND
        ckt.add(
            f"J{d}A",
            H1X08,
            f"STEPSTICK {d} LOGIC",
            {
                "1": "MOT_EN",
                "2": ms1,
                "3": GND,
                "4": f"UART{d}",
                "5": f"UART{d}",
                "6": GND,
                "7": f"STEP{d}",
                "8": f"DIR{d}",
            },
        )
        ckt.add(
            f"J{d}B",
            H1X08,
            f"STEPSTICK {d} POWER",
            {
                "1": "VBAT",
                "2": GND,
                "3": f"M{d}_2B",
                "4": f"M{d}_2A",
                "5": f"M{d}_1A",
                "6": f"M{d}_1B",
                "7": "3V3",
                "8": GND,
            },
        )
        ckt.add(
            f"J{d + 2}",
            XH4,
            f"MOTOR {d}",
            {"1": f"M{d}_1A", "2": f"M{d}_1B", "3": f"M{d}_2A", "4": f"M{d}_2B"},
        )
        ckt.add(f"C{d}", CP100, "100u/25V", {"1": "VBAT", "2": GND})
        ckt.add(f"C{d + 2}", C, "100n", {"1": "VBAT", "2": GND})
        r(f"R{d}", "1k", "TMC_TX", f"UART{d}")
    r("R3", "0R", "UART1", "TMC_RX_1")
    r("R4", "0R", "UART2", "TMC_RX_2")
    r("R5", "0R", "TMC_RX_1", "TMC_RX")
    r("R6", "0R", "TMC_RX_2", "TMC_RX")  # both drivers answer on one wire, distinct addresses
    ckt.add("J5", XH3, "ENDSTOP X", {"1": GND, "2": "3V3", "3": "ENDSTOP_X"})
    ckt.add("J6", XH3, "ENDSTOP Y", {"1": GND, "2": "3V3", "3": "ENDSTOP_Y"})
    ckt.add("J7", XH3, "SERVO", {"1": "SERVO", "2": "5V", "3": GND})
    ckt.add("C5", C, "100n", {"1": "3V3", "2": GND})
    ckt.add("C6", CP, "47u/10V", {"1": "5V", "2": GND})
    ckt.add(
        "J8",
        H2X10,
        "BRAIN",
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
    r("R7", "10k", "MOT_ALARM", "3V3")
    r("R8", "10k", "MOT_DIAG", "3V3")
    for ref, net in (("TP1", "VBAT"), ("TP2", GND), ("TP3", "TMC_RX")):
        ckt.add(ref, TP, net, {"1": net})
    for i in range(1, 5):
        ckt.add(f"H{i}", HOLE, "M3", {"1": GND})
    return ckt


SPEC = Spec(
    name="motion",
    title="Damier LC, carte moteurs",
    width=90.0,
    height=60.0,
    layers=2,
    clearance=0.15,
    track=0.3,
    power_track=1.0,
    via_pad=0.8,
    via_drill=0.4,
    gnd_layer="B.Cu",
    power_nets=(
        "VBAT",
        "5V",
        "3V3",
        "M1_1A",
        "M1_1B",
        "M1_2A",
        "M1_2B",
        "M2_1A",
        "M2_1B",
        "M2_2A",
        "M2_2B",
    ),
)


def motion_placements(ckt: Circuit) -> dict[str, tuple[float, float, float]]:
    W, H = SPEC.width, SPEC.height
    out = {}
    # two stepstick sockets side by side: upright headers 15.24 mm apart
    for d, x0 in ((1, 10.0), (2, 44.0)):
        out[f"J{d}A"] = (x0, 30.0, 0.0)
        out[f"J{d}B"] = (x0 + 15.24, 30.0, 0.0)
    out["J8"] = (82.0, 22.0, 0.0)  # IDC to the brain, east edge
    out["C1"] = (16.0, 8.0, 0.0)  # bulk capacitors, north
    out["C2"] = (30.0, 8.0, 0.0)
    out.update(
        shelf(
            [
                "C3",
                "C4",
                "C5",
                "C6",
                "R1",
                "R2",
                "R3",
                "R4",
                "R5",
                "R6",
                "R7",
                "R8",
                "TP1",
                "TP2",
                "TP3",
            ],
            ckt,
            38.0,
            76.0,
            2.5,
            upright=True,
        )
    )
    out["J3"] = (16.0, 55.0, 0.0)  # motors, endstops, servo: south
    out["J5"] = (31.0, 52.0, 0.0)
    out["J4"] = (46.0, 55.0, 0.0)
    out["J7"] = (60.0, 55.0, 0.0)
    out["J6"] = (72.0, 55.0, 0.0)
    for i, (x, y) in enumerate(((5.0, 5.0), (W - 5.0, 5.0), (5.0, H - 5.0), (W - 5.0, H - 5.0)), 1):
        out[f"H{i}"] = (x, y, 0.0)
    return out


def build_motion(cfg: BoardConfig):
    ckt = build_motion_circuit(cfg)
    gb = GenericBoard(SPEC, ckt, motion_placements(ckt), generator="boardgen")
    gb.place_all()
    gb.route_all()
    return gb.finish(texts=[("DAMIER LC / MOTEURS", 45.0, 58.5, "F.SilkS", 1.2)])


def schematic_groups() -> list[tuple[str, float, list[str]]]:
    return [
        (
            "STEPSTICKS",
            40.0,
            [
                "J1A",
                "J1B",
                "J2A",
                "J2B",
                "C1",
                "C2",
                "C3",
                "C4",
                "R1",
                "R2",
                "R3",
                "R4",
                "R5",
                "R6",
            ],
        ),
        ("MOTORS, ENDSTOPS, SERVO", 110.0, ["J3", "J4", "J5", "J6", "J7", "C5", "C6"]),
        ("BRAIN LINK", 170.0, ["J8", "R7", "R8", "TP1", "TP2", "TP3", "H1", "H2", "H3", "H4"]),
    ]
