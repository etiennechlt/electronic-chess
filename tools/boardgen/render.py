"""Matplotlib rendering of a generic board: pads, tracks per layer, vias,
outline and references, for the documentation and for review."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection

from .core import Result

LAYER_STYLE = {
    "F.Cu": ("#c83232", 1.0, 3),
    "In1.Cu": ("#c8a000", 0.7, 2),
    "In2.Cu": ("#00a0a0", 0.7, 1),
    "B.Cu": ("#3264c8", 1.0, 0),
}


def render_board(res: Result, out_path: Path, dpi: int = 200) -> None:
    w, h = res.spec.width, res.spec.height
    fig, ax = plt.subplots(figsize=(9.0, 9.0 * h / w + 0.4))
    ax.set_facecolor("#101418")

    def width_pt(width_mm: float) -> float:
        return width_mm * (9.0 * 72.0 * 0.86) / w

    for layer, (color, alpha, z) in LAYER_STYLE.items():
        segs, widths = [], []
        for t in res.tracks:
            if t.layer != layer:
                continue
            for a, b in zip(t.pts, t.pts[1:], strict=False):
                segs.append((a, b))
                widths.append(width_pt(t.width))
        if segs:
            ax.add_collection(
                LineCollection(
                    segs, colors=color, alpha=alpha, zorder=z, linewidths=widths, capstyle="round"
                )
            )
    for p in res.pads:
        color = "#e8e8ee" if p.layer in ("F.Cu", "*.Cu") else "#8090c0"
        rect = plt.Rectangle((-p.w / 2, -p.h / 2), p.w, p.h, facecolor=color, zorder=5)
        tr = matplotlib.transforms.Affine2D().rotate_deg(-p.rot).translate(p.x, p.y) + ax.transData
        rect.set_transform(tr)
        ax.add_patch(rect)
    for v in res.vias:
        ax.add_patch(plt.Circle((v.x, v.y), v.pad / 2, color="#e6e6e6", zorder=6))
        ax.add_patch(plt.Circle((v.x, v.y), v.drill / 2, color="#101418", zorder=7))
    for hx, hy, hd in res.holes:
        ax.add_patch(plt.Circle((hx, hy), hd / 2, fill=False, color="#8aa0b4", zorder=6))
    for ref, (x, y, _rot) in res.placements.items():
        ax.annotate(ref, (x, y), color="#8aa0b4", ha="center", va="center", fontsize=4, zorder=8)
    ax.plot([0, w, w, 0, 0], [0, 0, h, h, 0], color="#e6c832", linewidth=1.4, zorder=8)
    ax.set_xlim(-3, w + 3)
    ax.set_ylim(h + 3, -3)
    ax.set_aspect("equal")
    ax.set_axis_off()
    fig.tight_layout(pad=0)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=dpi, facecolor="#101418")
    plt.close(fig)
