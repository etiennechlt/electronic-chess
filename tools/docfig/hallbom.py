"""Purchase list and cost of the Hall layer of note 24, and of its RFID
variant, for the page and the note.

Quantities come from config/board.yaml (squares, quadrants, supply
groups, pieces); prices are market data and live in docs/prix-hall.csv
with a status and a source per line, the lines the plateau sheet already
prices (FET, passives) being read from docs/prix-plateau.csv. The spare
rule and the price reader are those of tools/bomagg.py, so the Hall
layer is costed exactly like the plateau.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from chessboard_calc.config import BoardConfig

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
PRICES_PLATEAU = ROOT / "docs" / "prix-plateau.csv"
PRICES_HALL = ROOT / "docs" / "prix-hall.csv"

USD_TO_EUR = 0.92  # the convention of the sourcing sheets (docs/bom-plateau.md)
VAT = 0.20  # collected at the order (IOSS) or at import
SPARE_RATE = 0.10  # the default of tools/bomagg.py

# Purchase keys of the generic lines, as the plateau sheet names them.
GATE_RESISTOR = "10k@R_0603_1608Metric"
DECOUPLING = "100n@C_0603_1608Metric"
PIN_HEADER = "PinHeader_1x10_P2.54mm"
PCB_LOT = "PCB_200x200_2L_x5"
RFID_READER = "MFRC522_QFN32"
RFID_CRYSTAL = "XTAL_27.12MHz"
RFID_MATCHING = "NFC_matching_set"
# The three analog references that make the bill of the LC front end
# (docs/bom-plateau.md), for the comparison.
LC_FRONT_END = ("ADG1607BCPZ", "AD8421ARZ", "OPA2810IDR")


def _bomagg():
    if str(TOOLS) not in sys.path:
        sys.path.insert(0, str(TOOLS))
    import bomagg

    return bomagg


def prices() -> dict:
    """The plateau sheet first, the Hall sheet on top of it."""
    bomagg = _bomagg()
    merged = bomagg.read_prices(PRICES_PLATEAU)
    merged.update(bomagg.read_prices(PRICES_HALL))
    return merged


@dataclass(frozen=True)
class CostLine:
    key: str
    label: str
    quantity: int
    buy: int  # quantity plus spares
    channel: str  # the cheaper channel, as bomagg picks it
    unit_usd: float | None
    status: str
    source: str

    @property
    def priced(self) -> bool:
        return self.unit_usd is not None

    @property
    def total_usd(self) -> float:
        return 0.0 if self.unit_usd is None else self.unit_usd * self.buy


@dataclass(frozen=True)
class Basket:
    name: str
    lines: tuple[CostLine, ...]
    exact_usd: float  # exact count, no spares
    buy_usd: float  # with the spare rule

    @property
    def all_priced(self) -> bool:
        return all(line.priced for line in self.lines)

    @property
    def eur_ht(self) -> float:
        return self.buy_usd * USD_TO_EUR

    @property
    def eur_ttc(self) -> float:
        return self.eur_ht * (1.0 + VAT)


def _basket(name: str, items: list[tuple[str, str, int, bool]], rate: float) -> Basket:
    bomagg = _bomagg()
    table = prices()
    lines = []
    exact = buy_total = 0.0
    for key, label, quantity, spare_ok in items:
        price = table.get(key, bomagg.Price())
        channel, unit = price.cheapest()
        buy = quantity + (bomagg.spares(quantity, rate) if spare_ok else 0)
        line = CostLine(key, label, quantity, buy, channel, unit, price.status, price.source)
        lines.append(line)
        if unit is not None:
            exact += unit * quantity
            buy_total += unit * buy
    return Basket(name, tuple(lines), exact, buy_total)


def quadrants(cfg: BoardConfig) -> int:
    return (cfg.plateau.grid // cfg.plateau.quadrant.squares) ** 2


def hall_basket(cfg: BoardConfig, rate: float = SPARE_RATE, sensor_index: int = 0) -> Basket:
    """The standalone prototype of the brief: four Hall sheets and a dev kit."""
    hr = cfg.hall_rfid
    sensor = hr.sensors[sensor_index]
    squares = cfg.plateau.grid**2
    n_q = quadrants(cfg)
    fets = hr.power_gating.groups * n_q
    items = [
        (sensor.mpn, f"capteur Hall {sensor.part}, {sensor.package}", squares, True),
        (hr.mux.mpn, f"multiplexeur {hr.mux.part}, {hr.mux.channels} vers 1", n_q, True),
        (hr.power_gating.fet, "P-FET de rangée", fets, True),
        (GATE_RESISTOR, "résistance de grille 10 kΩ, 0603", fets, True),
        (DECOUPLING, "découplage 100 nF, 0603, par capteur et par mux", squares + n_q, True),
        (PIN_HEADER, "embase 2,54 mm vers l'ESP32, une par nappe", n_q, True),
        (PCB_LOT, "cartes nues 200 x 200 mm, 2 couches, lot de 5 (minimum)", 1, False),
        (hr.esp32.devkit, "carte de développement ESP32-S3", 1, False),
    ]
    return _basket("hall", items, rate)


def hall_parts_basket(cfg: BoardConfig, rate: float = SPARE_RATE) -> Basket:
    """The components alone: what sits on the four sheets."""
    full = hall_basket(cfg, rate)
    lines = tuple(ln for ln in full.lines if ln.key not in (PCB_LOT, cfg.hall_rfid.esp32.devkit))
    exact = sum(0.0 if ln.unit_usd is None else ln.unit_usd * ln.quantity for ln in lines)
    buy = sum(ln.total_usd for ln in lines)
    return Basket("hall-parts", lines, exact, buy)


def rfid_basket(cfg: BoardConfig, rate: float = SPARE_RATE) -> Basket:
    """The identity layer as one reader per square, plus a tag per piece."""
    squares = cfg.plateau.grid**2
    pieces = 2 * 16 + 2 * cfg.pieces.spare_queens_per_side
    tag = cfg.hall_rfid.nfc.tag
    items = [
        (RFID_READER, "lecteur 13,56 MHz par case (MFRC522, QFN-32)", squares, True),
        (RFID_CRYSTAL, "quartz 27,12 MHz par lecteur", squares, True),
        (RFID_MATCHING, "filtre et adaptation d'antenne, une dizaine de passifs", squares, True),
        (
            tag.order_key,
            f"étiquette {tag.part} ø{tag.d_out_mm:.0f} mm, une par pièce",
            pieces,
            True,
        ),
    ]
    return _basket("rfid", items, rate)


def lc_front_end_usd(rate: float = SPARE_RATE) -> float:
    """What the three analog references of the four LC quadrants cost, spares
    included, from the generated BOMs and the plateau sheet: the number the
    Hall layer is compared to."""
    bomagg = _bomagg()
    plan = bomagg.parse_plan([f"{path}:{count}" for path, count in bomagg.PLATEAU])
    lines, _parts, _pads = bomagg.aggregate(plan)
    table = bomagg.read_prices(PRICES_PLATEAU)
    total = 0.0
    for line in lines:
        if line.key in LC_FRONT_END:
            _, unit = table.get(line.key, bomagg.Price()).cheapest()
            if unit is not None:
                total += unit * line.buy(rate)
    return total
