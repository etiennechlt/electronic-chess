"""The .kicad_pro files: what makes a generated board openable in KiCad.

KiCad only opens a project, never a bare board, so each generated board
ships one. These tests pin the two things that matter: the file is the
JSON KiCad expects, and it carries the rules the generator enforced.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from analoggen.circuit import build_circuit  # noqa: E402
from analoggen.pcb import CLR, FAB_CLR, VIA_D, VIA_DRILL, W_FINE, design_rules  # noqa: E402
from analoggen.schematic import emit_schematic  # noqa: E402
from coilgen.project import DesignRules, project_json, schematic_root_uuid  # noqa: E402

HARDWARE = Path(__file__).resolve().parents[1] / "hardware" / "mockup-2x2"
BOARDS = ["analog-board", "coil-board"]


@pytest.mark.parametrize("name", BOARDS)
def test_committed_project_sits_next_to_its_board(name):
    """KiCad pairs the files by stem: same directory, same name."""
    directory = HARDWARE / name
    project = json.loads((directory / f"{name}.kicad_pro").read_text(encoding="utf-8"))
    assert project["meta"]["filename"] == f"{name}.kicad_pro"
    assert (directory / f"{name}.kicad_pcb").exists()


def test_analog_project_carries_the_router_rules():
    project = json.loads(project_json("analog-board", design_rules()))
    netclass = project["net_settings"]["classes"][0]
    assert netclass["clearance"] == CLR
    assert (netclass["via_diameter"], netclass["via_drill"]) == (VIA_D, VIA_DRILL)
    rules = project["board"]["design_settings"]["rules"]
    assert rules["min_clearance"] == FAB_CLR   # the exact fabrication gate
    assert rules["min_track_width"] == W_FINE  # entries into fine-pitch pads


def test_committed_analog_project_is_the_generated_one():
    directory = HARDWARE / "analog-board"
    schematic = (directory / "analog-board.kicad_sch").read_text(encoding="utf-8")
    expected = project_json("analog-board", design_rules(),
                            root_sheet_uuid=schematic_root_uuid(schematic))
    assert (directory / "analog-board.kicad_pro").read_text(encoding="utf-8") == expected


def test_root_uuid_is_the_one_the_schematic_header_declares(cfg):
    circuit, _chain = build_circuit(cfg)
    text = emit_schematic(circuit, "test")
    assert text.splitlines()[1].strip() == f"(uuid {schematic_root_uuid(text)})"


def test_root_uuid_refuses_a_foreign_file():
    with pytest.raises(ValueError):
        schematic_root_uuid("(kicad_pcb (version 20221018))")


def test_a_board_without_schematic_declares_no_sheet():
    project = json.loads(project_json("coil-board", DesignRules(0.13, 0.5, 0.6, 0.3)))
    assert project["sheets"] == []
    widths = project["board"]["design_settings"]["track_widths"]
    vias = project["board"]["design_settings"]["via_dimensions"]
    # KiCad's leading "use the netclass value" entries.
    assert widths[0] == 0.0
    assert vias[0] == {"diameter": 0.0, "drill": 0.0}
