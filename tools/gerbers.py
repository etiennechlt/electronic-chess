"""Fabrication files of a generated board, from the command line.

The generators leave the copper pours unfilled and `kicad-cli` plots a
board as saved: exported straight away, a ground plane comes out of
KiCad as an empty layer and the fabricator etches a board without its
plane. So the recipe of the DRC and plot scripts comes first: load the
board with KiCad's own `pcbnew` module, fill the pours, save a copy in
a scratch directory, then run `kicad-cli pcb export` on that copy.

The layer set is read off the board rather than spelled out per
project: the copper stack comes from the copper layer count, the paste
layers from the sides that actually carry SMD pads, and the masks, the
silkscreens and the board outline are always there. Run with the
Python that carries `pcbnew`, on Debian and Ubuntu the system
interpreter:

    /usr/bin/python3 tools/gerbers.py hardware/bench/bench.kicad_pcb

writes the plots and the Excellon drill files in
`hardware/bench/gerbers/` (ignored by git) and the archive to upload to
the fabricator in `hardware/bench/bench-gerbers.zip` (committed).

A board whose routing is unfinished is refused: the count of
unconnected pads must be zero, the same gate as `tools/drc.py`, so that
no archive of a board with open nets can be committed by accident.
`--force` exports one anyway, `--layers` overrides the layer set.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

# A fixed instant for the archive entries: the zip of an unchanged board
# stays the same but for the creation date KiCad writes in every plot.
ZIP_EPOCH = (1980, 1, 1, 0, 0, 0)


def copper_layers(board) -> list[str]:
    """The copper stack of a board, outside in, as kicad-cli names it."""
    count = board.GetCopperLayerCount()
    inner = [f"In{i}.Cu" for i in range(1, count - 1)]
    return ["F.Cu", *inner, "B.Cu"]


def paste_layers(board) -> list[str]:
    """The paste layers worth a stencil: the sides that carry SMD pads."""
    import pcbnew  # KiCad's own module, not on PyPI

    sides = {"F.Cu": "F.Paste", "B.Cu": "B.Paste"}
    used = set()
    for footprint in board.Footprints():
        for pad in footprint.Pads():
            if pad.GetAttribute() != pcbnew.PAD_ATTRIB_SMD:
                continue
            side = "B.Cu" if footprint.IsFlipped() else "F.Cu"
            used.add(sides[side])
    return [layer for layer in sides.values() if layer in used]


def board_layers(board) -> list[str]:
    """Every layer the fabricator needs, in the order of the stack."""
    return [
        *copper_layers(board),
        *paste_layers(board),
        "F.SilkS",
        "B.SilkS",
        "F.Mask",
        "B.Mask",
        "Edge.Cuts",
    ]


def load_filled(board_path: Path, scratch: Path):
    """The board with its pours filled, saved next to a copy of its project
    (the design rules and net classes the filler reads). Returns the board
    object and the path of the copy."""
    import pcbnew  # KiCad's own module, not on PyPI

    for ext in (".kicad_pro", ".kicad_prl"):
        side = board_path.with_suffix(ext)
        if side.exists():
            shutil.copy(side, scratch / side.name)
    board = pcbnew.LoadBoard(str(board_path))
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    filled = scratch / board_path.name
    board.Save(str(filled))
    return board, filled


def unconnected_count(board) -> int:
    """Pads the routing leaves open, the gate of `tools/drc.py`."""
    connectivity = board.GetConnectivity()
    connectivity.RecalculateRatsnest()
    return connectivity.GetUnconnectedCount(True)


def export(filled: Path, out_dir: Path, layers: list[str]) -> list[Path]:
    """Plots and drill files of a filled board, in `out_dir`."""
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.iterdir():
        if old.is_file():
            old.unlink()
    subprocess.run(
        [
            "kicad-cli", "pcb", "export", "gerbers",
            "--output", f"{out_dir}/",
            "--layers", ",".join(layers),
            str(filled),
        ],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        [
            "kicad-cli", "pcb", "export", "drill",
            "--output", f"{out_dir}/",
            "--format", "excellon",
            "--excellon-separate-th",
            str(filled),
        ],
        check=True,
        capture_output=True,
    )
    return sorted(p for p in out_dir.iterdir() if p.is_file())


def archive(files: list[Path], zip_path: Path) -> None:
    """The archive to upload, entries sorted and stamped alike."""
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in files:
            info = zipfile.ZipInfo(path.name, date_time=ZIP_EPOCH)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, path.read_bytes())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="fabrication files of a board with kicad-cli")
    parser.add_argument("boards", nargs="+", type=Path)
    parser.add_argument("--out", type=Path, default=None, help="directory of the archives")
    parser.add_argument("--layers", default=None, help="comma separated layer set, overrides")
    parser.add_argument("--force", action="store_true", help="export even with open nets")
    args = parser.parse_args(argv)
    try:
        import pcbnew  # noqa: F401
    except ImportError:
        print("pcbnew module not importable: run with KiCad's Python (/usr/bin/python3)")
        return 2
    if shutil.which("kicad-cli") is None:
        print("kicad-cli not found on PATH")
        return 2
    rc = 0
    for board_path in args.boards:
        with tempfile.TemporaryDirectory() as tmp:
            board, filled = load_filled(board_path, Path(tmp))
            open_pads = unconnected_count(board)
            if open_pads and not args.force:
                print(f"{board_path}: {open_pads} unconnected pad(s), routing unfinished; "
                      f"finish them or pass --force")
                rc = 1
                continue
            layers = args.layers.split(",") if args.layers else board_layers(board)
            out_dir = (args.out or board_path.parent) / "gerbers"
            files = export(filled, out_dir, layers)
        zip_path = (args.out or board_path.parent) / f"{board_path.stem}-gerbers.zip"
        archive(files, zip_path)
        warn = f", {open_pads} unconnected pad(s)" if open_pads else ""
        print(f"{board_path}: {len(layers)} layers, {len(files)} files{warn} -> {zip_path}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
