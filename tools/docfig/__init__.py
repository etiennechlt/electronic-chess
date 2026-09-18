"""Documentation figures and pages generated from config/board.yaml.

`python -m docfig build` writes the SVG files of `docs/images/` that the
notes 18 and 19 embed; the same functions return inline fragments for the
pages, and `python -m docfig pages` writes those to `docs/pages/`: one
self-contained HTML file per note, for a reader who opens a browser
rather than the repository.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from chessboard_calc.config import BoardConfig

from .bench import fig_bench_nucleo, fig_brain_blocks, fig_scan_cycle
from .common import standalone
from .page_bench import bench_page
from .page_q import q_page
from .page_tuto import tuto_page
from .q import (
    fig_q_chain,
    fig_q_plan,
    fig_q_ringdown,
    fig_q_stack,
    fig_q_timeline,
    fig_q_vs_frequency,
    fig_q_width,
)
from .tuto import fig_bench_inventory, fig_bench_tests, fig_puck_making, fig_shield_assembly

FIGURES: dict[str, Callable[[BoardConfig], str]] = {
    "q-ringdown.svg": fig_q_ringdown,
    "q-largeur.svg": fig_q_width,
    "q-plan.svg": fig_q_plan,
    "q-frequence.svg": fig_q_vs_frequency,
    "q-coupe.svg": fig_q_stack,
    "q-mesure.svg": fig_q_timeline,
    "q-chaine.svg": fig_q_chain,
    "cerveau-blocs.svg": fig_brain_blocks,
    "cerveau-cycle.svg": fig_scan_cycle,
    "banc-nucleo.svg": fig_bench_nucleo,
    "tuto-inventaire.svg": fig_bench_inventory,
    "tuto-shield.svg": fig_shield_assembly,
    "tuto-puck.svg": fig_puck_making,
    "tuto-tests.svg": fig_bench_tests,
}


PAGES: dict[str, Callable[[BoardConfig], str]] = {
    "facteur-q.html": q_page,
    "cerveau-banc.html": bench_page,
    "tuto-banc.html": tuto_page,
}


def write_all(cfg: BoardConfig, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for name, fn in FIGURES.items():
        path = out_dir / name
        path.write_text(standalone(fn(cfg)) + "\n", encoding="utf-8")
        written.append(path)
    return written


def write_pages(cfg: BoardConfig, out_dir: Path) -> list[Path]:
    """The explanatory pages, figures embedded, one file each."""
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for name, fn in PAGES.items():
        path = out_dir / name
        path.write_text(fn(cfg), encoding="utf-8")
        written.append(path)
    return written
