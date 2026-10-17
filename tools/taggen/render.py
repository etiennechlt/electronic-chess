"""Matplotlib rendering of the tag panel: outline, copper per layer,
vias, bites, for the documentation."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .panel import PanelResult


def render_panel(res: PanelResult, out_path: Path, dpi: int = 200) -> None:
    import re

    w, h = res.panel_mm
    fig, ax = plt.subplots(figsize=(9.0, 9.0 * h / w + 0.4))
    ax.set_facecolor("#101418")
    for ring in res.outline_rings:
        xs, ys = zip(*ring, strict=False)
        ax.plot(xs, ys, color="#e6c832", linewidth=0.8, zorder=8)
    seg = re.compile(
        r'\(segment \(start (\S+) (\S+)\) \(end (\S+) (\S+)\) \(width (\S+)\) \(layer "(\S+)"\)'
    )
    colors = {"F.Cu": "#c83232", "B.Cu": "#3264c8"}
    for item in res.board.body:
        m = seg.match(item.strip())
        if m:
            x1, y1, x2, y2, width, layer = m.groups()
            ax.plot(
                [float(x1), float(x2)],
                [float(y1), float(y2)],
                color=colors.get(layer, "#888"),
                linewidth=float(width) * 9.0 * 72.0 * 0.86 / w,
                alpha=0.9,
                zorder=3 if layer == "F.Cu" else 1,
                solid_capstyle="round",
            )
    for bx, by in res.bites:
        ax.add_patch(plt.Circle((bx, by), 0.25, color="#8aa0b4", zorder=6))
    for ref, (x, y, _rot) in res.placements.items():
        ax.annotate(ref, (x, y), color="#8aa0b4", ha="center", va="center", fontsize=4, zorder=9)
    ax.set_xlim(-2, w + 2)
    ax.set_ylim(h + 2, -2)
    ax.set_aspect("equal")
    ax.set_axis_off()
    fig.tight_layout(pad=0)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=dpi, facecolor="#101418")
    plt.close(fig)
