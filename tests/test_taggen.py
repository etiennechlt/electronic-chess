"""The tag panel of the demonstrator (note 27): discs sized by the model,
coils that turn the same way on both layers, a panel that fits the price
tier, a one-piece outline, and generated lists that agree."""

import csv
import io

import numpy as np
import pytest
from analoggen.fplib import FOOTPRINT_DIR
from coilgen.geometry import spiral_points
from taggen import panel as tg

from chessboard_calc import nfc

pytestmark = pytest.mark.skipif(not FOOTPRINT_DIR.exists(), reason="KiCad libraries not installed")


@pytest.fixture(scope="module")
def result(cfg):
    return tg.build_tag_panel(cfg)


def test_panel_holds_every_variant_and_fits_the_tier(cfg, result):
    tags = cfg.hall_rfid.mockup.tags
    n = cfg.hall_rfid.demo.tags.per_variant
    expected = sum(len(trims) for trims in tags.trims_pF.values()) * n
    assert len(result.tags) == expected == 15
    assert result.panel_mm[0] == cfg.hall_rfid.demo.tags.panel_mm[0]
    assert result.panel_mm[1] <= cfg.hall_rfid.demo.tags.panel_mm[1]
    by_variant = {}
    for t in result.tags:
        by_variant[t.variant] = by_variant.get(t.variant, 0) + 1
    assert set(by_variant.values()) == {n}
    assert {"P", "P+15pF", "P+22pF", "G", "G+10pF"} == set(by_variant)


def test_discs_are_the_model_discs(cfg, result):
    for t in result.tags:
        geo = nfc.tag_geometry(cfg, 50.0, t.size)
        assert t.disc_mm == geo.disc_mm
        assert t.geometry.turns_per_layer == geo.turns_per_layer
    sizes = {t.size: t.disc_mm for t in result.tags}
    assert sizes == {"P": pytest.approx(14.5), "G": pytest.approx(19.5)}


def test_both_layers_turn_the_same_way():
    centre = (0.0, 0.0)
    top = spiral_points(centre, 5.05, 6.65, 5, tg.START_ANGLE_DEG, -1)
    bottom = spiral_points(centre, 6.65, 5.05, 5, tg.START_ANGLE_DEG, -1)
    a, b = tg.coil_turning_deg(top, centre), tg.coil_turning_deg(bottom, centre)
    assert a == pytest.approx(-1800.0, abs=1.0) and b == pytest.approx(-1800.0, abs=1.0)
    # both ends of the coil sit at the start angle: the inner ends meet at
    # the chip, the outer ends at the via on the rim
    assert np.allclose(top[0], bottom[-1]) and np.allclose(top[-1], bottom[0])


def test_outline_is_one_piece_with_voids(result):
    assert len(result.outline_rings) > 1
    outer = result.outline_rings[0]
    xs = [x for x, _ in outer]
    ys = [y for _, y in outer]
    assert (min(xs), min(ys)) == (0.0, 0.0)
    assert (max(xs), max(ys)) == result.panel_mm


def test_bites_sit_outside_every_disc(result):
    for bx, by in result.bites:
        for t in result.tags:
            d = ((bx - t.centre[0]) ** 2 + (by - t.centre[1]) ** 2) ** 0.5
            assert d >= t.disc_mm / 2.0 - 1e-6, (bx, by, t.ref)


def test_lists_agree(result):
    rows = list(csv.DictReader(io.StringIO(tg.bom_csv(result))))
    chips = [r for r in rows if r["Footprint"].startswith("TSSOP-8")]
    assert sum(int(r["Qty"]) for r in chips) == len(result.tags)
    assert all(r["MPN"] == "NT3H2111W0FTTJ" for r in chips)
    bare = [r for r in rows if r["Value"] == "non montee"]
    assert bare and all(r["DNP"] == "DNP" for r in bare)
    cpl = list(csv.DictReader(io.StringIO(tg.jlc_cpl_csv(result))))
    jlc = list(csv.DictReader(io.StringIO(tg.jlc_bom_csv(result))))
    placed = {d for r in jlc for d in r["Designator"].split(",")}
    assert {r["Designator"] for r in cpl} == placed


def test_board_declares_two_layers_and_the_tag_thickness(cfg, result):
    text = result.board.serialize()
    assert f"(thickness {cfg.hall_rfid.mockup.tags.board_mm:g})" in text
    assert '(1 "In1.Cu" signal)' not in text
    assert text.count("(net_tie_pad_groups") == 0
