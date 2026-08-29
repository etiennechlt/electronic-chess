"""Matplotlib rendering of the routed analog board, for review and docs."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .circuit import Circuit
from .pcb import BOARD_H, BOARD_W, PcbResult, _pad_instances


def render_pcb(result: PcbResult, circuit: Circuit, out_path: Path,
               dpi: int = 220, show_plane: bool = False) -> None:
    fig, ax = plt.subplots(figsize=(12.0, 12.0 * BOARD_H / BOARD_W))
    ax.set_facecolor("#101418")

    if show_plane:
        for poly in result.plane_polys:
            ax.add_patch(plt.Polygon(poly, closed=True, color="#1d3a52",
                                     zorder=1, linewidth=0))

    pads = _pad_instances(circuit, result.placements)
    for p in pads:
        color = "#d8d8a8" if p.tht else "#a07878"
        ax.add_patch(plt.Rectangle((p.x - p.w / 2, p.y - p.h / 2), p.w, p.h,
                                   color=color, zorder=4))

    scale = 12.0 * 72.0 * 0.9 / BOARD_W
    for _net, w, pts, layer in result.tracks:
        color, z = ("#c84040", 3) if layer == "F.Cu" else ("#4070c8", 2)
        xs = [a for a, _ in pts]
        ys = [b for _, b in pts]
        ax.plot(xs, ys, color=color, linewidth=w * scale / 2.2, alpha=0.9,
                zorder=z, solid_capstyle="round")
    for _net, x, y in result.vias:
        ax.add_patch(plt.Circle((x, y), 0.30, color="#e6e6e6", zorder=5))
        ax.add_patch(plt.Circle((x, y), 0.13, color="#101418", zorder=6))

    majors = {"J1", "J2", "J4", "J5", "U1", "U2", "U3", "U4", "U5", "U6", "U7",
              "L1", "JP1", "JP3", "Q1"}
    for ref, (x, y, _rot) in result.placements.items():
        if ref in majors:
            ax.annotate(ref, (x, y - 2.2), color="#9ab0c4", fontsize=8,
                        ha="center", zorder=7)

    ax.plot([0, BOARD_W, BOARD_W, 0, 0], [0, 0, BOARD_H, BOARD_H, 0],
            color="#e6c832", linewidth=1.4, zorder=8)
    ax.set_xlim(-3, BOARD_W + 3)
    ax.set_ylim(BOARD_H + 3, -3)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=dpi, facecolor="#101418")
    plt.close(fig)
