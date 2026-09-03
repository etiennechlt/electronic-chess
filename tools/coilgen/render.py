"""Matplotlib rendering of the generated coil board, for review and docs."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection

from .board import BuildResult

LAYER_STYLE = {
    "F.Cu": ("#c83232", 1.0, 3),
    "In1.Cu": ("#c8a000", 0.85, 2),
    "In2.Cu": ("#00a0a0", 0.85, 1),
    "B.Cu": ("#3264c8", 1.0, 0),
}


def render_board(result: BuildResult, out_path: Path, dpi: int = 220) -> None:
    w, h = result.outline_mm
    fig, ax = plt.subplots(figsize=(7.2, 7.2))
    ax.set_facecolor("#101418")

    def width_pt(width_mm: float) -> float:
        # figure is 7.2 in for ~w mm plus margins; convert mm to points.
        return width_mm * (7.2 * 72.0 * 0.86) / w

    for layer, (color, alpha, z) in LAYER_STYLE.items():
        spiral_segs, route_segs = [], []
        for coil in result.coils:
            for path in coil.paths:
                if path.layer == layer:
                    pts = path.points
                    spiral_segs.extend(
                        [
                            ((pts[i, 0], pts[i, 1]), (pts[i + 1, 0], pts[i + 1, 1]))
                            for i in range(len(pts) - 1)
                        ]
                    )
            for _label, rlayer, pts in coil.routes:
                if rlayer == layer:
                    route_segs.extend([(pts[i], pts[i + 1]) for i in range(len(pts) - 1)])
        for segs, w_mm in ((spiral_segs, result.track_width_mm), (route_segs, 0.5)):
            if segs:
                ax.add_collection(
                    LineCollection(
                        segs,
                        colors=color,
                        alpha=alpha,
                        zorder=z,
                        linewidths=width_pt(w_mm),
                        capstyle="round",
                    )
                )

    for coil in result.coils:
        for vx, vy in coil.vias:
            ax.add_patch(plt.Circle((vx, vy), 0.45, color="#e6e6e6", zorder=5))
            ax.add_patch(plt.Circle((vx, vy), 0.18, color="#101418", zorder=6))
        ax.annotate(
            coil.name, coil.center, color="#8aa0b4", ha="center", va="center", fontsize=13, zorder=7
        )
    for px in result.pad_xs:
        ax.add_patch(plt.Circle((px, 2.5), 0.85, color="#d0d0a0", zorder=5))
        ax.add_patch(plt.Circle((px, 2.5), 0.5, color="#101418", zorder=6))

    for layer, (color, alpha, z) in LAYER_STYLE.items():
        segs = [
            (pts[i], pts[i + 1])
            for _n, llayer, _w, pts in result.led_tracks
            if llayer == layer
            for i in range(len(pts) - 1)
        ]
        if segs:
            ax.add_collection(
                LineCollection(
                    segs,
                    colors=color,
                    alpha=alpha,
                    zorder=z,
                    linewidths=width_pt(0.5),
                    capstyle="round",
                )
            )
    for vx, vy in result.led_vias:
        ax.add_patch(plt.Circle((vx, vy), 0.4, color="#e6e6e6", zorder=5))
        ax.add_patch(plt.Circle((vx, vy), 0.18, color="#101418", zorder=6))
    for ref, (lx, ly) in result.leds:
        ax.add_patch(
            plt.Rectangle(
                (lx - 2.5, ly - 2.5), 5.0, 5.0, facecolor="#e8e8ee", edgecolor="#8aa0b4", zorder=8
            )
        )
        ax.annotate(ref, (lx, ly), color="#101418", ha="center", va="center", fontsize=6, zorder=9)
    for hx, hy, hd in result.holes:
        ax.add_patch(
            plt.Circle((hx, hy), hd / 2.0, fill=False, color="#8aa0b4", zorder=5, linewidth=1.0)
        )

    ax.plot([0, w, w, 0, 0], [0, 0, h, h, 0], color="#e6c832", linewidth=1.4, zorder=8)
    ax.set_xlim(-4, w + 4)
    ax.set_ylim(h + 4, -4)  # KiCad orientation: y down
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=dpi, facecolor="#101418")
    plt.close(fig)
