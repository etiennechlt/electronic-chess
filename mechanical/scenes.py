"""Documentation scenes: exploded piece stack and assembled mockup view.

Builds throwaway CadQuery solids, meshes them and hands them to
render_stl.render as colored parts. Outputs land in docs/images/.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import cadquery as cq
import numpy as np
from cadquery import exporters
from common import load, puck_dims
from parts import magnet_bracket_base, magnet_cup, piece_puck
from render_stl import read_stl, render

from chessboard_calc.config import PieceType


def _tris(shape, dz=0.0, dx=0.0, dy=0.0) -> np.ndarray:
    moved = shape.translate((dx, dy, dz)) if hasattr(shape, "translate") \
        else shape.val().translate((dx, dy, dz))
    with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as fh:
        exporters.export(cq.Workplane(obj=moved) if not hasattr(moved, "val")
                         else moved, fh.name)
        return read_stl(Path(fh.name))


def exploded_piece(out: Path) -> None:
    cfg, pitch = load()
    dims = puck_dims(cfg, PieceType.ROOK, pitch)

    shell = piece_puck(dims).val()
    felt = cq.Workplane("XY").circle(dims.base_d / 2.0).extrude(0.8).val()
    coil = (cq.Workplane("XY").circle(dims.coil_d / 2.0)
            .circle(dims.coil_d * 0.2).extrude(dims.coil_h).val())
    cap = cq.Workplane("XY").box(3.2, 1.6, 1.0).val()
    magnet = (cq.Workplane("XY").circle(dims.magnet_d / 2.0)
              .extrude(dims.magnet_h).val())

    parts = [
        (_tris(felt, dz=-16.0), "#3a4652"),
        (_tris(coil, dz=-7.0), "#c98330"),
        (_tris(cap, dz=-6.5, dx=dims.coil_d / 2.0 + 4.0), "#b8b09a"),
        (_tris(magnet, dz=2.0), "#5d6a75"),
        (_tris(shell, dz=14.0), "#7fa8c9"),
    ]
    render(parts, out, elev=16.0, azim=-60.0)


def magnet_assembly(out: Path) -> None:
    cfg, _pitch = load()
    mm = cfg.mockup.coil_board.magnet_mount
    base = magnet_bracket_base(mm.hole_spacing_mm, cfg.carriage.magnet.d_mm).val()
    cup = magnet_cup(cfg.carriage.magnet.d_mm, cfg.carriage.magnet.h_mm).val()
    n42 = (cq.Workplane("XY").circle(cfg.carriage.magnet.d_mm / 2.0)
           .extrude(cfg.carriage.magnet.h_mm).val())
    parts = [
        (_tris(base, dz=0.0), "#7fa8c9"),
        (_tris(cup, dz=14.0), "#88b7a0"),
        (_tris(n42, dz=17.5), "#5d6a75"),
    ]
    render(parts, out, elev=24.0, azim=-50.0)


def mockup_assembly(out: Path) -> None:
    """Stylized full-mockup view: both boards, acrylic, pucks, bracket."""
    cfg, pitch = load()
    parts = []

    coil_pcb = cq.Workplane("XY").box(100, 100, 1.6, centered=(False, False, False)).val()
    parts.append((_tris(coil_pcb, dz=25.0), "#2c5c3f"))
    for cx, cy in [(25, 25), (75, 25), (25, 75), (75, 75)]:
        spiral = (cq.Workplane("XY").circle(20.0).circle(11.25)
                  .extrude(0.2).val().translate((cx, cy, 26.6)))
        parts.append((_tris(spiral), "#c98330"))
    for (cx, cy), piece in zip([(25, 75), (75, 75), (25, 25)],
                               [PieceType.ROOK, PieceType.BISHOP, PieceType.PAWN],
                               strict=False):
        dims = puck_dims(cfg, piece, pitch)
        puck = piece_puck(dims).val()
        parts.append((_tris(puck, dx=cx, dy=cy, dz=27.2), "#7fa8c9"))

    ana_pcb = cq.Workplane("XY").box(100, 62, 1.6, centered=(False, False, False)).val()
    parts.append((_tris(ana_pcb, dy=-66.0, dz=25.0), "#3a3f2c"))
    for dx, dy, w, d, h in [(20, -50, 12, 12, 2.5), (48, -30, 6, 5, 1.6),
                            (62, -40, 5, 4, 1.6), (75, -40, 5, 4, 1.6),
                            (90, -32, 5, 4, 1.6), (12, -38, 7, 6, 2.0)]:
        chip = cq.Workplane("XY").box(w, d, h, centered=(False, False, False)).val()
        parts.append((_tris(chip, dx=dx, dy=dy, dz=26.6), "#4a5560"))

    mm = cfg.mockup.coil_board.magnet_mount
    base = magnet_bracket_base(mm.hole_spacing_mm, cfg.carriage.magnet.d_mm).val()
    parts.append((_tris(base, dx=25.0, dy=75.0, dz=6.0), "#88b7a0"))
    cup = magnet_cup(cfg.carriage.magnet.d_mm, cfg.carriage.magnet.h_mm).val()
    parts.append((_tris(cup, dx=25.0, dy=75.0, dz=12.0), "#88b7a0"))
    for hx, hy in [(5, 5), (95, 5), (5, 95), (95, 95)]:
        leg = cq.Workplane("XY").circle(2.4).extrude(25.0).val()
        parts.append((_tris(leg, dx=hx, dy=hy), "#5d6a75"))

    render(parts, out, elev=32.0, azim=-40.0)


if __name__ == "__main__":
    out_dir = Path(__file__).resolve().parents[1] / "docs" / "images"
    exploded_piece(out_dir / "piece-exploded.png")
    magnet_assembly(out_dir / "magnet-bracket.png")
    mockup_assembly(out_dir / "mockup-3d.png")
    print("scenes rendered")
