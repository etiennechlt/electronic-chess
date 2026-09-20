"""La liste d'achat du plateau (docs/bom-plateau.md) : quantités, prix et fichier
commité. Les garde-fous répondent à l'erreur 11 de la note 22, un BOM
silencieusement partiel : ici, une ligne sans prix est une erreur, et le
CSV commité doit être exactement celui que l'outil produit."""

import csv
from pathlib import Path

import bomagg

ROOT = Path(__file__).resolve().parents[1]
PRICES = ROOT / "docs/prix-plateau.csv"
LIST = ROOT / "docs/bom-plateau.csv"


def merged():
    plan = bomagg.parse_plan([f"{path}:{count}" for path, count in bomagg.PLATEAU])
    return plan, *bomagg.aggregate(plan)


def test_le_plateau_est_quatre_quadrants_et_un_cerveau():
    _plan, lines, parts, pads = merged()
    assert parts == {"quadrant": 1296, "brain": 103}  # 4 x 324, puis 103
    assert pads == {"quadrant": 80, "brain": 10}  # points de test, amarres, trous
    assert sum(parts.values()) == 1399
    assert len(lines) == 71


def test_les_quantites_de_chaque_carte_se_retrouvent_dans_le_total():
    _plan, lines, parts, _pads = merged()
    for board, expected in parts.items():
        assert sum(line.per_board.get(board, 0) for line in lines) == expected


def test_chaque_ligne_d_achat_porte_un_prix():
    """Aucune ligne ne disparaît du panier faute de prix : c'est le trou
    de l'erreur 11, transposé à l'approvisionnement."""
    _plan, lines, _parts, _pads = merged()
    prices = bomagg.read_prices(PRICES)
    absent = [line.key for line in lines if line.key not in prices]
    assert not absent, absent
    sans_prix = [
        line.key for line in lines if prices[line.key].cheapest()[1] is None
    ]
    assert not sans_prix, sans_prix


def test_le_csv_commite_est_celui_que_l_outil_produit(tmp_path):
    _plan, lines, _parts, _pads = merged()
    prices = bomagg.read_prices(PRICES)
    fresh = tmp_path / "bom-plateau.csv"
    bomagg.write_csv(fresh, lines, ["quadrant", "brain"], prices, 0.10)
    assert fresh.read_text(encoding="utf-8") == LIST.read_text(encoding="utf-8")


def test_les_rechanges_ajoutent_sans_jamais_retrancher():
    for quantity in (1, 2, 9, 10, 128, 182):
        extra = bomagg.spares(quantity, 0.10)
        assert extra >= 1
        assert extra >= 2 or quantity < 10
    assert bomagg.spares(128, 0.0) == 0


def test_le_frontal_analogique_fait_la_moitie_de_la_facture():
    """Le constat qui motive la section 2 de la note 16 : trois références
    du frontal pèsent plus que tout le reste du quadrant."""
    _plan, lines, _parts, _pads = merged()
    prices = bomagg.read_prices(PRICES)
    total, _count = bomagg.totals(lines, prices, 0.10)["mixed"]
    frontal = sum(
        cost
        for line, cost in bomagg.drivers(lines, prices, 0.10, len(lines))
        if line.mpn in ("ADG1607BCPZ", "AD8421ARZ", "OPA2810IDR")
    )
    assert frontal / total > 0.60


def test_le_fichier_de_prix_date_chaque_ligne_verifiee():
    with PRICES.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows
    for row in rows:
        assert row["Status"] in ("verified", "estimated"), row
        if row["Status"] == "verified":
            assert row["Source"].strip(), row  # une source, sinon ce n'est pas vérifié
