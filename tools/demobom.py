"""The purchase lists of the two technology demonstrators (notes 26 and 27),
with what each line costs on each channel and where to buy it.

    python3 tools/demobom.py                 # both lists, to docs/
    python3 tools/demobom.py --model a       # the LC demonstrator only

A demonstrator is a set of generated boards, each counted once, some
of whose parts stay unfitted (the LC demonstrator fits the analog board
of the mockup without its buck, its isolated UART and its LED buffer:
the option A of the pilot sheet). The generated `bom.csv` of every
board stays the source of references and quantities, as for
`tools/bomagg.py`, whose reading, aggregation and price file this tool
reuses; it adds the unfitted references, the links to both channels and
the Markdown sheets the tutorials embed.

Prices come from `docs/prix-demonstrateur.csv` (format of
`docs/prix-plateau.csv`: key, LCSC code and price, Mouser number and
price, status, source). Every price carries its date in its source;
they age, the quantities do not. Stdlib only, no KiCad, no network.
"""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from bomagg import (  # noqa: E402
    NOT_A_PART,
    Line,
    Price,
    family,
    read_prices,
    refs,
)

USD_TO_EUR = 0.92
VAT = 0.20
SPARE_RATE = 0.10
MOUSER_SEARCH = "https://www.mouser.fr/c/?q={q}"
MOUSER_PART = "https://www.mouser.fr/ProductDetail/{sku}"
LCSC_PART = "https://www.lcsc.com/product-detail/{code}.html"
LCSC_SEARCH = "https://www.lcsc.com/search?q={q}"


@dataclass
class Board:
    path: Path
    label: str
    unfitted: tuple[str, ...] = ()  # references left off the demonstrator


@dataclass
class Model:
    key: str
    title: str
    boards: list[Board]
    fixed: list[tuple[str, int]] = field(
        default_factory=list
    )  # price keys of boards, shipping, extras


MODELS = {
    "a": Model(
        "a",
        "Démonstrateur A, détection LC par oscillations",
        [
            Board(ROOT / "hardware/mockup-2x2/coil-board", "bobines"),
            Board(
                ROOT / "hardware/mockup-2x2/analog-board",
                "analogique",
                # option A of the pilot sheet: no buck (LDO only), no isolated UART, no LED buffer
                unfitted=(
                    "U1",
                    "L1",
                    "JP3",
                    "R1",
                    "R2",
                    "R3",
                    "R4",
                    "C4",
                    "C5",
                    "C6",
                    "C7",
                    "C8",
                    "FB1",
                    "U7",
                    "C26",
                    "J5",
                    "R66",
                    "R67",
                    "U8",
                    "R68",
                    "C27",
                ),
            ),
        ],
        fixed=[
            ("NUCLEO-G474RE", 1),
            ("PCB_100x100_4L_x5", 1),
            ("PCB_100x62_2L_x5", 1),
            ("Shipping_JLCPCB", 1),
            ("Shipping_Mouser", 1),
        ],
    ),
    "b": Model(
        "b",
        "Démonstrateur B, effet Hall et RFID",
        [
            Board(ROOT / "hardware/hallrfid-demo", "carte"),
            Board(ROOT / "hardware/tag-demo", "étiquettes"),
        ],
        fixed=[
            ("PCB_100x100_4L_x5", 1),
            ("PCB_100x87_2L_0.8_x5", 1),
            ("PCBA_economic_setup", 1),
            ("Shipping_JLCPCB", 1),
            ("Shipping_Mouser", 1),
            ("Magnets_ferrite_12_15_18x4", 1),
            ("NanoVNA-H", 1),
        ],
    ),
}

# footprint prefix -> key of the generic price line (parts bought by value)
GENERIC_KEYS = {
    "R_0603_1608Metric": "Resistor@R_0603_1608Metric",
    "R_0805_2012Metric": "Resistor@R_0805_2012Metric",
    "R_2512_6332Metric": "Resistor@R_2512_6332Metric",
    "C_0603_1608Metric": "Capacitor@C_0603_1608Metric",
    "C_0402_1005Metric": "Capacitor@C_0402_1005Metric",
    "C_1206_3216Metric": "Capacitor@C_1206_3216Metric",
    "CP_Elec": "Capacitor@CP_Elec",
    "PinHeader": "PinHeader@P2.54mm",
    "SolderJumper": "SolderJumper",
}


def read_board(board: Board) -> tuple[list[tuple[Line, int]], list[str]]:
    """The fitted, purchasable lines of one board and the references it leaves off."""
    bom = board.path / "bom.csv"
    if not bom.is_file():
        raise SystemExit(f"{bom}: no generated BOM, run the board generator first")
    lines: list[tuple[Line, int]] = []
    skipped: list[str] = []
    for row in csv.DictReader(bom.open(encoding="utf-8")):
        designators = refs(row.get("References", ""))
        footprint = (row.get("Footprint") or "").strip()
        if footprint.startswith(NOT_A_PART):
            continue
        if (row.get("DNP") or "").strip():
            skipped += designators
            continue
        kept = [d for d in designators if d not in board.unfitted]
        skipped += [d for d in designators if d in board.unfitted]
        if not kept:
            continue
        value = (row.get("Value") or "").strip()
        mpn = (row.get("MPN") or "").strip()
        lines.append(
            (
                Line(
                    key=mpn or f"{value}@{footprint}",
                    family=family(kept[0]),
                    value=value,
                    footprint=footprint,
                    mpn=mpn,
                    lcsc=(row.get("LCSC") or "").strip(),
                ),
                len(kept),
            )
        )
    return lines, skipped


def aggregate(model: Model) -> tuple[list[Line], dict[str, list[str]]]:
    merged: dict[str, Line] = {}
    skipped: dict[str, list[str]] = {}
    for board in model.boards:
        lines, left = read_board(board)
        skipped[board.label] = left
        for line, qty in lines:
            kept = merged.setdefault(line.key, line)
            kept.per_board[board.label] = kept.per_board.get(board.label, 0) + qty
            if not kept.lcsc and line.lcsc:
                kept.lcsc = line.lcsc
    order = {
        "U": 0,
        "Q": 1,
        "D": 2,
        "Y": 3,
        "L": 4,
        "J": 5,
        "SW": 6,
        "JP": 7,
        "FB": 8,
        "R": 9,
        "C": 10,
    }
    ranked = sorted(merged.values(), key=lambda ln: (order.get(ln.family, 99), -ln.total, ln.key))
    return ranked, skipped


def price_of(line: Line, prices: dict[str, Price]) -> Price:
    if line.key in prices:
        return prices[line.key]
    for prefix, generic in GENERIC_KEYS.items():
        if line.footprint.startswith(prefix) and generic in prices:
            return prices[generic]
    return Price()


def links(line: Line, price: Price) -> tuple[str, str]:
    code = price.lcsc or line.lcsc
    lcsc = (
        LCSC_PART.format(code=code)
        if code
        else (LCSC_SEARCH.format(q=line.mpn) if line.mpn else "")
    )
    if price.mouser:
        mouser = MOUSER_PART.format(sku=quote(price.mouser, safe=""))
    elif line.mpn:
        mouser = MOUSER_SEARCH.format(q=quote(line.mpn, safe=""))
    else:
        size = line.footprint.split("_")[1] if "_" in line.footprint else ""
        mouser = MOUSER_SEARCH.format(q=quote(f"{line.value} {size}".strip(), safe=""))
    if lcsc.startswith(LCSC_SEARCH[: LCSC_SEARCH.index("{")]):
        lcsc = LCSC_SEARCH.format(q=quote(line.mpn, safe=""))
    return lcsc, mouser


def buy_qty(line: Line) -> int:
    return line.buy(SPARE_RATE)


def totals(lines: list[Line], prices: dict[str, Price]) -> dict[str, float]:
    out = {"lcsc": 0.0, "mouser": 0.0, "cheapest": 0.0, "unpriced": 0}
    for line in lines:
        p = price_of(line, prices)
        q = buy_qty(line)
        if p.lcsc_usd is not None:
            out["lcsc"] += p.lcsc_usd * q
        if p.mouser_usd is not None:
            out["mouser"] += p.mouser_usd * q
        channel, unit = p.cheapest()
        if unit is None:
            out["unpriced"] += 1
        else:
            out["cheapest"] += unit * q
    return out


def fixed_total(
    model: Model, prices: dict[str, Price]
) -> tuple[list[tuple[str, float, str]], float]:
    rows, total = [], 0.0
    for key, qty in model.fixed:
        p = prices.get(key)
        if p is None:
            rows.append((key, 0.0, "prix manquant"))
            continue
        unit = p.lcsc_usd if p.lcsc_usd is not None else p.mouser_usd
        unit = unit or 0.0
        rows.append((key, unit * qty, p.source))
        total += unit * qty
    return rows, total


def usd_to_eur_ttc(usd: float) -> float:
    return usd * USD_TO_EUR * (1.0 + VAT)


def markdown(
    model: Model,
    lines: list[Line],
    skipped: dict[str, list[str]],
    prices: dict[str, Price],
    date: str,
) -> str:
    boards = [b.label for b in model.boards]
    out = [
        f"# Nomenclature du {model.title[0].lower() + model.title[1:]}",
        "",
        f"Générée par `python3 tools/demobom.py --model {model.key}` le {date} depuis les",
        "`bom.csv` des cartes et `docs/prix-demonstrateur.csv`. Les quantités",
        "sont celles des cartes ; la colonne « achat » ajoute la rechange de",
        f"{int(SPARE_RATE * 100)} % par ligne (au moins une pièce, deux au-delà de dix). Les prix",
        "sont en USD à l'unité ou à la petite série, datés dans la fiche de",
        "prix, « vérifié » ou « estimé » ; chaque lien ouvre la page ou la",
        "recherche du distributeur, à relire le jour de la commande. Conversion",
        f"1 USD = {USD_TO_EUR} EUR, TVA {int(VAT * 100)} % ajoutée dans les totaux.",
        "",
        "## Composants",
        "",
    ]
    head = [
        "Repères",
        "Valeur",
        "Empreinte",
        "MPN",
        *boards,
        "Achat",
        "LCSC (USD)",
        "Mouser (USD)",
        "Moins cher",
    ]
    out.append("| " + " | ".join(head) + " |")
    out.append("|" + "---|" * len(head))
    for line in lines:
        p = price_of(line, prices)
        lcsc_link, mouser_link = links(line, p)
        code = p.lcsc or line.lcsc
        lcsc_cell = (
            f"[{code}]({lcsc_link})" if code else (f"[chercher]({lcsc_link})" if lcsc_link else "")
        )
        if p.lcsc_usd is not None:
            lcsc_cell += f" {p.lcsc_usd:.3f}"
        mouser_cell = f"[{p.mouser or 'chercher'}]({mouser_link})"
        if p.mouser_usd is not None:
            mouser_cell += f" {p.mouser_usd:.2f}"
        channel, unit = p.cheapest()
        q = buy_qty(line)
        cheapest = f"{unit * q:.2f} ({channel})" if unit is not None else "à relever"
        fam = line.family
        out.append(
            "| "
            + " | ".join(
                [
                    fam,
                    line.value,
                    line.footprint,
                    line.mpn or "",
                    *[str(line.per_board.get(b, 0)) for b in boards],
                    str(q),
                    lcsc_cell,
                    mouser_cell,
                    cheapest,
                ]
            )
            + " |"
        )
    t = totals(lines, prices)
    out += [
        "",
        "## Totaux",
        "",
        "| Poste | USD | EUR TTC |",
        "|---|---|---|",
    ]
    for label, key in (
        ("Composants, tout chez LCSC (lignes qui y existent)", "lcsc"),
        ("Composants, tout chez Mouser (lignes qui y existent)", "mouser"),
        ("Composants, le moins cher ligne à ligne", "cheapest"),
    ):
        out.append(f"| {label} | {t[key]:.0f} | {usd_to_eur_ttc(t[key]):.0f} |")
    rows, fixed = fixed_total(model, prices)
    for key, usd, _src in rows:
        out.append(f"| {key} | {usd:.0f} | {usd_to_eur_ttc(usd):.0f} |")
    grand = t["cheapest"] + fixed
    out.append(
        "| **Total, le moins cher ligne à ligne, cartes et port compris** "
        f"| **{grand:.0f}** | **{usd_to_eur_ttc(grand):.0f}** |"
    )
    if t["unpriced"]:
        out.append("")
        out.append(f"{t['unpriced']} ligne(s) sans prix : à relever au panier.")
    left = {k: v for k, v in skipped.items() if v}
    if left:
        out += ["", "## Non monté sur le démonstrateur", ""]
        for board, items in left.items():
            out.append(f"- carte {board} : {', '.join(sorted(items))}")
    return "\n".join(out) + "\n"


def carts(out_dir: Path, model: Model, lines: list[Line], prices: dict[str, Price]) -> None:
    """One cart per channel in the site's import format: a line goes where
    it is cheaper, a line one channel does not sell goes to the other."""
    lcsc_path = out_dir / f"panier-demonstrateur-{model.key}-lcsc.csv"
    mouser_path = out_dir / f"panier-demonstrateur-{model.key}-mouser.csv"
    with (
        lcsc_path.open("w", encoding="utf-8", newline="") as fl,
        mouser_path.open("w", encoding="utf-8", newline="") as fm,
    ):
        wl, wm = csv.writer(fl), csv.writer(fm)
        wl.writerow(["LCSC Part Number", "Manufacture Part Number", "Quantity", "Description"])
        wm.writerow(["Mouser Part Number", "Manufacturer Part No", "Quantity", "Description"])
        for line in lines:
            p = price_of(line, prices)
            channel, _unit = p.cheapest()
            desc = f"{line.value} {line.footprint}".strip()
            if channel == "lcsc" and (p.lcsc or line.lcsc):
                wl.writerow([p.lcsc or line.lcsc, line.mpn, buy_qty(line), desc])
            else:
                wm.writerow([p.mouser, line.mpn, buy_qty(line), desc])


def write_csv(path: Path, model: Model, lines: list[Line], prices: dict[str, Price]) -> None:
    boards = [b.label for b in model.boards]
    with path.open("w", encoding="utf-8", newline="") as handle:
        w = csv.writer(handle)
        w.writerow(
            [
                "Family",
                "Value",
                "Footprint",
                "MPN",
                "LCSC",
                *boards,
                "Total",
                "Buy",
                "LCSC_USD",
                "Mouser",
                "Mouser_USD",
                "Cheapest",
                "Line_USD",
                "Status",
                "LCSC_link",
                "Mouser_link",
            ]
        )
        for line in lines:
            p = price_of(line, prices)
            channel, unit = p.cheapest()
            q = buy_qty(line)
            lcsc_link, mouser_link = links(line, p)
            w.writerow(
                [
                    line.family,
                    line.value,
                    line.footprint,
                    line.mpn,
                    p.lcsc or line.lcsc,
                    *[line.per_board.get(b, 0) for b in boards],
                    line.total,
                    q,
                    "" if p.lcsc_usd is None else f"{p.lcsc_usd:.4f}",
                    p.mouser,
                    "" if p.mouser_usd is None else f"{p.mouser_usd:.4f}",
                    channel,
                    "" if unit is None else f"{unit * q:.4f}",
                    p.status,
                    lcsc_link,
                    mouser_link,
                ]
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="demobom")
    parser.add_argument("--model", choices=sorted(MODELS), action="append")
    parser.add_argument("--prices", type=Path, default=ROOT / "docs/prix-demonstrateur.csv")
    parser.add_argument("--out", type=Path, default=ROOT / "docs")
    parser.add_argument("--date", default=None, help="date printed in the sheets (default: today)")
    args = parser.parse_args(argv)
    import datetime as dt

    date = args.date or dt.date.today().strftime("%d/%m/%Y")
    prices = read_prices(args.prices)
    for key in args.model or sorted(MODELS):
        model = MODELS[key]
        lines, skipped = aggregate(model)
        md = markdown(model, lines, skipped, prices, date)
        (args.out / f"bom-demonstrateur-{key}.md").write_text(md, encoding="utf-8")
        write_csv(args.out / f"bom-demonstrateur-{key}.csv", model, lines, prices)
        carts(args.out, model, lines, prices)
        t = totals(lines, prices)
        print(
            f"model {key}: {len(lines)} lines, {sum(ln.total for ln in lines)} parts, "
            f"cheapest {t['cheapest']:.0f} USD, {t['unpriced']} unpriced"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
