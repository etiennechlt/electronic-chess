"""Documentation scenes: the 8x8 board and its clock (ADR 0010), plus the
exploded piece stack and the retired 2x2 mockup.

Builds CadQuery solids, meshes them and hands them to render_stl.render
as colored parts. Outputs land in docs/images/.

`--film-meshes DIR` exports instead the meshes the 3D films load
(media/pitch): the thin board layer by layer, the gantry base and the
clock, as binary STL with a manifest.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import cadquery as cq
import clock
import numpy as np
import plateau
from cadquery import exporters
from common import Part, load, puck_dims
from parts import magnet_bracket_base, magnet_cup, piece_puck
from render_stl import read_stl, render

from chessboard_calc.config import PieceType


def _tris(shape, dz=0.0, dx=0.0, dy=0.0) -> np.ndarray:
    moved = (
        shape.translate((dx, dy, dz))
        if hasattr(shape, "translate")
        else shape.val().translate((dx, dy, dz))
    )
    with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as fh:
        exporters.export(cq.Workplane(obj=moved) if not hasattr(moved, "val") else moved, fh.name)
        return read_stl(Path(fh.name))


def exploded_piece(out: Path) -> None:
    cfg, pitch = load()
    dims = puck_dims(cfg, PieceType.ROOK, pitch)

    shell = piece_puck(dims).val()
    felt = cq.Workplane("XY").circle(dims.base_d / 2.0).extrude(0.8).val()
    coil = (
        cq.Workplane("XY")
        .circle(dims.coil_d / 2.0)
        .circle(dims.coil_d * 0.2)
        .extrude(dims.coil_h)
        .val()
    )
    cap = cq.Workplane("XY").box(3.2, 1.6, 1.0).val()
    magnet = cq.Workplane("XY").circle(dims.magnet_d / 2.0).extrude(dims.magnet_h).val()

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
    n42 = (
        cq.Workplane("XY")
        .circle(cfg.carriage.magnet.d_mm / 2.0)
        .extrude(cfg.carriage.magnet.h_mm)
        .val()
    )
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
        spiral = (
            cq.Workplane("XY")
            .circle(20.0)
            .circle(11.25)
            .extrude(0.2)
            .val()
            .translate((cx, cy, 26.6))
        )
        parts.append((_tris(spiral), "#c98330"))
    for (cx, cy), piece in zip(
        [(25, 75), (75, 75), (25, 25)],
        [PieceType.ROOK, PieceType.BISHOP, PieceType.PAWN],
        strict=False,
    ):
        dims = puck_dims(cfg, piece, pitch)
        puck = piece_puck(dims).val()
        parts.append((_tris(puck, dx=cx, dy=cy, dz=27.2), "#7fa8c9"))

    ana_pcb = cq.Workplane("XY").box(100, 62, 1.6, centered=(False, False, False)).val()
    parts.append((_tris(ana_pcb, dy=-66.0, dz=25.0), "#3a3f2c"))
    for dx, dy, w, d, h in [
        (20, -50, 12, 12, 2.5),
        (48, -30, 6, 5, 1.6),
        (62, -40, 5, 4, 1.6),
        (75, -40, 5, 4, 1.6),
        (90, -32, 5, 4, 1.6),
        (12, -38, 7, 6, 2.0),
    ]:
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


def render_parts(parts: list[Part], out: Path, elev: float, azim: float) -> None:
    render([(_tris(p.shape), p.color) for p in parts], out, elev=elev, azim=azim)


def plateau_scenes(out_dir: Path) -> None:
    """The 8x8 board: thin base closed and exploded, gantry base open and
    closed, the clock alone."""
    cfg, _ = load()
    thin = plateau.assembly(cfg, gantry=False)
    render_parts(thin, out_dir / "plateau-fin.png", elev=30.0, azim=-55.0)
    render_parts(
        plateau.exploded(thin, 70.0), out_dir / "plateau-eclate.png", elev=18.0, azim=-55.0
    )
    gantry = plateau.assembly(cfg, gantry=True)
    render_parts(
        [p for p in gantry if p.group not in ("quad", "bois", "pieces")],
        out_dir / "plateau-chariot-ouvert.png",
        elev=40.0,
        azim=-55.0,
    )
    render_parts(gantry, out_dir / "plateau-chariot.png", elev=30.0, azim=-55.0)
    render_parts(clock.assembly(cfg), out_dir / "horloge.png", elev=28.0, azim=-35.0)
    render_parts(
        plateau.exploded(clock.assembly(cfg), 25.0),
        out_dir / "horloge-eclatee.png",
        elev=22.0,
        azim=-35.0,
    )


# Mesh resolution of the film exports: coarse enough to keep the files small,
# fine enough that no facet shows at the films' framing.
FILM_TOLERANCE_MM = 0.3
FILM_ANGULAR_TOLERANCE = 0.5


def _export_layer(parts: list[Part], out_dir: Path, set_name: str, layer: str) -> list[dict]:
    """One STL per colour of a layer, so the scene can give each its material."""
    entries = []
    for color in sorted({p.color for p in parts}):
        name = f"{set_name}-{layer}-{color.lstrip('#')}.stl"
        compound = cq.Compound.makeCompound([p.shape for p in parts if p.color == color])
        exporters.export(
            compound,
            str(out_dir / name),
            tolerance=FILM_TOLERANCE_MM,
            angularTolerance=FILM_ANGULAR_TOLERANCE,
        )
        entries.append({"file": name, "set": set_name, "layer": layer, "color": color})
    return entries


def film_meshes(out_dir: Path) -> None:
    """The solids of the films, in the CadQuery frame (mm, z up, play area from
    the origin): `fin` is the thin board split into the layers the build film
    drops one at a time, `chariot` the gantry base without its board module,
    `horloge` the clock with its rocker bar apart so the scene can tilt it."""
    cfg, _ = load()
    g = plateau.geometry(cfg)
    out_dir.mkdir(parents=True, exist_ok=True)

    def quadrant(p: Part) -> int:
        c = p.shape.BoundingBox().center
        return int(c.y >= g.quadrant_mm) * 2 + int(c.x >= g.quadrant_mm)

    thin = plateau.assembly(cfg, gantry=False, with_pieces=False)
    cells = [p for p in thin if p.group == "elec" and p.name.startswith("cellule")]
    layers = [("base", [p for p in thin if p.group == "base"])]
    layers += [(f"cellule-{k + 1}", [cell]) for k, cell in enumerate(cells)]
    layers.append(("cartes", [p for p in thin if p.group == "elec" and p not in cells]))
    layers += [
        (f"quadrant-{k + 1}", [p for p in thin if p.group == "quad" and quadrant(p) == k])
        for k in range(4)
    ]
    layers.append(("bois", [p for p in thin if p.group == "bois"]))
    meshes = []
    for layer, parts in layers:
        meshes += _export_layer(parts, out_dir, "fin", layer)

    gantry = plateau.assembly(cfg, gantry=True, with_pieces=False)
    meshes += _export_layer(
        [p for p in gantry if p.group not in ("quad", "bois")], out_dir, "chariot", "base"
    )

    parts = clock.assembly(cfg)
    bar = [p for p in parts if p.name.startswith("barre")]
    meshes += _export_layer([p for p in parts if p not in bar], out_dir, "horloge", "boitier")
    meshes += _export_layer(bar, out_dir, "horloge", "barre")
    bb = cq.Compound.makeCompound([p.shape for p in bar]).BoundingBox()
    manifest = {
        "frame": "CadQuery, mm, z up",
        "meshes": meshes,
        "clock_pivot_mm": [round(bb.center.x, 2), round(bb.center.y, 2), round(bb.zmin, 2)],
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    print(f"{len(meshes)} meshes in {out_dir}")


if __name__ == "__main__":
    if "--film-meshes" in sys.argv:
        film_meshes(Path(sys.argv[sys.argv.index("--film-meshes") + 1]))
        sys.exit(0)
    out_dir = Path(__file__).resolve().parents[1] / "docs" / "images"
    plateau_scenes(out_dir)
    exploded_piece(out_dir / "piece-exploded.png")
    magnet_assembly(out_dir / "magnet-bracket.png")
    mockup_assembly(out_dir / "mockup-3d.png")
    print("scenes rendered")
