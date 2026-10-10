"""python -m serie signature OUT_DIR | python -m serie film PROJECT_DIR"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from chessboard_calc.config import DEFAULT_CONFIG_PATH, load_config

from .facts import ROOT, counters, facts, write_js
from .signature import write_all

IMAGES = ROOT / "docs" / "images"
COMMON = ROOT / "media" / "pitch" / "commun"


def prepare_film(cfg, project: Path) -> None:
    """Fill `PROJECT/assets/` with what the compositions read: facts.js,
    the notes, the scale and the thud, the repository renders, and a copy of
    media/pitch/commun (style, helpers, 3D scene kit, font, meshes) shared by
    every film. All of it is regenerated, none of it is committed."""
    assets = project / "assets"
    shutil.copytree(COMMON, assets / "commun", dirs_exist_ok=True)
    data = facts(cfg) | counters()
    write_js(assets / "facts.js", data)
    sounds = write_all(cfg, assets / "sons")
    renders = assets / "rendus"
    renders.mkdir(parents=True, exist_ok=True)
    copied = 0
    for image in sorted(IMAGES.glob("*.png")):
        shutil.copy2(image, renders / image.name)
        copied += 1
    print(
        f"{project}: facts.js ({data['tests']} tests, {data['components']} composants), "
        f"{len(sounds)} sons, {copied} rendus"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    sub = parser.add_subparsers(dest="command", required=True)
    sig = sub.add_parser("signature", help="one .wav per note and the rising scale")
    sig.add_argument("out", type=Path)
    film = sub.add_parser("film", help="facts, sounds and renders of a HyperFrames film")
    film.add_argument("project", type=Path)
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    if args.command == "signature":
        for path in write_all(cfg, args.out):
            print(path)
    else:
        prepare_film(cfg, args.project)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
