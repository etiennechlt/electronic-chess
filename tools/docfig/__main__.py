"""CLI: python -m docfig build [--out docs/images]."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from chessboard_calc.config import DEFAULT_CONFIG_PATH, load_config

from . import write_all


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="docfig")
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build", help="write the documentation figures")
    build.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    build.add_argument("--out", default="docs/images")
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    for path in write_all(cfg, Path(args.out)):
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
