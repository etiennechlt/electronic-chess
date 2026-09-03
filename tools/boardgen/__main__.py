"""CLI: python -m boardgen build <brain|power|motion|clock> [--out DIR] [--render PATH]."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from analoggen.bom import bom_csv, jlc_bom_csv, jlc_cpl_csv
from analoggen.schematic import emit_schematic
from coilgen.project import project_json, schematic_root_uuid

from chessboard_calc.config import DEFAULT_CONFIG_PATH, load_config

from .core import Result, design_rules, summary
from .render import render_board

BOARDS = {}


def _register():
    from . import brain

    BOARDS["brain"] = (brain.build_brain, brain.SPEC, brain.schematic_groups)
    try:
        from . import clock, motion, power

        BOARDS["power"] = (power.build_power, power.SPEC, power.schematic_groups)
        BOARDS["motion"] = (motion.build_motion, motion.SPEC, motion.schematic_groups)
        BOARDS["clock"] = (clock.build_clock, clock.SPEC, clock.schematic_groups)
    except ImportError:
        pass


def write_outputs(result: Result, groups, out: Path, render: str | None) -> None:
    name = result.spec.name
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{name}.kicad_pcb").write_text(result.board.serialize(), encoding="utf-8")
    sch = emit_schematic(result.circuit, result.spec.title, groups=groups, project=name, paper="A1")
    (out / f"{name}.kicad_sch").write_text(sch, encoding="utf-8")
    (out / f"{name}.kicad_pro").write_text(
        project_json(name, design_rules(result.spec), root_sheet_uuid=schematic_root_uuid(sch)),
        encoding="utf-8",
    )
    (out / "bom.csv").write_text(bom_csv(result.circuit), encoding="utf-8")
    (out / "jlc-bom.csv").write_text(jlc_bom_csv(result.circuit), encoding="utf-8")
    (out / "jlc-cpl.csv").write_text(
        jlc_cpl_csv(result.circuit, result.placements, board_h_mm=result.spec.height),
        encoding="utf-8",
    )
    print(f"wrote {out / (name + '.kicad_pcb')}: {summary(result)}")
    for line in result.open_nets[:40]:
        print(f"  open net: {line}")
    for line in result.clearance_errors[:20]:
        print(f"  clearance: {line}")
    if render:
        render_board(result, Path(render))
        print(f"wrote {render}")


def main(argv: list[str] | None = None) -> int:
    _register()
    parser = argparse.ArgumentParser(prog="boardgen")
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build", help="generate one board project")
    build.add_argument("board", choices=sorted(BOARDS))
    build.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    build.add_argument("--out", default=None)
    build.add_argument("--render", default=None)
    args = parser.parse_args(argv)
    cfg = load_config(args.config)
    fn, spec, groups_fn = BOARDS[args.board]
    result = fn(cfg)
    out = Path(args.out) if args.out else Path("hardware") / args.board
    write_outputs(result, groups_fn(), out, args.render)
    return 1 if (result.open_nets or result.clearance_errors) else 0


if __name__ == "__main__":
    sys.exit(main())
