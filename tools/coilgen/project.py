"""Minimal KiCad 7 project writer (.kicad_pro, JSON).

KiCad has no way to open a bare .kicad_pcb from the project manager:
without a project file next to it, only the standalone board editor
opens the file, and it then offers to create the missing project. Both
generated boards therefore ship a project file carrying the design
rules the generator actually enforced, so a double click opens the
board (and, for the analog board, its schematic) with a DRC already
set to the numbers of the generator.

Only the keys this project cares about are written; KiCad fills every
other setting with its own defaults when it loads the file.
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from dataclasses import dataclass, field

PROJECT_VERSION = 1
NET_SETTINGS_VERSION = 3

_ROOT_UUID = re.compile(r"\(uuid\s+([0-9a-fA-F-]+)\)")


def schematic_root_uuid(text: str) -> str:
    """Root sheet uuid of a generated schematic, for the sheet list.

    The emitter writes it in the header, before any other uuid.
    """
    if not text.lstrip().startswith("(kicad_sch"):
        raise ValueError("not a KiCad schematic")
    match = _ROOT_UUID.search(text)
    if match is None:
        raise ValueError("no root uuid found in the schematic")
    return match.group(1)


@dataclass(frozen=True)
class DesignRules:
    """The numbers the generator routed with, as KiCad reads them.

    The netclass values are what the editor offers when routing by
    hand; the ``min_*`` values are what the DRC refuses. They differ on
    purpose: the router keeps a design clearance and only the exact
    fabrication gate is a hard failure.
    """

    clearance_mm: float
    track_width_mm: float
    via_diameter_mm: float
    via_drill_mm: float
    min_clearance_mm: float | None = None
    min_track_width_mm: float | None = None
    min_via_diameter_mm: float | None = None
    min_hole_mm: float | None = None
    edge_clearance_mm: float = 0.2
    track_widths_mm: Sequence[float] = field(default_factory=tuple)
    via_sizes_mm: Sequence[tuple[float, float]] = field(default_factory=tuple)

    def rules_block(self) -> dict[str, float]:
        return {
            "max_error": 0.005,
            "min_clearance": _fallback(self.min_clearance_mm, self.clearance_mm),
            "min_copper_edge_clearance": self.edge_clearance_mm,
            "min_hole_clearance": 0.25,
            "min_hole_to_hole": 0.25,
            "min_microvia_diameter": 0.2,
            "min_microvia_drill": 0.1,
            "min_through_hole_diameter": _fallback(self.min_hole_mm, self.via_drill_mm),
            "min_track_width": _fallback(self.min_track_width_mm, self.track_width_mm),
            "min_via_diameter": _fallback(self.min_via_diameter_mm, self.via_diameter_mm),
        }


def _fallback(value: float | None, default: float) -> float:
    return default if value is None else value


def project_json(name: str, rules: DesignRules, *, root_sheet_uuid: str | None = None) -> str:
    """Serialize a .kicad_pro for the board file named ``name``.

    ``name`` is the common stem of the board and schematic files: KiCad
    pairs ``name.kicad_pro`` with ``name.kicad_pcb`` and
    ``name.kicad_sch`` in the same directory. Pass the schematic root
    uuid when there is a schematic, so the editors agree on the sheet.
    """
    # 0.0 in these lists is KiCad's "use the netclass value" entry and
    # must stay first.
    widths = [0.0, rules.track_width_mm, *rules.track_widths_mm]
    vias = [(0.0, 0.0), (rules.via_diameter_mm, rules.via_drill_mm), *rules.via_sizes_mm]
    sheets = [[root_sheet_uuid, ""]] if root_sheet_uuid else []
    project = {
        "board": {
            "3dviewports": [],
            "design_settings": {
                "defaults": {
                    "board_outline_line_width": 0.05,
                    "copper_line_width": 0.2,
                    "copper_text_size_h": 1.5,
                    "copper_text_size_v": 1.5,
                    "copper_text_thickness": 0.3,
                    "other_line_width": 0.1,
                    "silk_line_width": 0.1,
                    "silk_text_size_h": 1.0,
                    "silk_text_size_v": 1.0,
                    "silk_text_thickness": 0.15,
                },
                "diff_pair_dimensions": [],
                "drc_exclusions": [],
                "rules": rules.rules_block(),
                "track_widths": _unique(widths),
                "via_dimensions": [{"diameter": d, "drill": k} for d, k in _unique_pairs(vias)],
            },
            "layer_presets": [],
            "viewports": [],
        },
        "boards": [],
        "cvpcb": {"equivalence_files": []},
        "libraries": {"pinned_footprint_libs": [], "pinned_symbol_libs": []},
        "meta": {"filename": f"{name}.kicad_pro", "version": PROJECT_VERSION},
        "net_settings": {
            "classes": [
                {
                    "bus_width": 12,
                    "clearance": rules.clearance_mm,
                    "diff_pair_gap": 0.25,
                    "diff_pair_via_gap": 0.25,
                    "diff_pair_width": 0.2,
                    "line_style": 0,
                    "microvia_diameter": 0.3,
                    "microvia_drill": 0.1,
                    "name": "Default",
                    "pcb_color": "rgba(0, 0, 0, 0.000)",
                    "schematic_color": "rgba(0, 0, 0, 0.000)",
                    "track_width": rules.track_width_mm,
                    "via_diameter": rules.via_diameter_mm,
                    "via_drill": rules.via_drill_mm,
                    "wire_width": 6,
                }
            ],
            "meta": {"version": NET_SETTINGS_VERSION},
            "net_colors": None,
            "netclass_assignments": None,
            "netclass_patterns": [],
        },
        "pcbnew": {
            "last_paths": {
                "gencad": "",
                "idf": "",
                "netlist": "",
                "specctra_dsn": "",
                "step": "",
                "vrml": "",
            },
            "page_layout_descr_file": "",
        },
        "schematic": {
            "legacy_lib_dir": "",
            "legacy_lib_list": [],
            "page_layout_descr_file": "",
        },
        "sheets": sheets,
        "text_variables": {},
    }
    return json.dumps(project, indent=2, sort_keys=True) + "\n"


def _unique(values: Sequence[float]) -> list[float]:
    out: list[float] = []
    for v in values:
        if not any(abs(v - kept) < 1e-9 for kept in out):
            out.append(round(float(v), 4))
    return out


def _unique_pairs(pairs: Sequence[tuple[float, float]]) -> list[tuple[float, float]]:
    out: list[tuple[float, float]] = []
    for d, k in pairs:
        if not any(abs(d - a) < 1e-9 and abs(k - b) < 1e-9 for a, b in out):
            out.append((round(float(d), 4), round(float(k), 4)))
    return out
