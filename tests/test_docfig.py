"""The documentation figures and pages build from the yaml and carry the
model's numbers."""

import xml.etree.ElementTree as ET

import pytest
from docfig import FIGURES, PAGES
from docfig.common import fr_num, standalone
from docfig.q import plan_rows

from chessboard_calc.config import Color, PieceType
from chessboard_calc.resonance import frequency_plan, ringdown_tau_us


@pytest.mark.parametrize("name", sorted(FIGURES))
def test_every_figure_is_well_formed_svg(cfg, name):
    svg = standalone(FIGURES[name](cfg))
    root = ET.fromstring(svg)
    assert root.tag.endswith("svg")
    assert root.get("viewBox", "").startswith("0 0 ")
    assert root.get("aria-label")
    assert chr(0x2014) not in svg and chr(0x2013) not in svg  # no dashes in the texts


def test_plan_figure_lists_the_twelve_notes(cfg):
    svg = FIGURES["q-plan.svg"](cfg)
    for line in frequency_plan(cfg).lines:
        assert f">{line.f0_hz / 1e3:.0f}<" in svg
    assert len(plan_rows(cfg)) == 12


def test_ringdown_figure_uses_the_model_tau(cfg):
    svg = FIGURES["q-ringdown.svg"](cfg)
    f0 = frequency_plan(cfg).line(PieceType.PAWN, Color.BLACK).f0_hz
    tau = ringdown_tau_us(f0, cfg.resonator.q_nominal)
    assert f"τ = {fr_num(tau, 0)} µs" in svg


def test_fr_num():
    assert fr_num(7.06) == "7,1"
    assert fr_num(50.0, 0) == "50"
    assert fr_num(2.5) == "2,5"
    assert fr_num(1234.5, 1) == "1 234,5"


def test_tuto_figures_carry_the_four_test_pieces(cfg):
    from docfig.tuto import bench_pucks

    rows = bench_pucks(cfg)
    assert [r["piece"].value for r in rows] == [tp.piece.value for tp in cfg.mockup.test_pieces]
    puck_svg = FIGURES["tuto-puck.svg"](cfg)
    for r in rows:
        assert f">{fr_num(r['cap_nF'])} nF<" in puck_svg
        assert f">{r['f0_khz']:.0f} kHz<" in puck_svg
    tests_svg = FIGURES["tuto-tests.svg"](cfg)
    assert f"{rows[0]['f0_khz']:.0f} kHz" in tests_svg  # the first puck's note is the first check


TEXT_ONLY_PAGES = {
    "couts-demonstrateurs.html",
    "bom-demonstrateur-a.html",
    "bom-demonstrateur-b.html",
}


@pytest.mark.parametrize("name", sorted(PAGES))
def test_every_page_is_a_whole_document(cfg, name):
    """The pages of docs/pages: one self-contained file each, all their
    placeholders filled, their figures embedded, and the typography of the
    project (no dash, no absolute path)."""
    page = PAGES[name](cfg)
    assert page.startswith("<!doctype html>") and page.rstrip().endswith("</html>")
    assert "<title>" in page and "<style>" in page
    assert "{{" not in page
    assert chr(0x2014) not in page and chr(0x2013) not in page
    assert "/home/" not in page
    if name not in TEXT_ONLY_PAGES:
        assert page.count("<svg") >= 1  # the figures travel with the page


def test_the_q_page_carries_the_model_numbers(cfg):
    page = PAGES["facteur-q.html"](cfg)
    plan = frequency_plan(cfg)
    assert f"Q = {cfg.resonator.q_nominal:.0f}" in page
    for line in plan.lines:  # the twelve notes of the plan, in its table
        assert f">{fr_num(line.f0_hz / 1e3, 1)}<" in page


def test_the_hall_page_has_three_readings_and_the_model_numbers(cfg):
    from chessboard_calc.hall import hall_budget
    from chessboard_calc.nfc import analog_mux_verdict

    page = PAGES["hall-rfid.html"](cfg)
    for mode in ("simple", "technique", "implementation"):
        assert f'id="{mode}"' in page and f'data-mode="{mode}"' in page
    b = hall_budget(cfg, cfg.pitch.plateau_mm)
    assert f"{fr_num(b.threshold_mT)} mT" in page
    assert f"{fr_num(b.fields[PieceType.PAWN].b_nominal_mT)} mT" in page
    assert f"{fr_num(b.lift_margin)}" in page
    v = analog_mux_verdict(cfg, cfg.pitch.plateau_mm)
    assert f"Q = {fr_num(v.q_with_switch, 2)}" in page
    # the interactive curve travels twice (two readings) without duplicate ids
    assert page.count('data-curve="1"') == 2
    import re

    ids = re.findall(r'\sid="([^"]+)"', page)
    assert len(ids) == len(set(ids))


def test_hall_figures_carry_the_sensor_and_the_threshold(cfg):
    from chessboard_calc.hall import hall_budget

    b = hall_budget(cfg, cfg.pitch.plateau_mm)
    stack = FIGURES["hall-coupe.svg"](cfg)
    assert b.sensor.part in stack
    assert f"{fr_num(b.z_nominal_mm)} mm" in stack
    curve = FIGURES["hall-champ.svg"](cfg)
    assert f"seuil de présence : {fr_num(b.threshold_mT)} mT" in curve
    classes = FIGURES["hall-classes.svg"](cfg)
    assert "1 groupe(s)" in classes and "3 groupe(s)" in classes


def test_the_demonstrator_pages_render_their_notes(cfg):
    """The pages of notes 26 and 27 are the notes themselves: title, the
    sections, the tables and the figures of the Markdown, the links to
    the other pages, the renders embedded."""
    from chessboard_calc.config import Color, PieceType

    lc = PAGES["demonstrateur-lc.html"](cfg)
    f_pawn = frequency_plan(cfg).line(PieceType.PAWN, Color.BLACK).f0_hz
    assert "<h1>Démonstrateur A" in lc
    assert f">{fr_num(f_pawn / 1e3)}<" in lc  # the plan table, from the note
    assert 'href="demonstrateur-hall-rfid.html"' in lc  # the twin note has a page
    assert 'href="couts-demonstrateurs.html"' in lc
    assert "github.com/etiennechlt/electronic-chess/blob/main/hardware/mockup-2x2" in lc
    assert 'src="data:image/png;base64,' in lc  # the board renders travel with the page
    assert "<dl><dt>" in lc  # the lexicon
    assert "<pre><code>" in lc
    hr = PAGES["demonstrateur-hall-rfid.html"](cfg)
    assert "<h1>Démonstrateur B" in hr
    assert "DRV5055A3" in hr and "MFRC522" in hr
    assert hr.count("<section>") == 8
    assert "![" not in hr and "](" not in hr  # no Markdown left behind


def test_the_cost_page_follows_the_sheet(cfg):
    page = PAGES["couts-demonstrateurs.html"](cfg)
    assert "Scénario : soudure maison" in page
    assert '<td class="n">' in page  # the amounts are right-aligned
