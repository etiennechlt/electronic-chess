"""Build every mockup mechanical part: STL + STEP into exports/.

Usage, from the repository root with the project venv:
    python mechanical/build_all.py [--formats stl,step]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import cadquery as cq
from cadquery import exporters
from common import load, puck_dims
from parts import (
    magnet_bracket_base,
    magnet_cup,
    piece_puck,
    winding_jig,
    winding_jig_washer,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--formats", default="stl,step")
    parser.add_argument("--out", default=str(Path(__file__).parent / "exports"))
    args = parser.parse_args()
    formats = args.formats.split(",")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    cfg, pitch = load()

    parts: dict[str, cq.Workplane] = {}
    for tp in cfg.mockup.test_pieces:
        dims = puck_dims(cfg, tp.piece, pitch)
        parts[f"puck-{tp.piece.value}-{tp.color.value}"] = piece_puck(dims)

    # One winding jig per distinct coil envelope among the test pieces.
    seen = set()
    for tp in cfg.mockup.test_pieces:
        dims = puck_dims(cfg, tp.piece, pitch)
        key = round(dims.coil_d, 2)
        if key in seen:
            continue
        seen.add(key)
        d_in = cfg.resonator.coil.inner_ratio * dims.coil_d
        parts[f"jig-core-d{key:g}"] = winding_jig(dims.coil_d, d_in, dims.coil_h)
        parts[f"jig-washer-d{key:g}"] = winding_jig_washer(dims.coil_d, d_in)

    mm = cfg.mockup.coil_board.magnet_mount
    parts["magnet-bracket-base"] = magnet_bracket_base(
        mm.hole_spacing_mm, cfg.carriage.magnet.d_mm)
    parts["magnet-cup"] = magnet_cup(cfg.carriage.magnet.d_mm,
                                     cfg.carriage.magnet.h_mm)

    for name, part in parts.items():
        if "stl" in formats:
            exporters.export(part, str(out / f"{name}.stl"))
        if "step" in formats:
            exporters.export(part, str(out / f"{name}.step"))
        print(f"built {name}")
    print(f"{len(parts)} parts in {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
