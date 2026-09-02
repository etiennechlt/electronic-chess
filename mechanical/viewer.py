"""Interactive 3D viewer of the board and the clock (three.js), generated
from the same CadQuery models as the documentation renders.

    python mechanical/viewer.py [out.html]

Writes a self-contained HTML page (default mechanical/exports/plateau-3d.html):
both bases, exploded view, layers to hide, part names on hover, stack and
footprint tables from chessboard_calc.plateau. The page loads three.js
from cdnjs and everything else is inline.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import clock
import plateau
from common import Part, load

from chessboard_calc.config import BoardConfig
from chessboard_calc.plateau import gantry_base, geometry, thin_base

TEMPLATE = Path(__file__).parent / "viewer_template.html"
DEFAULT_OUT = Path(__file__).parent / "exports" / "plateau-3d.html"
TOLERANCE_MM = 0.3
ANGULAR_TOLERANCE = 0.5
CLOCK_GAP_MM = 40.0
CLOCK_Y_MM = 60.0


def mesh(part: Part) -> dict:
    verts, tris = part.shape.tessellate(TOLERANCE_MM, ANGULAR_TOLERANCE)
    return dict(
        n=part.name,
        g=part.group,
        e=part.explode,
        c=part.color,
        v=[round(c, 2) for vec in verts for c in vec.toTuple()],
        i=[idx for tri in tris for idx in tri],
    )


def clock_beside(cfg: BoardConfig, gantry: bool) -> tuple[list[Part], float]:
    base = gantry_base(cfg) if gantry else thin_base(cfg)
    x = base.x0_mm + base.width_mm + CLOCK_GAP_MM
    parts = [
        Part(p.name, p.shape.translate((x, CLOCK_Y_MM, 0)), p.color, p.group, p.explode)
        for p in clock.assembly(cfg)
    ]
    return parts, x + cfg.clock.body_mm[0] / 2.0


def scene(cfg: BoardConfig, gantry: bool) -> dict:
    g = geometry(cfg)
    base = gantry_base(cfg) if gantry else thin_base(cfg)
    parts = plateau.assembly(cfg, gantry=gantry)
    clock_parts, clock_cx = clock_beside(cfg, gantry)
    parts += clock_parts
    rows = [[layer.name, layer.thickness_mm] for layer in base.layers]
    size_rows = [
        ["largeur x profondeur", f"{base.width_mm:g} x {base.depth_mm:g} mm"],
        ["aire de jeu", f"{g.play_mm:g} x {g.play_mm:g} mm"],
    ]
    if gantry:
        size_rows += [
            ["ailes de capture", f"2 x {g.capture_band_mm:g} mm"],
            [
                "course X x Y",
                f"{g.play_mm + 2 * g.capture_band_mm:g} x {g.play_mm + g.y_margin_mm:g} mm",
            ],
        ]
    else:
        size_rows += [["bordure bois", f"{cfg.plateau.wood.border_mm:g} mm"]]
    return dict(
        parts=[mesh(p) for p in parts],
        layers=rows,
        size=size_rows,
        bbox=[base.x0_mm, base.y0_mm, base.width_mm, base.depth_mm, base.total_height_mm],
        clock=[clock_cx, CLOCK_Y_MM + cfg.clock.body_mm[1] / 2.0, cfg.clock.height_rear_mm / 2.0],
    )


def build(out: Path = DEFAULT_OUT) -> Path:
    cfg, _ = load()
    data = dict(
        fine=scene(cfg, gantry=False),
        chariot=scene(cfg, gantry=True),
        pitch=cfg.pitch.plateau_mm,
        explode=plateau.EXPLODE,
        groups=[
            ["base", "Base et coque", plateau.COL["shell"]],
            ["elec", "Électronique", plateau.COL["cell"]],
            ["chariot", "CoreXY", plateau.COL["rail"]],
            ["ailes", "Ailes de capture", plateau.COL["wing"]],
            ["quad", "Quadrants", plateau.COL["pcb"]],
            ["bois", "Contreplaqué", plateau.COL["light"]],
            ["pieces", "Pièces", plateau.COL["piece"]],
            ["horloge", "Horloge", "#2f3338"],
        ],
    )
    html = TEMPLATE.read_text(encoding="utf-8").replace(
        "__SCENE_JSON__", json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return out


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUT
    written = build(target)
    print(f"viewer written: {written} ({written.stat().st_size // 1024} kB)")
