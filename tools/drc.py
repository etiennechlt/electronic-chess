"""KiCad DRC of a generated board from the command line.

KiCad 7 ships no `kicad-cli pcb drc`; its `pcbnew` Python module does the
same job: load the board with its project (design rules, net classes),
fill the copper pours (the generators leave them unfilled), run the
rule checker and write the report KiCad would. Run with the Python that
carries the module, on Debian and Ubuntu the system interpreter:

    /usr/bin/python3 tools/drc.py hardware/brain/brain.kicad_pcb [more boards]

Prints, per board, the count of every violation type and the first
lines of each, and exits non zero when a board has any error-severity
violation or unconnected item. Warnings (silkscreen, library paths of
the footprints) are listed but never fail. `--all` prints every
violation, `--report DIR` keeps the raw reports.
"""

from __future__ import annotations

import argparse
import collections
import re
import sys
from pathlib import Path

WARNING_TYPES = {
    "lib_footprint_issues",
    "silk_overlap",
    "silk_over_copper",
    "silk_edge_clearance",
    "holes_co_located",
    "via_dangling",
    "track_dangling",
}

VIOLATION = re.compile(r"^\[(\w+)\]: (.*)\n((?:^    .*\n?)*)", re.M)


def run_drc(board_path: Path, report_path: Path) -> str:
    import pcbnew  # KiCad's own module, not on PyPI

    board = pcbnew.LoadBoard(str(board_path))
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    pcbnew.WriteDRCReport(board, str(report_path), pcbnew.EDA_UNITS_MILLIMETRES, True)
    return report_path.read_text(encoding="utf-8", errors="replace")


def summarize(report: str, show_all: bool = False, per_type: int = 3) -> tuple[str, int]:
    """Human summary of a KiCad DRC report and the number of failing items."""
    counts: collections.Counter[str] = collections.Counter()
    severity: dict[str, str] = {}
    samples: dict[str, list[str]] = collections.defaultdict(list)
    for m in VIOLATION.finditer(report):
        kind, title, body = m.group(1), m.group(2), m.group(3)
        counts[kind] += 1
        sev = re.search(r"Severity: (\w+)", body)
        severity[kind] = sev.group(1) if sev else "error"
        items = [ln.strip() for ln in body.splitlines() if ln.strip().startswith("@")]
        if show_all or len(samples[kind]) < per_type:
            samples[kind].append(f"{title} | " + " | ".join(items))
    unconnected = re.search(r"\*\* Found (\d+) unconnected pads \*\*", report)
    n_unconnected = int(unconnected.group(1)) if unconnected else 0
    lines = []
    failing = 0
    for kind, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        sev = severity[kind]
        hard = sev == "error" and kind not in WARNING_TYPES
        if hard:
            failing += n
        lines.append(f"  {n:5d}  {kind:<24} {sev}{'' if hard else ' (ignored)'}")
        for s in samples[kind]:
            lines.append(f"           {s[:160]}")
    lines.append(f"  unconnected items: {n_unconnected}")
    return "\n".join(lines), failing


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="KiCad DRC through pcbnew")
    parser.add_argument("boards", nargs="+", type=Path)
    parser.add_argument("--report", type=Path, default=None, help="directory for the raw reports")
    parser.add_argument("--all", action="store_true", help="print every violation")
    args = parser.parse_args(argv)
    try:
        import pcbnew  # noqa: F401
    except ImportError:
        print("pcbnew module not importable: run with KiCad's Python (/usr/bin/python3)")
        return 2
    rc = 0
    for board in args.boards:
        out_dir = args.report or board.parent
        report_path = out_dir / (board.stem + "-drc.rpt")
        report = run_drc(board, report_path)
        text, failing = summarize(report, show_all=args.all)
        n = re.search(r"\*\* Found (\d+) DRC violations \*\*", report)
        print(f"{board}: {n.group(1) if n else '?'} violations, {failing} failing")
        print(text)
        if args.report is None:
            report_path.unlink(missing_ok=True)
        if failing or "unconnected items: 0" not in text:
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
