"""One purchase list for a set of boards, and what it costs per channel.

Ordering the plateau is not ordering one board: the quadrant is built
four times, the brain once, and the same 100 nF appears on both. Adding
those quantities by hand is how a line gets forgotten or counted twice,
so this tool does it from the generated `bom.csv` of each board, which
stays the source of truth for references and quantities.

    python3 tools/bomagg.py                          # 4 quadrants + 1 brain
    python3 tools/bomagg.py --board hardware/brain:1 # any other set
    python3 tools/bomagg.py --prices docs/prix-plateau.csv \
        --csv docs/bom-plateau.csv --carts docs/    # list, prices and carts

With a price file it also totals the basket on each channel and picks
the cheaper one line by line, which is the only honest way to compare
LCSC against Mouser: the winner changes with the line, not with the
distributor. Prices are market data, they age, and each one carries its
status and its source in that file; quantities do not age, they come
from the boards.

Stdlib only, no KiCad and no network, like `tools/fabcheck.py`.
"""

from __future__ import annotations

import argparse
import csv
import math
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# The plateau of ADR 0010: four identical quadrants and one brain.
PLATEAU = (("hardware/quadrant", 4), ("hardware/brain", 1))

# Footprints that are copper, not components: nothing to buy, nothing to
# place. Same list as tools/fabcheck.py, same reason.
NOT_A_PART = ("TestPoint", "MountingHole", "NetTie", "COIL_TIE", "Fiducial")

# Designator prefix to purchasing family, longest prefix first.
FAMILIES = (
    ("BZ", "buzzer"),
    ("FB", "ferrite"),
    ("JP", "jumper"),
    ("LD", "led"),
    ("SW", "switch"),
    ("C", "capacitor"),
    ("D", "diode"),
    ("F", "fuse"),
    ("J", "connector"),
    ("L", "inductor"),
    ("Q", "transistor"),
    ("R", "resistor"),
    ("U", "ic"),
)

# Order of the families in the report: what drives the bill first.
FAMILY_ORDER = (
    "ic",
    "connector",
    "led",
    "transistor",
    "diode",
    "inductor",
    "ferrite",
    "buzzer",
    "switch",
    "fuse",
    "jumper",
    "capacitor",
    "resistor",
    "other",
)


def refs(cell: str) -> list[str]:
    """The designators of one BOM cell, commas or spaces."""
    return [r for r in re.split(r"[,\s]+", cell or "") if r]


def family(designator: str) -> str:
    head = re.match(r"[A-Za-z]+", designator)
    if head:
        letters = head.group(0).upper()
        for prefix, name in FAMILIES:
            if letters.startswith(prefix):
                return name
    return "other"


def spares(quantity: int, rate: float) -> int:
    """How many to add to a line, so one dead part does not stop a build.

    Ten percent, never less than one, and at least two on the lines
    bought by the dozen: those are the 0603 that vanish under the bench.
    """
    if rate <= 0:
        return 0
    extra = max(1, math.ceil(quantity * rate))
    return max(extra, 2) if quantity >= 10 else extra


@dataclass
class Line:
    key: str
    family: str
    value: str
    footprint: str
    mpn: str
    lcsc: str
    per_board: dict[str, int] = field(default_factory=dict)

    @property
    def total(self) -> int:
        return sum(self.per_board.values())

    def buy(self, rate: float) -> int:
        return self.total + spares(self.total, rate)


@dataclass
class Price:
    lcsc: str = ""
    lcsc_usd: float | None = None
    mouser: str = ""
    mouser_usd: float | None = None
    status: str = ""
    source: str = ""

    def cheapest(self) -> tuple[str, float | None]:
        if self.lcsc_usd is not None and self.mouser_usd is not None:
            return ("lcsc", self.lcsc_usd) if self.lcsc_usd <= self.mouser_usd else (
                "mouser",
                self.mouser_usd,
            )
        if self.lcsc_usd is not None:
            return "lcsc", self.lcsc_usd
        if self.mouser_usd is not None:
            return "mouser", self.mouser_usd
        return "", None


def read_bom(directory: Path) -> tuple[list[tuple[Line, int]], int]:
    """The purchasable lines of one board, plus its count of bare pads."""
    bom = directory / "bom.csv"
    if not bom.is_file():
        raise SystemExit(f"{bom}: no generated BOM, run the board generator first")
    lines: list[tuple[Line, int]] = []
    pads = 0
    for row in csv.DictReader(bom.open(encoding="utf-8")):
        designators = refs(row.get("References", ""))
        quantity = int(row.get("Qty") or len(designators) or 0)
        footprint = (row.get("Footprint") or "").strip()
        if footprint.startswith(NOT_A_PART):
            pads += quantity
            continue
        if (row.get("DNP") or "").strip().lower() in ("1", "yes", "true", "x", "oui"):
            continue
        value = (row.get("Value") or "").strip()
        mpn = (row.get("MPN") or "").strip()
        lines.append(
            (
                Line(
                    key=mpn or f"{value}@{footprint}",
                    family=family(designators[0] if designators else ""),
                    value=value,
                    footprint=footprint,
                    mpn=mpn,
                    lcsc=(row.get("LCSC") or "").strip(),
                ),
                quantity,
            )
        )
    return lines, pads


def aggregate(plan: list[tuple[Path, int]]) -> tuple[list[Line], dict[str, int], dict[str, int]]:
    """Merge the BOMs of the plan, each board counted as many times as asked."""
    merged: dict[str, Line] = {}
    parts: dict[str, int] = {}
    pads: dict[str, int] = {}
    for directory, multiplier in plan:
        board = directory.name
        lines, bare = read_bom(directory)
        parts[board] = sum(q for _, q in lines) * multiplier
        pads[board] = bare * multiplier
        for line, quantity in lines:
            held = merged.setdefault(line.key, line)
            held.per_board[board] = held.per_board.get(board, 0) + quantity * multiplier
            # A code found on one board serves the same part on another.
            held.lcsc = held.lcsc or line.lcsc
            held.mpn = held.mpn or line.mpn
    order = {name: rank for rank, name in enumerate(FAMILY_ORDER)}
    ranked = sorted(merged.values(), key=lambda ln: (order.get(ln.family, 99), -ln.total, ln.key))
    return ranked, parts, pads


def read_prices(path: Path) -> dict[str, Price]:
    prices: dict[str, Price] = {}

    def number(cell: str) -> float | None:
        cell = (cell or "").strip().replace(",", ".")
        return float(cell) if cell else None

    for row in csv.DictReader(path.open(encoding="utf-8")):
        key = (row.get("Key") or "").strip()
        if not key:
            continue
        prices[key] = Price(
            lcsc=(row.get("LCSC") or "").strip(),
            lcsc_usd=number(row.get("LCSC_USD", "")),
            mouser=(row.get("Mouser") or "").strip(),
            mouser_usd=number(row.get("Mouser_USD", "")),
            status=(row.get("Status") or "").strip(),
            source=(row.get("Source") or "").strip(),
        )
    return prices


def lcsc_code(line: Line, prices: dict[str, Price]) -> str:
    """The code to order with: the price file decides for the keys it holds."""
    if line.key in prices:
        return prices[line.key].lcsc
    return line.lcsc


def write_csv(
    path: Path,
    lines: list[Line],
    boards: list[str],
    prices: dict[str, Price],
    rate: float,
) -> None:
    header = ["Family", "Value", "Footprint", "MPN", "LCSC", *boards, "Total", "Buy"]
    if prices:
        header += ["LCSC_USD", "Mouser_USD", "Cheapest", "Line_USD", "Status"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        for line in lines:
            price = prices.get(line.key, Price())
            buy = line.buy(rate)
            row = [
                line.family,
                line.value,
                line.footprint,
                line.mpn,
                lcsc_code(line, prices),
                *[line.per_board.get(board, 0) for board in boards],
                line.total,
                buy,
            ]
            if prices:
                channel, unit = price.cheapest()
                row += [
                    "" if price.lcsc_usd is None else f"{price.lcsc_usd:.4f}",
                    "" if price.mouser_usd is None else f"{price.mouser_usd:.4f}",
                    channel,
                    "" if unit is None else f"{unit * buy:.4f}",
                    price.status,
                ]
            writer.writerow(row)


def markdown(lines: list[Line], boards: list[str], prices: dict[str, Price], rate: float) -> str:
    head = ["Poste", "Empreinte", "MPN", "LCSC", *boards, "Total", "Achat"]
    if prices:
        head += ["LCSC USD", "Mouser USD", "Ligne USD"]
    out = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for line in lines:
        price = prices.get(line.key, Price())
        buy = line.buy(rate)
        channel, unit = price.cheapest()
        cells = [
            line.value,
            line.footprint,
            line.mpn or "",
            lcsc_code(line, prices),
            *[str(line.per_board.get(board, 0)) for board in boards],
            str(line.total),
            str(buy),
        ]
        if prices:
            cells += [
                "" if price.lcsc_usd is None else f"{price.lcsc_usd:.4f}",
                "" if price.mouser_usd is None else f"{price.mouser_usd:.4f}",
                "" if unit is None else f"{unit * buy:.2f} ({channel})",
            ]
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out)


def carts(
    directory: Path,
    lines: list[Line],
    prices: dict[str, Price],
    rate: float,
) -> dict[str, int]:
    """Split the list in one cart per channel, each in that site's import format.

    A line goes where it is cheaper, and a line one channel does not sell
    goes to the other without discussion. Generic passives carry no code:
    they are picked in the catalogue or left to the assembler's library,
    and the description is what the search box needs.
    """
    directory.mkdir(parents=True, exist_ok=True)
    counted = {"lcsc": 0, "mouser": 0}
    files = {
        "lcsc": (directory / "panier-lcsc.csv", ["LCSC Part Number", "Manufacture Part Number"]),
        "mouser": (directory / "panier-mouser.csv", ["Mouser Part Number", "Manufacturer Part No"]),
    }
    handles = {}
    for channel, (path, head) in files.items():
        handle = path.open("w", encoding="utf-8", newline="")
        writer = csv.writer(handle)
        writer.writerow([*head, "Quantity", "Description"])
        handles[channel] = (handle, writer)
    for line in lines:
        price = prices.get(line.key, Price())
        channel, _unit = price.cheapest()
        if not channel:
            continue
        code = lcsc_code(line, prices) if channel == "lcsc" else price.mouser
        _handle, writer = handles[channel]
        writer.writerow(
            [code, line.mpn, line.buy(rate), f"{line.value} {line.footprint}".strip()]
        )
        counted[channel] += 1
    for handle, _writer in handles.values():
        handle.close()
    return counted


def totals(
    lines: list[Line], prices: dict[str, Price], rate: float
) -> dict[str, tuple[float, int]]:
    """What the same basket costs on each channel, and how many lines it covers.

    A channel that does not sell a part simply does not total it, so a
    cheap channel can be cheap because it is incomplete: the count is
    there to say so, and the mixed basket is the only one always whole.
    """
    sums = {"lcsc": [0.0, 0], "mouser": [0.0, 0], "mixed": [0.0, 0]}
    for line in lines:
        price = prices.get(line.key, Price())
        buy = line.buy(rate)
        if price.lcsc_usd is not None:
            sums["lcsc"][0] += price.lcsc_usd * buy
            sums["lcsc"][1] += 1
        if price.mouser_usd is not None:
            sums["mouser"][0] += price.mouser_usd * buy
            sums["mouser"][1] += 1
        _, unit = price.cheapest()
        if unit is not None:
            sums["mixed"][0] += unit * buy
            sums["mixed"][1] += 1
    return {name: (total, count) for name, (total, count) in sums.items()}


def board_cost(
    lines: list[Line], prices: dict[str, Price], board: str, multiplier: int
) -> tuple[float, int]:
    """Parts cost of ONE board of that name, and how many of its lines are priced."""
    total, priced = 0.0, 0
    for line in lines:
        quantity = line.per_board.get(board, 0)
        if not quantity:
            continue
        _, unit = prices.get(line.key, Price()).cheapest()
        if unit is None:
            continue
        total += unit * quantity / multiplier
        priced += 1
    return total, priced


def drivers(lines: list[Line], prices: dict[str, Price], rate: float, count: int) -> list[
    tuple[Line, float]
]:
    """The lines that make the bill, cheapest channel each, biggest first."""
    weighted = []
    for line in lines:
        _, unit = prices.get(line.key, Price()).cheapest()
        if unit is not None:
            weighted.append((line, unit * line.buy(rate)))
    weighted.sort(key=lambda pair: -pair[1])
    return weighted[:count]


def parse_plan(items: list[str]) -> list[tuple[Path, int]]:
    plan: list[tuple[Path, int]] = []
    for item in items:
        path, _, count = item.partition(":")
        directory = Path(path)
        if not directory.is_absolute():
            directory = ROOT / directory
        plan.append((directory, int(count or 1)))
    return plan


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--board",
        action="append",
        default=[],
        metavar="DIR[:N]",
        help="board directory and how many of it, repeatable (default: the plateau)",
    )
    parser.add_argument("--prices", type=Path, help="price file, joined on MPN or Value@Footprint")
    parser.add_argument("--csv", type=Path, help="write the merged list there")
    parser.add_argument("--markdown", action="store_true", help="print the list as a table")
    parser.add_argument(
        "--carts",
        type=Path,
        metavar="DIR",
        help="write one import file per channel there, needs --prices",
    )
    parser.add_argument(
        "--spares",
        type=float,
        default=0.10,
        metavar="RATE",
        help="spare rate on every line, 0 to buy the exact count (default 0.10)",
    )
    args = parser.parse_args(argv)

    plan = parse_plan(args.board or [f"{path}:{count}" for path, count in PLATEAU])
    lines, parts, pads = aggregate(plan)
    boards = [directory.name for directory, _ in plan]
    prices = read_prices(args.prices) if args.prices else {}

    for directory, multiplier in plan:
        board = directory.name
        print(
            f"{board:14s} x{multiplier}  {parts[board]:5d} components  "
            f"{pads[board]:3d} pads (test points, ties, holes)"
        )
    buys = sum(line.buy(args.spares) for line in lines)
    print(
        f"{'total':14s}     {sum(parts.values()):5d} components in "
        f"{len(lines):3d} purchase lines, {buys} units to buy with spares"
    )

    if prices:
        clashes = [
            (line, prices[line.key].lcsc)
            for line in lines
            if line.key in prices
            and prices[line.key].lcsc
            and line.lcsc
            and prices[line.key].lcsc != line.lcsc
        ]
        if clashes:
            print(
                f"{'lcsc clash':14s}     {len(clashes)} codes differ from the circuit "
                "description, the price file wins: "
                + ", ".join(f"{line.mpn} {line.lcsc} -> {code}" for line, code in clashes[:4])
            )
        missing = [line for line in lines if prices.get(line.key, Price()).cheapest()[1] is None]
        sums = totals(lines, prices, args.spares)
        for name in ("lcsc", "mouser", "mixed"):
            total, count = sums[name]
            print(
                f"{'basket ' + name:14s}     {total:8.2f} USD over {count:3d} of "
                f"{len(lines)} lines"
            )
        if missing:
            print(f"{'no price':14s}     {len(missing)} lines: " + ", ".join(
                f"{line.value} {line.footprint}" for line in missing[:6]
            ))
        for directory, multiplier in plan:
            unit_cost, priced = board_cost(lines, prices, directory.name, multiplier)
            print(
                f"{'one ' + directory.name:14s}     {unit_cost:8.2f} USD of parts, "
                f"{priced:3d} lines, exact count without spares"
            )
        for line, cost in drivers(lines, prices, args.spares, 6):
            share = 100 * cost / sums["mixed"][0] if sums["mixed"][0] else 0
            print(
                f"{'driver':14s}     {cost:8.2f} USD  {share:4.1f} %  "
                f"{line.buy(args.spares):4d} x {line.mpn or line.value} {line.footprint}"
            )
    if args.csv:
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        write_csv(args.csv, lines, boards, prices, args.spares)
        shown = args.csv.relative_to(ROOT) if args.csv.is_absolute() else args.csv
        print(f"{'written':14s}     {shown}")
    if args.carts:
        if not prices:
            parser.error("--carts needs --prices: the price file decides where a line goes")
        counted = carts(args.carts, lines, prices, args.spares)
        print(
            f"{'carts':14s}     lcsc {counted['lcsc']:3d} lines, mouser {counted['mouser']:3d} "
            f"lines, in {args.carts}"
        )
    if args.markdown:
        print()
        print(markdown(lines, boards, prices, args.spares))
    return 0


if __name__ == "__main__":
    sys.exit(main())
