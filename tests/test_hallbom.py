"""The cost of the Hall layer of note 24: quantities from the yaml, prices
from the sheets with a status per line, the plateau's own spare rule."""

import csv
import pathlib

import pytest
from docfig.hallbom import (
    PRICES_HALL,
    PRICES_PLATEAU,
    USD_TO_EUR,
    VAT,
    hall_basket,
    hall_parts_basket,
    lc_front_end_usd,
    rfid_basket,
)

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_the_hall_sheet_has_the_plateau_columns_and_a_status_per_line():
    with PRICES_HALL.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    with PRICES_PLATEAU.open(encoding="utf-8") as fh:
        plateau_columns = csv.DictReader(fh).fieldnames
    assert rows and list(rows[0]) == plateau_columns
    for row in rows:
        assert row["Status"] in ("verified", "estimated"), row["Key"]
        assert row["Source"], row["Key"]
        assert row["LCSC_USD"] or row["Mouser_USD"], row["Key"]
        assert chr(0x2014) not in row["Source"] and chr(0x2013) not in row["Source"]


def test_quantities_follow_the_yaml(cfg):
    basket = hall_basket(cfg)
    by_key = {ln.key: ln for ln in basket.lines}
    hr = cfg.hall_rfid
    quadrants = (cfg.plateau.grid // cfg.plateau.quadrant.squares) ** 2
    assert by_key[hr.sensors[0].mpn].quantity == cfg.plateau.grid**2 == 64
    assert by_key[hr.mux.mpn].quantity == quadrants == 4
    assert by_key[hr.power_gating.fet].quantity == hr.power_gating.groups * quadrants == 16
    assert by_key["100n@C_0603_1608Metric"].quantity == 64 + 4
    # the spare rule of bomagg: ten percent, at least two from ten pieces, none on a lot
    assert by_key[hr.sensors[0].mpn].buy == 64 + 7
    assert by_key[hr.mux.mpn].buy == 4 + 1
    assert by_key["PCB_200x200_2L_x5"].buy == 1
    assert by_key[hr.esp32.devkit].buy == 1


def test_every_line_is_priced_and_the_totals_add_up(cfg):
    for basket in (hall_basket(cfg), hall_parts_basket(cfg), rfid_basket(cfg)):
        assert basket.all_priced, [ln.key for ln in basket.lines if not ln.priced]
        assert 0.0 < basket.exact_usd <= basket.buy_usd
        assert basket.buy_usd == pytest.approx(sum(ln.total_usd for ln in basket.lines))
        assert basket.eur_ht == pytest.approx(basket.buy_usd * USD_TO_EUR)
        assert basket.eur_ttc == pytest.approx(basket.eur_ht * (1.0 + VAT))
    assert hall_parts_basket(cfg).buy_usd < hall_basket(cfg).buy_usd


def test_the_presence_layer_costs_a_fraction_of_the_lc_front_end(cfg):
    # docs/bom-plateau.md: the three analog references of the four quadrants
    # make 113.85 USD with spares; the Hall sheets' components stay under half.
    lc = lc_front_end_usd()
    assert 100.0 < lc < 130.0
    assert hall_parts_basket(cfg).buy_usd < lc / 2.0
    # the sensor line is the bill of the Hall layer
    basket = hall_parts_basket(cfg)
    sensor = next(ln for ln in basket.lines if ln.key == cfg.hall_rfid.sensors[0].mpn)
    assert sensor.total_usd > 0.8 * basket.buy_usd


def test_rfid_tags_count_the_pieces_and_the_spare_queens(cfg):
    basket = rfid_basket(cfg)
    tags = next(ln for ln in basket.lines if ln.key == cfg.hall_rfid.nfc.tag.order_key)
    assert tags.quantity == 32 + 2 * cfg.pieces.spare_queens_per_side
    readers = next(ln for ln in basket.lines if ln.key == "MFRC522_QFN32")
    assert readers.quantity == cfg.plateau.grid**2


def test_the_page_carries_the_totals(cfg):
    from docfig import PAGES
    from docfig.common import fr_num

    page = PAGES["hall-rfid.html"](cfg)
    assert f"{fr_num(hall_basket(cfg).eur_ttc, 0)} €" in page
    assert f"{fr_num(rfid_basket(cfg).eur_ttc, 0)} €" in page
    assert "prix-hall.csv" in page
