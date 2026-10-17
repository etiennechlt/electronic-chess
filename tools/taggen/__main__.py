"""CLI: python -m taggen build [--out hardware/tag-demo] [--render PATH]."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from coilgen.project import project_json

from chessboard_calc.config import DEFAULT_CONFIG_PATH, load_config

from .panel import NAME, bom_csv, build_tag_panel, design_rules, jlc_bom_csv, jlc_cpl_csv


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="taggen")
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build", help="generate the tag panel")
    build.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    build.add_argument("--out", default=f"hardware/{NAME}")
    build.add_argument("--render", default=None, help="optional PNG output path")
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    result = build_tag_panel(cfg)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{NAME}.kicad_pcb").write_text(result.board.serialize(), encoding="utf-8")
    (out / f"{NAME}.kicad_pro").write_text(project_json(NAME, design_rules()), encoding="utf-8")
    (out / "bom.csv").write_text(bom_csv(result), encoding="utf-8")
    (out / "jlc-bom.csv").write_text(jlc_bom_csv(result), encoding="utf-8")
    (out / "jlc-cpl.csv").write_text(jlc_cpl_csv(result), encoding="utf-8")
    print(
        f"wrote {out / (NAME + '.kicad_pcb')}: {len(result.tags)} tags, "
        f"{result.panel_mm[0]:g} x {result.panel_mm[1]:g} mm, {len(result.bites)} mouse bites"
    )
    if args.render:
        from .render import render_panel

        render_panel(result, Path(args.render))
        print(f"wrote {args.render}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
