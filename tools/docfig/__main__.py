"""CLI: python -m docfig build [--out docs/images], python -m docfig pages
[--out docs/pages]."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from chessboard_calc.config import DEFAULT_CONFIG_PATH, load_config

from . import write_all, write_pages


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="docfig")
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build", help="write the documentation figures")
    build.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    build.add_argument("--out", default="docs/images")
    pages = sub.add_parser("pages", help="write the explanatory pages")
    pages.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    pages.add_argument("--out", default="docs/pages")
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    writer = write_all if args.command == "build" else write_pages
    for path in writer(cfg, Path(args.out)):
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
