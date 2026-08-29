"""Command-line entry point: python -m chessboard_calc report [--pitch 40|50|all]."""

from __future__ import annotations

import argparse
import sys

from .config import DEFAULT_CONFIG_PATH, load_config
from .report import full_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="chessboard_calc")
    sub = parser.add_subparsers(dest="command", required=True)
    rep = sub.add_parser("report", help="print the resolved parameter tables")
    rep.add_argument("--pitch", default="all", help="a pitch in mm, or 'all' (default)")
    rep.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="path to board.yaml")
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    if args.pitch == "all":
        pitches = list(cfg.pitch.candidates_mm)
    else:
        pitches = [float(args.pitch)]
    print(full_report(cfg, pitches))
    return 0


if __name__ == "__main__":
    sys.exit(main())
