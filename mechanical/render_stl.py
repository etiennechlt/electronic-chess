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
import matplotlib.colors
import matplotlib.image
import numpy as np


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


def _camera(elev: float, azim: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Orthographic camera basis, matplotlib convention (elev above the xy
    plane, azim around z). Returns (right, up, toward-camera) unit vectors."""
    el, az = np.radians(elev), np.radians(azim)
    d = np.array([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)])
    right = np.cross(-d, np.array([0.0, 0.0, 1.0]))
    right /= np.linalg.norm(right)
    up = np.cross(right, -d)
    up /= np.linalg.norm(up)
    return right, up, d


def render(tris: np.ndarray | list, out_path: Path, elev: float = 28.0,
           azim: float = -55.0, color: str = "#7fa8c9", size: int = 1200) -> None:
    """Render one triangle array, or a list of (triangles, color) parts.

    Software z-buffer rasterizer (numpy, no GL): every pixel keeps the
    nearest surface, so large slabs and small parts occlude correctly,
    which the painter's sort of a 3D axes cannot guarantee. Orthographic
    projection, flat shading, 2x supersampling.
    """
    parts = tris if isinstance(tris, list) else [(tris, color)]
    right, up, toward = _camera(elev, azim)
    light = np.array([0.4, -0.5, 0.75])
    light /= np.linalg.norm(light)

    all_tris = np.concatenate([np.asarray(t, dtype=float) for t, _ in parts])
    colors = np.concatenate([
        np.repeat(np.array(matplotlib.colors.to_rgb(c))[None, :], len(t), axis=0)
        for t, c in parts])
    normals = np.cross(all_tris[:, 1] - all_tris[:, 0], all_tris[:, 2] - all_tris[:, 0])
    norm = np.linalg.norm(normals, axis=1, keepdims=True)
    normals = normals / np.maximum(norm, 1e-12)
    # two-sided lighting: a face seen from behind is lit like its front
    shade = 0.35 + 0.65 * np.abs(normals @ light)
    colors = np.clip(colors * shade[:, None], 0.0, 1.0)

    flat = all_tris.reshape(-1, 3)
    px = flat @ right
    py = flat @ up
    depth = flat @ toward
    ss = 2
    res = size * ss
    span = max(px.max() - px.min(), py.max() - py.min()) * 1.08
    scale = res / span
    cx, cy = (px.max() + px.min()) / 2.0, (py.max() + py.min()) / 2.0
    sx = (px - cx) * scale + res / 2.0
    sy = res / 2.0 - (py - cy) * scale
    sx = sx.reshape(-1, 3)
    sy = sy.reshape(-1, 3)
    depth = depth.reshape(-1, 3)

    bg = np.array(matplotlib.colors.to_rgb("#101418"))
    img = np.empty((res, res, 3), dtype=float)
    img[:] = bg
    zbuf = np.full((res, res), -np.inf)
    for i in range(len(sx)):
        x0, x1 = int(np.floor(sx[i].min())), int(np.ceil(sx[i].max()))
        y0, y1 = int(np.floor(sy[i].min())), int(np.ceil(sy[i].max()))
        x0, y0 = max(x0, 0), max(y0, 0)
        x1, y1 = min(x1, res - 1), min(y1, res - 1)
        if x1 < x0 or y1 < y0:
            continue
        (ax, bx, cx_), (ay, by, cy_) = sx[i], sy[i]
        area = (bx - ax) * (cy_ - ay) - (by - ay) * (cx_ - ax)
        if abs(area) < 1e-9:
            continue
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        w0 = ((bx - gx) * (cy_ - gy) - (by - gy) * (cx_ - gx)) / area
        w1 = ((cx_ - gx) * (ay - gy) - (cy_ - gy) * (ax - gx)) / area
        w2 = 1.0 - w0 - w1
        inside = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
        if not inside.any():
            continue
        z = w0 * depth[i, 0] + w1 * depth[i, 1] + w2 * depth[i, 2]
        tile = zbuf[y0:y1 + 1, x0:x1 + 1]
        win = inside & (z > tile)
        tile[win] = z[win]
        img[y0:y1 + 1, x0:x1 + 1][win] = colors[i]
    # 2x2 box filter down to the output size
    img = img.reshape(size, ss, size, ss, 3).mean(axis=(1, 3))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    matplotlib.image.imsave(str(out_path), np.clip(img, 0.0, 1.0))


if __name__ == "__main__":
    render(read_stl(Path(sys.argv[1])), Path(sys.argv[2]))
