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
            ("PCBA_standard_2_boards", 1),
            ("Shipping_JLCPCB", 1),
            ("Shipping_Mouser", 1),
            ("Magnets_ferrite_12_15_18x4", 1),
            ("NanoVNA-H", 1),
        ],
    ),
}

# The cost sheet (docs/couts-demonstrateurs.md): every expense of a
# demonstrator beyond the component lines, by category. (category, price
# key, quantity, optional): an optional line is not counted in the
# minimum total. The components' total comes from the BOM lines.
Cost = tuple[str, str, int, bool]
CATEGORIES = (
    "Cartes nues (JLCPCB)",
    "Assemblage (JLCPCB)",
    "Cartes de développement",
    "Composants hors cartes et matériaux",
    "Outillage et instruments",
    "Port et douane",
)
COSTS: dict[str, list[Cost]] = {
    "a": [
        ("Cartes nues (JLCPCB)", "PCB_100x100_4L_x5", 1, False),
        ("Cartes nues (JLCPCB)", "PCB_inner_copper_1oz", 1, True),
        ("Cartes nues (JLCPCB)", "PCB_100x62_2L_x5", 1, False),
        ("Cartes nues (JLCPCB)", "PCB_stencil_100x100", 1, True),
        ("Assemblage (JLCPCB)", "PCBA_economic_setup", 1, True),
        ("Assemblage (JLCPCB)", "JLC3DP_pucks_and_jigs", 1, True),
        ("Cartes de développement", "NUCLEO-G474RE", 1, False),
        ("Composants hors cartes et matériaux", "Magnets_ferrite_12_15_18x4", 1, False),
        ("Composants hors cartes et matériaux", "Enamelled_wire_025_0315", 1, False),
        ("Composants hors cartes et matériaux", "Puck_C0G_capacitors", 1, False),
        ("Composants hors cartes et matériaux", "Plywood_3mm_felt", 1, False),
        ("Composants hors cartes et matériaux", "Nylon_M3_kit", 1, False),
        ("Composants hors cartes et matériaux", "Supply_12V_2A_jack", 1, False),
        ("Composants hors cartes et matériaux", "Dupont_and_USB_cables", 1, False),
        ("Outillage et instruments", "Tool_soldering_iron_kit", 1, False),
        ("Outillage et instruments", "Tool_multimeter", 1, False),
        ("Outillage et instruments", "Tool_bench_supply", 1, False),
        ("Outillage et instruments", "Tool_pocket_oscilloscope", 1, False),
        ("Outillage et instruments", "Tool_LCR_meter", 1, True),
        ("Port et douane", "Shipping_JLCPCB", 1, False),
        ("Port et douane", "Shipping_Mouser", 1, False),
        ("Port et douane", "Customs_import_FR", 1, False),
    ],
    "b": [
        ("Cartes nues (JLCPCB)", "PCB_100x100_4L_x5", 1, False),
        ("Cartes nues (JLCPCB)", "PCB_100x87_2L_0.8_x5", 1, False),
        ("Cartes nues (JLCPCB)", "PCB_stencil_100x100", 1, True),
        ("Assemblage (JLCPCB)", "PCBA_standard_2_boards", 1, False),
        ("Assemblage (JLCPCB)", "JLC3DP_pieces_and_plate", 1, True),
        ("Cartes de développement", "ESP32-S3-DevKitC-1", 1, True),
        ("Composants hors cartes et matériaux", "Magnets_ferrite_12_15_18x4", 1, False),
        ("Composants hors cartes et matériaux", "NTAG213_cards", 1, False),
        ("Composants hors cartes et matériaux", "Polyimide_tape", 1, False),
        ("Composants hors cartes et matériaux", "Nylon_M3_kit", 1, False),
        ("Composants hors cartes et matériaux", "UFL_SMA_pigtails", 1, False),
        ("Composants hors cartes et matériaux", "Dupont_and_USB_cables", 1, False),
        ("Composants hors cartes et matériaux", "Aluminium_steel_plates", 1, True),
        ("Outillage et instruments", "Tool_soldering_iron_kit", 1, False),
        ("Outillage et instruments", "Tool_multimeter", 1, False),
        ("Outillage et instruments", "Tool_bench_supply", 1, False),
        ("Outillage et instruments", "NanoVNA-H", 1, False),
        ("Outillage et instruments", "Tool_NFC_phone", 1, False),
        ("Outillage et instruments", "Tool_pocket_oscilloscope", 1, True),
        ("Outillage et instruments", "Tool_hot_air_station", 1, True),
        ("Port et douane", "Shipping_JLCPCB", 1, False),
        ("Port et douane", "Shipping_Mouser", 1, False),
        ("Port et douane", "Customs_import_FR", 1, False),
    ],
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


def unit_price(p: Price) -> float:
    """The price kept for a cost line: the cheaper channel, else the only one."""
    _channel, unit = p.cheapest()
    return unit or 0.0


HOME_EXCLUDED = ("Assemblage (JLCPCB)", "Outillage et instruments")
HOME_KEPT = {
    "PCB_stencil_100x100": "conseillé pour poser la pâte sous les QFN et le module",
    "JLC3DP_pucks_and_jigs": "ou imprimés chez soi",
    "JLC3DP_pieces_and_plate": "ou imprimés chez soi",
}
HOME_SHARED = (
    "Nylon_M3_kit",
    "Dupont_and_USB_cables",
    "Magnets_ferrite_12_15_18x4",
    "Shipping_Mouser",
)


def scenario_home(prices: dict[str, Price], components: dict[str, dict[str, float]]) -> list[str]:
    """The sheet's second scenario: every board soldered at home, the
    bench already equipped. Assembly and tools drop out, the stencil
    stays as the useful option, consumables are assumed in stock."""
    out = [
        "## Scénario : soudure maison, gros matériel déjà acheté",
        "",
        "Les cartes se commandent nues et se soudent au fer ; le HVQFN du",
        "MFRC522 et le module ESP32 passent à l'air chaud ou à la plaque, avec",
        "le pochoir. Fer, air chaud, alimentation de laboratoire, multimètre,",
        "oscilloscope et NanoVNA sont déjà sur l'établi, pâte, flux et tresse",
        "aussi. Restent les composants, les cartes nues, les cartes de",
        "développement (la NUCLEO reste comptée : elle porte le démonstrateur A ;",
        "à retirer si elle est déjà dans le tiroir), les matériaux et le port.",
        "Les codes LCSC manquants des condensateurs",
        "d'adaptation n'ont plus d'importance : on les achète par valeur, chez",
        "Mouser ou LCSC, dans la même commande.",
        "",
    ]
    totals: dict[str, dict[str, float]] = {}
    for key, title in (("a", MODELS["a"].title), ("b", MODELS["b"].title)):
        comp = components[key]
        minimum = complete = comp["cheapest"]
        out += [
            f"### {title}",
            "",
            "| Poste | USD | EUR TTC | Statut | Remarque |",
            "|---|---|---|---|---|",
            f"| Composants des cartes ({comp['parts']:.0f} pièces, rechange comprise) | "
            f"{comp['cheapest']:.0f} | {usd_to_eur_ttc(comp['cheapest']):.0f} | relevés web | "
            "le moins cher de LCSC ou Mouser ligne à ligne |",
        ]
        for cat, pkey, qty, optional in COSTS[key]:
            if cat in HOME_EXCLUDED and pkey not in HOME_KEPT:
                continue
            p = prices.get(pkey)
            if p is None:
                continue
            usd = unit_price(p) * qty
            status = ("optionnel, " if optional else "") + (
                "vérifié" if p.status == "verified" else "estimé"
            )
            note = HOME_KEPT.get(pkey, cat.lower())
            eur = usd_to_eur_ttc(usd)
            out.append(f"| {pkey.replace('_', ' ')} | {usd:.0f} | {eur:.0f} | {status} | {note} |")
            complete += usd
            if not optional:
                minimum += usd
        out += [
            f"| **Minimum** | **{minimum:.0f}** | **{usd_to_eur_ttc(minimum):.0f}** | | |",
            f"| **Avec les options** (pochoir, impression 3D, carte de secours) "
            f"| **{complete:.0f}** | **{usd_to_eur_ttc(complete):.0f}** | | |",
            "",
        ]
        totals[key] = {"minimum": minimum, "complete": complete}
    once = sum(
        unit_price(prices[k]) * q
        for _c, k, q, _o in COSTS["b"]
        if k in HOME_SHARED and prices.get(k)
    )
    pair_min = totals["a"]["minimum"] + totals["b"]["minimum"] - once
    pair_full = totals["a"]["complete"] + totals["b"]["complete"] - once
    out += [
        "| Les deux démonstrateurs, soudure maison | USD | EUR TTC |",
        "|---|---|---|",
        f"| Minimum (visserie, nappes, aimants et port Mouser comptés une fois) | {pair_min:.0f} "
        f"| {usd_to_eur_ttc(pair_min):.0f} |",
        f"| Avec les options | {pair_full:.0f} | {usd_to_eur_ttc(pair_full):.0f} |",
        "",
    ]
    return out


def cost_sheet(prices: dict[str, Price], components: dict[str, dict[str, float]], date: str) -> str:
    """docs/couts-demonstrateurs.md: every expense of each demonstrator by
    category, components included, with a minimum total (the lines that
    cannot be skipped) and a complete total (options included)."""
    out = [
        "# Coûts des démonstrateurs",
        "",
        f"Généré par `python3 tools/demobom.py` le {date} depuis",
        "`docs/prix-demonstrateur.csv` (prix et sources, datés, « vérifié » ou",
        "« estimé ») et les nomenclatures des cartes. Les composants sont",
        "comptés au canal le moins cher ligne à ligne, rechange comprise ; le",
        "détail par repère est dans [`bom-demonstrateur-a.md`](bom-demonstrateur-a.md)",
        "et [`bom-demonstrateur-b.md`](bom-demonstrateur-b.md). Conversion",
        f"1 USD = {USD_TO_EUR} EUR, TVA {VAT:.0%} dans la colonne EUR TTC. Une ligne",
        "« optionnelle » n'entre pas dans le minimum : elle est comptée dans le",
        "total complet. L'outillage s'achète une fois pour les deux démonstrateurs.",
        "Deux scénarios : tout acheter, cartes assemblées par JLCPCB et établi à",
        "équiper ; puis souder soi-même avec le gros matériel déjà acheté",
        "(section « soudure maison » en fin de fiche).",
        "",
    ]
    grand: dict[str, dict[str, float]] = {}
    for key, title in (("a", MODELS["a"].title), ("b", MODELS["b"].title)):
        comp = components[key]
        minimum = comp["cheapest"]
        complete = comp["cheapest"]
        out += [f"## {title}", ""]
        out += [
            "| Poste | USD | EUR TTC | Statut | Source et remarque |",
            "|---|---|---|---|---|",
            f"| **Composants des cartes** ({comp['lines']:.0f} lignes, {comp['parts']:.0f} pièces, "
            f"rechange comprise) | {comp['cheapest']:.0f} | "
            f"{usd_to_eur_ttc(comp['cheapest']):.0f} | "
            f"relevés web | le moins cher de LCSC ou Mouser ligne à ligne ; tout chez LCSC "
            f"{comp['lcsc']:.0f} USD, tout chez Mouser {comp['mouser']:.0f} USD |",
            "",
        ]
        for cat in CATEGORIES:
            rows = [c for c in COSTS[key] if c[0] == cat]
            if not rows:
                continue
            out += [
                f"### {cat}",
                "",
                "| Poste | USD | EUR TTC | Statut | Source et remarque |",
                "|---|---|---|---|---|",
            ]
            sub = 0.0
            for _cat, pkey, qty, optional in rows:
                p = prices.get(pkey)
                if p is None:
                    out.append(f"| {pkey} | ? | ? | prix manquant | |")
                    continue
                usd = unit_price(p) * qty
                status = ("optionnel, " if optional else "") + (
                    "vérifié" if p.status == "verified" else "estimé"
                )
                label = pkey.replace("_", " ")
                out.append(
                    f"| {label} | {usd:.0f} | {usd_to_eur_ttc(usd):.0f} | {status} | {p.source} |"
                )
                complete += usd
                sub += usd
                if not optional:
                    minimum += usd
            out += [
                f"| *Sous-total {cat.lower()}* | *{sub:.0f}* | *{usd_to_eur_ttc(sub):.0f}* | | |",
                "",
            ]
        out += [
            "| Total | USD | EUR TTC |",
            "|---|---|---|",
            f"| **Minimum** (composants, cartes, port, matériaux et outillage indispensables) "
            f"| **{minimum:.0f}** | **{usd_to_eur_ttc(minimum):.0f}** |",
            f"| **Complet** (options comprises) | **{complete:.0f}** "
            f"| **{usd_to_eur_ttc(complete):.0f}** |",
            "",
        ]
        grand[key] = {"minimum": minimum, "complete": complete}
    # the pair: tools and the shared lines bought once
    shared = {
        "Tool_soldering_iron_kit",
        "Tool_multimeter",
        "Tool_bench_supply",
        "Tool_pocket_oscilloscope",
        "Nylon_M3_kit",
        "Dupont_and_USB_cables",
        "Magnets_ferrite_12_15_18x4",
        "Shipping_Mouser",
    }
    saved = 0.0
    for _cat, pkey, qty, _optional in COSTS["b"]:
        if pkey in shared and prices.get(pkey) is not None:
            saved += unit_price(prices[pkey]) * qty
    pair_min = (
        grand["a"]["minimum"]
        + grand["b"]["minimum"]
        - sum(
            unit_price(prices[k])
            for _c, k, _q, o in COSTS["b"]
            if k in shared and not o and prices.get(k)
        )
    )
    pair_full = grand["a"]["complete"] + grand["b"]["complete"] - saved
    out += [
        "## Les deux démonstrateurs ensemble",
        "",
        "L'outillage, la visserie, les nappes, les aimants et un port Mouser",
        "ne s'achètent qu'une fois ; une seule commande JLCPCB peut porter les",
        "quatre cartes, ce qui économise encore un port (non compté ici).",
        "",
        "| Total | USD | EUR TTC |",
        "|---|---|---|",
        f"| Minimum des deux | {pair_min:.0f} | {usd_to_eur_ttc(pair_min):.0f} |",
        f"| Complet des deux | {pair_full:.0f} | {usd_to_eur_ttc(pair_full):.0f} |",
        "",
        *scenario_home(prices, components),
        "## Ce que les prix ne couvrent pas",
        "",
        "- Les frais de dossier du transporteur à l'importation (10 à 20 EUR par",
        "  envoi hors UE), variables ; la TVA est comptée.",
        "- Le temps de montage et de mesure, et le contreplaqué ou le filament",
        "  déjà en stock chez qui bricole.",
        "- Les codes LCSC des condensateurs C0G d'adaptation, à relever le jour",
        "  de la commande : sans eux, l'assemblage les saute et ils se soudent au fer.",
        "",
    ]
    return "\n".join(out)


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
    components: dict[str, dict[str, float]] = {}
    for key in sorted(MODELS):
        model = MODELS[key]
        lines, skipped = aggregate(model)
        t = totals(lines, prices)
        components[key] = dict(t, lines=len(lines), parts=sum(ln.total for ln in lines))
        if args.model and key not in args.model:
            continue
        md = markdown(model, lines, skipped, prices, date)
        (args.out / f"bom-demonstrateur-{key}.md").write_text(md, encoding="utf-8")
        write_csv(args.out / f"bom-demonstrateur-{key}.csv", model, lines, prices)
        carts(args.out, model, lines, prices)
        print(
            f"model {key}: {len(lines)} lines, {sum(ln.total for ln in lines)} parts, "
            f"cheapest {t['cheapest']:.0f} USD, {t['unpriced']} unpriced"
        )
    (args.out / "couts-demonstrateurs.md").write_text(
        cost_sheet(prices, components, date), encoding="utf-8"
    )
    print(f"wrote {args.out / 'couts-demonstrateurs.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
