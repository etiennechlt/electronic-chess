"""The fabrication archives: layer stack, drills and outline, pinned.

`tools/gerbers.py` reads the layer set off the board instead of
carrying one list per project, so what protects the archives is a
comparison against the stack the `.kicad_pcb` itself declares: a
missing inner layer or a drill file left out is a board the fabricator
etches wrong, and no DRC would say a word about it.
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path

import gerbers
import pytest

ROOT = Path(__file__).resolve().parents[1]

# The boards `tools/gerbers.py` exports, and their archive. The coil
# board still comes from the hand written layer list of its own
# export.sh and is checked only for the files every board needs.
GENERATED = {
    "analog-board": ROOT / "hardware/mockup-2x2/analog-board",
    "bench": ROOT / "hardware/bench",
    "quadrant-2x2": ROOT / "hardware/quadrant-2x2",
}
ARCHIVES = sorted(ROOT.glob("hardware/**/*-gerbers.zip"))


def declared_stack(board_path: Path) -> list[str]:
    """The copper layers the board file enables, outside in."""
    text = board_path.read_text(encoding="utf-8", errors="replace")
    start = text.index("(layers")
    depth = 0
    for end in range(start, len(text)):
        if text[end] == "(":
            depth += 1
        elif text[end] == ")":
            depth -= 1
            if depth == 0:
                break
    return re.findall(r'"([FB]\.Cu|In\d+\.Cu)"', text[start : end + 1])


def test_copper_layers_names_the_stack_outside_in():
    class Board:
        def __init__(self, count):
            self.count = count

        def GetCopperLayerCount(self):  # noqa: N802  (KiCad's own spelling)
            return self.count

    assert gerbers.copper_layers(Board(2)) == ["F.Cu", "B.Cu"]
    assert gerbers.copper_layers(Board(4)) == ["F.Cu", "In1.Cu", "In2.Cu", "B.Cu"]
    assert gerbers.copper_layers(Board(6)) == [
        "F.Cu",
        "In1.Cu",
        "In2.Cu",
        "In3.Cu",
        "In4.Cu",
        "B.Cu",
    ]


def test_the_repository_ships_an_archive_for_every_board_with_closed_routing():
    assert {p.parent.name for p in ARCHIVES} >= set(GENERATED)


@pytest.mark.parametrize("archive", ARCHIVES, ids=lambda p: p.parent.name)
def test_every_archive_carries_its_outline_drills_and_job(archive):
    names = zipfile.ZipFile(archive).namelist()
    assert any(n.endswith("-Edge_Cuts.gm1") for n in names), "board outline missing"
    assert any(n.endswith("-PTH.drl") for n in names), "plated drills missing"
    assert any(n.endswith("-NPTH.drl") for n in names), "non plated drills missing"
    assert any(n.endswith("-job.gbrjob") for n in names), "gerber job file missing"
    assert any(n.endswith("-F_Mask.gts") for n in names)
    assert any(n.endswith("-B_Mask.gbs") for n in names)


@pytest.mark.parametrize("board,directory", sorted(GENERATED.items()))
def test_the_generated_archives_carry_the_stack_the_board_declares(board, directory):
    stack = declared_stack(directory / f"{board}.kicad_pcb")
    names = zipfile.ZipFile(directory / f"{board}-gerbers.zip").namelist()
    for layer in stack:
        stem = f"{board}-{layer.replace('.', '_')}."
        assert any(n.startswith(stem) for n in names), f"{layer} missing from the archive"
    inner = sum(n.startswith(f"{board}-In") for n in names)
    assert inner == len(stack) - 2, "inner layers of the archive and of the board differ"


@pytest.mark.parametrize("board,directory", sorted(GENERATED.items()))
def test_the_generated_archives_are_stamped_alike(board, directory):
    """One instant for every entry: re-exporting an unchanged board leaves a
    diff made of the plots themselves, never of the dates of the archive."""
    with zipfile.ZipFile(directory / f"{board}-gerbers.zip") as zf:
        stamps = {info.date_time for info in zf.infolist()}
    assert stamps == {gerbers.ZIP_EPOCH}


@pytest.mark.parametrize("archive", ARCHIVES, ids=lambda p: p.parent.name)
def test_every_archive_records_the_board_it_was_plotted_from(archive):
    """A zip says nothing about which board it came from; the digest does.

    `tools/gerbers.py` writes a `sha256sum` file next to the archive
    with the fingerprint of the board and of the archive. Comparing it
    against what is committed is what catches an archive that has
    stopped matching its source, which no DRC and no viewer would.
    """
    digest = archive.with_suffix(".sha256")
    assert digest.is_file(), f"no digest next to {archive.name}"
    recorded = {}
    for line in digest.read_text(encoding="utf-8").split("\n"):
        if line.strip():
            value, name = line.split()
            recorded[name] = value
    board = archive.parent / f"{archive.parent.name}.kicad_pcb"
    assert set(recorded) == {board.name, archive.name}
    for path in (board, archive):
        assert gerbers.sha256(path) == recorded[path.name], f"{path.name} changed since the export"


def test_the_order_audit_clears_the_boards_whose_routing_is_closed():
    """`tools/fabcheck.py` is the pre-order audit, run as a test.

    It answers the two questions a fabricator's upload cannot: whether
    the archive still matches the board it claims to come from, and how
    much of the board an assembly order would actually populate.
    """
    import fabcheck

    audits = {
        a.name: a
        for a in (
            fabcheck.audit(p)
            for p in sorted({q.parent for q in (ROOT / "hardware").rglob("*.kicad_pcb")})
        )
        if a is not None
    }
    # every archive in the repository matches its board
    assert [a.name for a in audits.values() if a.archive and a.digest != "ok"] == []
    # the boards ordered as bare PCBs are clear, and say so
    for name in ("quadrant-2x2", "bench"):
        assert audits[name].ready_bare, name
    # a board whose routing is open ships no archive at all
    for name in ("brain", "power", "clock", "coil-board"):
        assert audits[name].archive is None, name
    # and the assembly BOM of the ordered boards is known to be partial
    assert audits["quadrant-2x2"].assembled < audits["quadrant-2x2"].parts
    assert audits["quadrant-2x2"].cpl_orphans == []
