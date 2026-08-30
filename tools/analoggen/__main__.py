"""CLI: python -m analoggen build [--out DIR] [--render PATH]."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from chessboard_calc.config import DEFAULT_CONFIG_PATH, load_config

from .bom import bom_csv, jlc_bom_csv, jlc_cpl_csv
from .circuit import build_circuit
from .pcb import build_pcb
from .render import render_pcb
from .schematic import emit_schematic
from .spice import chain_netlist


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="analoggen")
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build", help="generate the analog board project")
    build.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    build.add_argument("--out", default="hardware/mockup-2x2/analog-board")
    build.add_argument("--render", default=None, help="optional PNG output path")
    build.add_argument("--skip-pcb", action="store_true",
                       help="only schematic, BOM and SPICE outputs")
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    circuit, chain = build_circuit(cfg)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    (out / "analog-board.kicad_sch").write_text(
        emit_schematic(circuit, "Damier LC, maquette 2x2, carte analogique"),
        encoding="utf-8")
    (out / "bom.csv").write_text(bom_csv(circuit), encoding="utf-8")
    (out / "jlc-bom.csv").write_text(jlc_bom_csv(circuit), encoding="utf-8")
    (out / "chain-spice.cir").write_text(chain_netlist(chain), encoding="utf-8")
    print(f"schematic, BOM and SPICE written to {out} "
          f"(chain gain {chain.total_gain:.0f})")

    if not args.skip_pcb:
        result = build_pcb(cfg, circuit)
        (out / "analog-board.kicad_pcb").write_text(
            result.board.serialize(), encoding="utf-8")
        (out / "jlc-cpl.csv").write_text(
            jlc_cpl_csv(circuit, result.placements), encoding="utf-8")
        status = (f"routed: {len(result.tracks)} tracks, {len(result.vias)} vias, "
                  f"open {len(result.open_nets)}, drc {len(result.drc_errors)}")
        print(status)
        if result.open_nets:
            print("  finish list (airwires to close in KiCad):")
            for entry in result.open_nets:
                print(f"    - {entry}")
        if result.drc_errors:
            print("  DRC:", "; ".join(result.drc_errors[:6]))
        if args.render:
            render_pcb(result, circuit, Path(args.render))
            print(f"wrote {args.render}")
        # Leftover airwires are a documented state (see the board README);
        # only a clearance violation is a build failure.
        if result.drc_errors:
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
