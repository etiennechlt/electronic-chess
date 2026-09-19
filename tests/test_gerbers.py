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

# The boards `tools/gerbers.py` exports, and their archive. The two
# mockup archives come from the hand written layer list of their own
# export.sh and are checked only for the files every board needs.
GENERATED = {
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
        "F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu",
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
