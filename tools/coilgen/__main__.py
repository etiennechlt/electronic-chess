"""CLI: python -m coilgen build [--out DIR] [--render PATH]."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from chessboard_calc.config import DEFAULT_CONFIG_PATH, load_config

from .board import build_coil_board, design_rules
from .project import project_json
from .render import render_board


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="coilgen")
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build", help="generate the mockup coil board")
    build.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    build.add_argument("--out", default="hardware/mockup-2x2/coil-board")
    build.add_argument("--render", default=None, help="optional PNG output path")
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    result = build_coil_board(cfg)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    pcb_path = out_dir / "coil-board.kicad_pcb"
    pcb_path.write_text(result.board.serialize(), encoding="utf-8")
    pro_path = out_dir / "coil-board.kicad_pro"
    pro_path.write_text(project_json("coil-board", design_rules(cfg, result)), encoding="utf-8")
    print(
        f"wrote {pcb_path} ({result.turns_per_layer} turns/layer, "
        f"track {result.track_width_mm:.2f} mm)"
    )
    print(f"wrote {pro_path} (open this one in KiCad)")
    if args.render:
        render_board(result, Path(args.render))
        print(f"wrote {args.render}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
