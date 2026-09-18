"""KiCad plot of a generated board's faces, from the command line.

The generators leave the copper pours unfilled and KiCad's `kicad-cli`
plots a board as saved, so the DRC script's recipe comes first: load the
board with KiCad's own `pcbnew` module, fill the pours, save a copy in a
scratch directory, then plot that copy with `kicad-cli pcb export svg`.
One SVG per face, board area only, no drawing sheet: the top face with
its silkscreen, the bottom face mirrored (as one looks at the real
board turned over). Run with the Python that carries `pcbnew`, on
Debian and Ubuntu the system interpreter:

    /usr/bin/python3 tools/plot.py hardware/bench/bench.kicad_pcb --out docs/images

writes `docs/images/bench-top.svg` and `docs/images/bench-bottom.svg`.
`--faces top,bottom,both` selects the views; `both` overlays the two
copper layers with the top silkscreen, the view of the board editor.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

FACES = {
    "top": ("F.Cu,F.SilkS,Edge.Cuts", False),
    "bottom": ("B.Cu,B.SilkS,Edge.Cuts", True),
    "both": ("B.Cu,F.Cu,F.SilkS,Edge.Cuts", False),
}


def fill_copy(board_path: Path, scratch: Path) -> Path:
    """The board with its pours filled, saved next to a copy of its project
    (the design rules and net classes the filler reads)."""
    import pcbnew  # KiCad's own module, not on PyPI

    for ext in (".kicad_pro", ".kicad_prl"):
        side = board_path.with_suffix(ext)
        if side.exists():
            shutil.copy(side, scratch / side.name)
    board = pcbnew.LoadBoard(str(board_path))
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    filled = scratch / board_path.name
    board.Save(str(filled))
    return filled


def plot_face(filled: Path, out: Path, face: str) -> None:
    layers, mirror = FACES[face]
    cmd = [
        "kicad-cli",
        "pcb",
        "export",
        "svg",
        "--output",
        str(out),
        "--layers",
        layers,
        "--page-size-mode",
        "2",
        "--exclude-drawing-sheet",
    ]
    if mirror:
        cmd.append("--mirror")
    cmd.append(str(filled))
    subprocess.run(cmd, check=True, capture_output=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="plot the faces of a board with kicad-cli")
    parser.add_argument("boards", nargs="+", type=Path)
    parser.add_argument("--out", type=Path, default=None, help="directory of the SVG files")
    parser.add_argument("--faces", default="top,bottom", help="comma separated: top, bottom, both")
    args = parser.parse_args(argv)
    faces = [f.strip() for f in args.faces.split(",") if f.strip()]
    unknown = [f for f in faces if f not in FACES]
    if unknown:
        print(f"unknown face(s): {', '.join(unknown)}; choose among {', '.join(FACES)}")
        return 2
    try:
        import pcbnew  # noqa: F401
    except ImportError:
        print("pcbnew module not importable: run with KiCad's Python (/usr/bin/python3)")
        return 2
    if shutil.which("kicad-cli") is None:
        print("kicad-cli not found on PATH")
        return 2
    for board in args.boards:
        out_dir = args.out or board.parent
        out_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory() as tmp:
            filled = fill_copy(board, Path(tmp))
            for face in faces:
                out = out_dir / f"{board.stem}-{face}.svg"
                plot_face(filled, out, face)
                print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
