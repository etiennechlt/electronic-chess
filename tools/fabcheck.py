"""Order readiness of every generated board, in one command.

The audit that decides whether a board can be sent to a fabricator was
done by hand once (see `docs/notes/23-commande-jlcpcb.md`) and found
three defects that no other check would have reported: an archive older
than the board it claims to plot, an assembly BOM carrying a third of
the components, and a via rule nobody had confronted with the
manufacturer's capabilities. This tool is that audit, repeatable:

    python3 tools/fabcheck.py                     # every board
    python3 tools/fabcheck.py hardware/bench      # one of them

It reads the board files and the generated CSVs only, so it runs
anywhere (no KiCad, no network). What it cannot do is replace the DRC:
run `tools/drc.py` with KiCad's Python for that, and `tools/gerbers.py`
to write an archive, which refuses a board whose routing is open.

Exit code is non zero when a board ships an archive whose digest no
longer matches what is committed, which is the one defect here that
makes a fabrication order wrong rather than merely incomplete.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Footprints that are copper, not components: nothing to source, nothing
# to place, and a line about them in an assembly report is noise.
NOT_A_PART = ("TestPoint", "MountingHole", "NetTie", "COIL_TIE", "Fiducial")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def refs(cell: str) -> set[str]:
    """The designators of one BOM or CPL cell, commas or spaces."""
    return {r for r in re.split(r"[,\s]+", cell or "") if r}


@dataclass
class BoardAudit:
    directory: Path
    name: str
    layers: int = 0
    width_mm: float = 0.0
    height_mm: float = 0.0
    tracks: int = 0
    vias: int = 0
    min_track_mm: float = 0.0
    min_via: tuple[float, float] = (0.0, 0.0)
    parts: int = 0
    assembled: int = 0
    no_lcsc: list[str] = field(default_factory=list)
    pads_only: int = 0
    cpl_orphans: list[str] = field(default_factory=list)
    archive: Path | None = None
    digest: str = "none"  # none, ok, stale, incomplete

    @property
    def ready_bare(self) -> bool:
        return self.archive is not None and self.digest == "ok"

    @property
    def ready_assembled(self) -> bool:
        return self.ready_bare and not self.no_lcsc and not self.cpl_orphans


def read_board(path: Path) -> tuple[int, float, float, int, int, float, tuple[float, float]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    setup = text.split("(setup", 1)[0]
    layers = len(re.findall(r'"(?:F|B|In\d+)\.Cu"', setup))
    xs, ys = [], []
    for m in re.finditer(
        r"\(gr_(?:line|rect) \(start ([\d.-]+) ([\d.-]+)\) \(end ([\d.-]+) ([\d.-]+)\)(.{0,140})",
        text,
        re.S,
    ):
        if "Edge.Cuts" not in m.group(5):
            continue
        xs += [float(m.group(1)), float(m.group(3))]
        ys += [float(m.group(2)), float(m.group(4))]
    widths = [
        float(w)
        for w in re.findall(
            r"\(segment \(start [\d.-]+ [\d.-]+\) \(end [\d.-]+ [\d.-]+\) \(width ([\d.]+)\)", text
        )
    ]
    vias = [
        (float(a), float(b))
        for a, b in re.findall(
            r"\(via \(at [\d.-]+ [\d.-]+\) \(size ([\d.]+)\) \(drill ([\d.]+)\)", text
        )
    ]
    return (
        layers,
        max(xs) - min(xs) if xs else 0.0,
        max(ys) - min(ys) if ys else 0.0,
        len(widths),
        len(vias),
        min(widths) if widths else 0.0,
        min(vias) if vias else (0.0, 0.0),
    )


def audit(directory: Path) -> BoardAudit | None:
    boards = sorted(directory.glob("*.kicad_pcb"))
    if not boards:
        return None
    board = boards[0]
    out = BoardAudit(directory=directory, name=board.stem)
    (
        out.layers,
        out.width_mm,
        out.height_mm,
        out.tracks,
        out.vias,
        out.min_track_mm,
        out.min_via,
    ) = read_board(board)

    full, dnp = set(), set()
    bom = directory / "bom.csv"
    if bom.is_file():
        for row in csv.DictReader(bom.open(encoding="utf-8")):
            here = refs(row.get("References", ""))
            footprint = row.get("Footprint", "")
            if footprint.startswith(NOT_A_PART):
                out.pads_only += len(here)
                continue
            full |= here
            if (row.get("DNP") or "").strip().lower() in ("1", "yes", "true", "x", "oui"):
                dnp |= here
            elif not (row.get("LCSC") or "").strip():
                out.no_lcsc.append(f"{len(here)} x {row.get('Value', '?')} {footprint}")
    out.parts = len(full - dnp)

    assembled: set[str] = set()
    jlc = directory / "jlc-bom.csv"
    if jlc.is_file():
        for row in csv.DictReader(jlc.open(encoding="utf-8")):
            assembled |= refs(row.get("Designator", ""))
    out.assembled = len(assembled)

    cpl = directory / "jlc-cpl.csv"
    if cpl.is_file():
        for row in csv.DictReader(cpl.open(encoding="utf-8")):
            ref = (row.get("Designator") or "").strip()
            if ref and ref not in assembled:
                out.cpl_orphans.append(ref)

    archives = sorted(directory.glob("*-gerbers.zip"))
    if archives:
        out.archive = archives[0]
        recorded = {}
        digest = out.archive.with_suffix(".sha256")
        if digest.is_file():
            for line in digest.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    value, name = line.split()
                    recorded[name] = value
        if not recorded:
            out.digest = "none"
        elif set(recorded) != {board.name, out.archive.name}:
            out.digest = "incomplete"
        elif all(sha256(directory / n) == v for n, v in recorded.items()):
            out.digest = "ok"
        else:
            out.digest = "stale"
    return out


def report(audits: list[BoardAudit]) -> int:
    bad = 0
    for a in audits:
        verdict = (
            "assembly ready"
            if a.ready_assembled
            else "bare boards ready"
            if a.ready_bare
            else "not ready"
        )
        print(
            f"{a.name:14s} {a.width_mm:5.0f} x {a.height_mm:3.0f} mm  {a.layers} layers  "
            f"{a.tracks:5d} tracks {a.vias:4d} vias  track >= {a.min_track_mm:.2f} mm  "
            f"via {a.min_via[0]:.2f}/{a.min_via[1]:.2f}  -> {verdict}"
        )
        if a.archive is None:
            print("    archive: none (tools/gerbers.py refuses a board with open routing)")
        elif a.digest == "ok":
            print(f"    archive: {a.archive.name}, digest matches the committed board")
        else:
            bad += 1
            print(f"    archive: {a.archive.name}, digest {a.digest.upper()}: do not fabricate")
        print(
            f"    assembly: {a.assembled} of {a.parts} parts in jlc-bom.csv "
            f"({a.pads_only} pads and ties are not parts)",
            end="",
        )
        if a.cpl_orphans:
            print(f", {len(a.cpl_orphans)} CPL designators absent from it: {a.cpl_orphans[:6]}")
        else:
            print(", CPL and BOM agree")
        for line in a.no_lcsc[:6]:
            print(f"      no LCSC code: {line}")
        if len(a.no_lcsc) > 6:
            print(f"      no LCSC code: and {len(a.no_lcsc) - 6} more lines")
    return 1 if bad else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("boards", nargs="*", type=Path, help="board directories (default: all)")
    args = parser.parse_args(argv)
    directories = args.boards or sorted(
        {p.parent for p in (ROOT / "hardware").rglob("*.kicad_pcb")}
    )
    audits = [a for a in (audit(Path(d)) for d in directories) if a is not None]
    if not audits:
        print("no board found")
        return 2
    return report(audits)


if __name__ == "__main__":
    sys.exit(main())
