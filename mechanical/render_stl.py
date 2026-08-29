"""Shaded PNG renders of STL files (matplotlib, no GL needed).

Used by the documentation build; also handy to eyeball a part:
    python mechanical/render_stl.py exports/puck-pawn-black.stl out.png
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d.art3d import Poly3DCollection


def read_stl(path: Path) -> np.ndarray:
    """Triangles (n, 3, 3) from a binary STL."""
    data = path.read_bytes()
    if data[:5] == b"solid" and b"facet" in data[:200]:
        # ASCII STL fallback.
        tris = []
        cur = []
        for line in data.decode("ascii", "ignore").splitlines():
            line = line.strip()
            if line.startswith("vertex"):
                cur.append([float(v) for v in line.split()[1:4]])
                if len(cur) == 3:
                    tris.append(cur)
                    cur = []
        return np.array(tris)
    n = struct.unpack("<I", data[80:84])[0]
    tris = np.frombuffer(data, dtype=np.float32, count=n * 12,
                         offset=84 + 0).reshape(-1, 12)
    # Binary records are 50 bytes (12 floats + 2 spare bytes): re-read
    # with a structured dtype instead.
    rec = np.dtype([("n", "<3f4"), ("v", "<9f4"), ("attr", "<u2")])
    body = np.frombuffer(data, dtype=rec, count=n, offset=84)
    _ = tris
    return body["v"].reshape(-1, 3, 3).astype(float)


def render(tris: np.ndarray, out_path: Path, elev: float = 28.0,
           azim: float = -55.0, color: str = "#7fa8c9") -> None:
    fig = plt.figure(figsize=(6, 6))
    ax = fig.add_subplot(projection="3d")
    ax.set_facecolor("#101418")
    fig.patch.set_facecolor("#101418")
    light = np.array([0.4, -0.5, 0.75])
    light = light / np.linalg.norm(light)
    normals = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    norm = np.linalg.norm(normals, axis=1, keepdims=True)
    normals = normals / np.maximum(norm, 1e-12)
    shade = 0.35 + 0.65 * np.clip(normals @ light, 0.0, 1.0)
    base = np.array(matplotlib.colors.to_rgb(color))
    facecolors = np.clip(base[None, :] * shade[:, None], 0.0, 1.0)
    coll = Poly3DCollection(tris, facecolors=facecolors, edgecolors="none")
    ax.add_collection3d(coll)
    lo = tris.reshape(-1, 3).min(axis=0)
    hi = tris.reshape(-1, 3).max(axis=0)
    center = (lo + hi) / 2.0
    radius = float(np.max(hi - lo)) / 2.0 * 1.15
    ax.set_xlim(center[0] - radius, center[0] + radius)
    ax.set_ylim(center[1] - radius, center[1] + radius)
    ax.set_zlim(center[2] - radius, center[2] + radius)
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()
    fig.tight_layout(pad=0)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=200, facecolor="#101418")
    plt.close(fig)


if __name__ == "__main__":
    render(read_stl(Path(sys.argv[1])), Path(sys.argv[2]))
