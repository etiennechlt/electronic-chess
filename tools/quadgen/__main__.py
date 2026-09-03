"""CLI: python -m quadgen build [--out DIR] [--render PATH]."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from analoggen.bom import bom_csv, jlc_bom_csv, jlc_cpl_csv
from analoggen.schematic import emit_schematic
from analoggen.spice import chain_netlist
from coilgen.project import project_json, schematic_root_uuid
from coilgen.render import render_board

from chessboard_calc.config import DEFAULT_CONFIG_PATH, load_config

from .board import build_quadrant, design_rules, summary
from .circuit import schematic_groups


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
    sch = emit_schematic(
        result.circuit,
        "Damier LC, quadrant 4x4",
        groups=schematic_groups(cfg),
        project="quadrant",
        paper="A0",
    )
    (out / "quadrant.kicad_sch").write_text(sch, encoding="utf-8")
    (out / "quadrant.kicad_pro").write_text(
        project_json(
            "quadrant", design_rules(cfg, result), root_sheet_uuid=schematic_root_uuid(sch)
        ),
        encoding="utf-8",
    )
    (out / "bom.csv").write_text(bom_csv(result.circuit), encoding="utf-8")
    (out / "jlc-bom.csv").write_text(jlc_bom_csv(result.circuit), encoding="utf-8")
    (out / "jlc-cpl.csv").write_text(
        jlc_cpl_csv(result.circuit, result.placements, board_h_mm=result.layout.board_h),
        encoding="utf-8",
    )
    (out / "chain-spice.cir").write_text(chain_netlist(result.chain), encoding="utf-8")
    print(f"wrote {out / 'quadrant.kicad_pcb'}: {summary(result)}")
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
