"""CLI: python -m quadgen build [--out DIR] [--render PATH]."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from coilgen.project import project_json
from coilgen.render import render_board

from chessboard_calc.config import DEFAULT_CONFIG_PATH, load_config

from .board import build_quadrant, design_rules, summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="quadgen")
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build", help="generate the quadrant board")
    build.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    build.add_argument("--out", default="hardware/quadrant")
    build.add_argument("--render", default=None, help="optional PNG output path")
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    result = build_quadrant(cfg)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "quadrant.kicad_pcb").write_text(result.board.serialize(), encoding="utf-8")
    (out / "quadrant.kicad_pro").write_text(
        project_json("quadrant", design_rules(cfg, result)), encoding="utf-8"
    )
    print(f"wrote {out / 'quadrant.kicad_pcb'}: {summary(result)}")
    for line in result.open_routes:
        print(f"  open: {line}")
    for line in result.clearance_errors[:20]:
        print(f"  clearance: {line}")
    if args.render:
        render_board(result, Path(args.render))
        print(f"wrote {args.render}")
    return 1 if (result.open_routes or result.clearance_errors) else 0


if __name__ == "__main__":
    sys.exit(main())
