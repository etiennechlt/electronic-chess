"""CLI: python -m quadgen build [--reduced] [--out DIR] [--render PATH] [--no-strip]."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from analoggen.bom import bom_csv, jlc_bom_csv, jlc_cpl_csv
from analoggen.spice import chain_netlist
from coilgen.project import project_json
from coilgen.render import render_board

from chessboard_calc.config import DEFAULT_CONFIG_PATH, load_config

from .board import build_quadrant, design_rules, summary
from .schematic import quadrant_schematic
from .variant import project_name, reduced_config


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="quadgen")
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build", help="generate the quadrant board")
    build.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    build.add_argument(
        "--reduced",
        action="store_true",
        help="the 2 x 2 development quadrant (plateau.quadrant.reduced)",
    )
    build.add_argument("--out", default=None, help="output directory (hardware/<project>)")
    build.add_argument("--render", default=None, help="optional PNG output path")
    build.add_argument(
        "--no-strip", action="store_true", help="place the front end but do not route it"
    )
    build.add_argument(
        "--resume", default=None, help="a QUADGEN_DUMP file: finishing pass and checks only"
    )
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    if args.reduced:
        cfg = reduced_config(cfg)
    name = project_name(cfg, args.reduced)
    out = Path(args.out or f"hardware/{name}")
    out.mkdir(parents=True, exist_ok=True)
    if args.resume:
        from .board import Builder

        result = Builder.resume(args.resume)
    else:
        result = build_quadrant(cfg, strip=not args.no_strip)
    (out / f"{name}.kicad_pcb").write_text(result.board.serialize(), encoding="utf-8")
    sch = quadrant_schematic(cfg, result.circuit, result.chain, name)
    sch.verify(result.circuit)
    for filename, text in sch.emit().items():
        (out / filename).write_text(text, encoding="utf-8")
    (out / f"{name}.kicad_pro").write_text(
        project_json(name, design_rules(cfg, result), root_sheet_uuid=sch.root.uuid),
        encoding="utf-8",
    )
    (out / "bom.csv").write_text(bom_csv(result.circuit), encoding="utf-8")
    (out / "jlc-bom.csv").write_text(jlc_bom_csv(result.circuit), encoding="utf-8")
    (out / "jlc-cpl.csv").write_text(
        jlc_cpl_csv(result.circuit, result.placements, board_h_mm=result.layout.board_h),
        encoding="utf-8",
    )
    (out / "chain-spice.cir").write_text(chain_netlist(result.chain), encoding="utf-8")
    print(f"wrote {out / f'{name}.kicad_pcb'}: {summary(result)}")
    for line in result.open_routes:
        print(f"  open: {line}")
    for line in result.open_nets:
        print(f"  open net: {line}")
    for line in result.clearance_errors[:20]:
        print(f"  clearance: {line}")
    if args.render:
        render_board(result, Path(args.render))
        print(f"wrote {args.render}")
    return 1 if (result.open_routes or result.open_nets or result.clearance_errors) else 0


if __name__ == "__main__":
    sys.exit(main())
