"""Every number a film shows, computed from config/board.yaml.

A composition never types a number: it carries `data-fact="key"` and
the film fills the text from `assets/facts.js`, which this module
writes. Labels are formatted the French way (decimal comma, narrow
no-break space before units and between thousands), once, here.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

from chessboard_calc import plateau, power
from chessboard_calc.config import DEFAULT_CONFIG_PATH, BoardConfig, PieceType, resolve_geometry
from chessboard_calc.resonance import frequency_plan

from .signature import notes

ROOT = Path(__file__).resolve().parents[2]
NNBSP = " "

PIECES_FR = {
    "pawn": ("pion", "m"),
    "knight": ("cavalier", "m"),
    "bishop": ("fou", "m"),
    "rook": ("tour", "f"),
    "queen": ("dame", "f"),
    "king": ("roi", "m"),
}
COLORS_FR = {"black": ("noir", "noire"), "white": ("blanc", "blanche")}

# The lines of config/board.yaml quoted on screen, by their dotted path.
YAML_QUOTE = (
    "resonator.L_target_uH",
    "resonator.C_tol_pct",
    "pitch.plateau_mm",
    "power.battery.layout",
)


def fr(value: float, digits: int = 0) -> str:
    """216.6 -> '216,6', 1399 -> '1 399' with narrow no-break spaces."""
    text = f"{value:,.{digits}f}".replace(",", NNBSP).replace(".", ",")
    return text


def piece_name(piece: str, color: str) -> str:
    name, gender = PIECES_FR[piece]
    masc, fem = COLORS_FR[color]
    return f"{name} {fem if gender == 'f' else masc}"


def yaml_quote(path: Path = DEFAULT_CONFIG_PATH, keys: tuple[str, ...] = YAML_QUOTE) -> list[str]:
    """The quoted keys as they stand in the yaml, under their section headers,
    comments stripped: the screen shows the file, not a retyped copy."""
    stack: list[tuple[int, str]] = []
    found: dict[str, tuple[list[str], str]] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].rstrip()
        m = re.match(r"^( *)([A-Za-z_0-9]+):(.*)$", line)
        if not m:
            continue
        indent, key, rest = len(m.group(1)), m.group(2), m.group(3)
        while stack and stack[-1][0] >= indent:
            stack.pop()
        dotted = ".".join([k for _, k in stack] + [key])
        if dotted in keys:
            found[dotted] = ([k for _, k in stack], f"{key}:{rest}")
        stack.append((indent, key))
    out: list[str] = []
    open_sections: list[str] = []
    for key in keys:
        parents, leaf = found[key]
        common = 0
        while (
            common < min(len(parents), len(open_sections))
            and parents[common] == open_sections[common]
        ):
            common += 1
        for depth in range(common, len(parents)):
            out.append("  " * depth + parents[depth] + ":")
        out.append("  " * len(parents) + leaf)
        open_sections = parents
    return out


def facts(cfg: BoardConfig) -> dict:
    """The film's facts. Each label is the exact text a composition shows."""
    plan = frequency_plan(cfg)
    geo = plateau.geometry(cfg)
    pawn = resolve_geometry(cfg, geo.pitch_mm).classes[PieceType.PAWN]
    q = cfg.plateau.quadrant.squares
    lines = []
    for note, line in zip(notes(cfg), plan.lines, strict=True):
        lines.append(
            {
                "slug": note.slug,
                "piece": note.piece,
                "color": note.color,
                "name": piece_name(note.piece, note.color),
                "khz": round(line.f0_hz / 1e3, 1),
                "label": f"{fr(line.f0_hz / 1e3, 1)}{NNBSP}kHz",
                "audio_hz": round(note.audio_hz, 1),
                "sound": f"assets/sons/{note.slug}.wav",
            }
        )
    lowest = plan.lines[0]
    return {
        "lines": lines,
        "line": {ln["slug"]: ln for ln in lines},
        "lines_count": fr(len(lines)),
        "band_low_khz": fr(plan.lines[0].f0_hz / 1e3),
        "band_high_khz": fr(plan.lines[-1].f0_hz / 1e3),
        "coil_uh": fr(cfg.resonator.L_target_uH),
        "cap_tol": f"{fr(cfg.resonator.C_tol_pct)}{NNBSP}%",
        "pulse_us": fr(cfg.measurement.drive.pulse_us),
        "window_us": fr(cfg.measurement.window_us),
        "tau_us": fr(lowest.tau_nominal_us),
        "module_cm": fr(geo.module_mm / 10),
        "thickness_mm": fr(geo.thin.height_mm + geo.top_module_thickness_mm),
        "plywood_mm": fr(cfg.gap.surface_mm),
        "quadrants": fr((cfg.plateau.grid // q) ** 2),
        "quadrant_grid": f"{q}{NNBSP}×{NNBSP}{q}",
        "coils": fr(cfg.plateau.grid**2),
        "leds": fr(len(plateau.led_points(cfg))),
        "mcu": re.sub(r"[A-Z]{2}$", "", cfg.mcu.part),
        "radio": cfg.clock.radio.upper(),
        "clock_mcu": re.sub(r"-WROOM.*$", "", cfg.clock.mcu),
        "battery": cfg.power.battery.layout.split("S")[0] + "S",
        "energy_wh": fr(cfg.power.battery.energy_wh, 1),
        "autonomy_human_h": fr(power.autonomy_h(cfg, engine_on=False)),
        "autonomy_engine_h": fr(power.autonomy_h(cfg, engine_on=True)),
        "scale_step_s": cfg.serie.scale_step_s,
        "yaml_quote": yaml_quote(),
        "squares": fr(cfg.plateau.grid**2),
        "spirals_per_quadrant": fr(q**2),
        "cells": fr(_cells(cfg)),
        "base_height_mm": fr(geo.thin.height_mm),
        "gantry_thickness_mm": fr(geo.gantry.height_mm + geo.top_module_thickness_mm),
        "felt_mm": fr(cfg.gap.felt_mm, 1),
        "pawn_coil_mm": fr(pawn.coil_d_out_mm, 1),
        "pawn_magnet_mm": fr(pawn.magnet_d_mm, 1),
        "idle_scan_hz": fr(cfg.measurement.idle_scan_hz),
        "scene": scene(cfg),
    }


def _cells(cfg: BoardConfig) -> int:
    """3S1P is three cells: series count times parallel count."""
    m = re.fullmatch(r"(\d+)S(\d+)P", cfg.power.battery.layout)
    return int(m.group(1)) * int(m.group(2))


def scene(cfg: BoardConfig) -> dict:
    """Plain numbers for the 3D scenes (mm, CadQuery frame): the pieces drawn
    on their real bases, what is inside them, the light holes, the clock."""
    geo = plateau.geometry(cfg)
    classes = resolve_geometry(cfg, geo.pitch_mm).classes
    pieces = {}
    for piece, g in classes.items():
        pieces[str(piece)] = {
            "base": g.base_mm,
            "height": round(g.base_mm * cfg.serie.piece_height_ratio[piece], 2),
            "coil_od": g.coil_d_out_mm,
            "coil_id": round(g.coil_d_in_mm, 2),
            "magnet_d": g.magnet_d_mm,
        }
    return {
        "pitch": geo.pitch_mm,
        "grid": cfg.plateau.grid,
        "pieces": pieces,
        "coil_h": cfg.resonator.coil.height_mm,
        "magnet_h": cfg.piece_magnet.thickness_mm,
        "felt": cfg.gap.felt_mm,
        "capacitor": list(cfg.serie.capacitor_mm),
        "led_points": [[round(x, 2), round(y, 2)] for x, y in plateau.led_points(cfg)],
        "gantry_lift": geo.gantry.top_z_mm - geo.thin.top_z_mm,
        "clock_tilt_deg": cfg.clock.rocker.tilt_deg,
        "scale_step_s": cfg.serie.scale_step_s,
    }


def component_count() -> int:
    """Components of the plateau (four quadrants and the brain), as bomagg counts them."""
    sys.path.insert(0, str(ROOT / "tools"))
    import bomagg

    plan = bomagg.parse_plan([f"{path}:{count}" for path, count in bomagg.PLATEAU])
    _, parts, _ = bomagg.aggregate(plan)
    return sum(parts.values())


def collected_tests() -> int:
    """Tests the suite collects right now, the number the film quotes."""
    out = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return int(re.search(r"(\d+) tests? collected", out).group(1))


def counters() -> dict:
    """Facts about the repository rather than the board: slower, film builds only."""
    return {"components": fr(component_count()), "tests": fr(collected_tests())}


FILL_JS = """
window.fillFacts = function (root) {
  root.querySelectorAll("[data-fact]").forEach(function (el) {
    var value = el.getAttribute("data-fact").split(".").reduce(function (node, key) {
      return node == null ? undefined : node[key];
    }, window.FACTS);
    if (value === undefined) throw new Error("unknown fact " + el.getAttribute("data-fact"));
    el.textContent = value;
  });
};
"""


def write_js(path: Path, data: dict) -> None:
    """`window.FACTS` and the `fillFacts(root)` helper every scene calls."""
    path.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(data, ensure_ascii=False, indent=1)
    path.write_text(
        "// Written by `python -m serie film` from config/board.yaml: do not edit.\n"
        f"window.FACTS = {body};\n{FILL_JS.lstrip()}",
        encoding="utf-8",
    )
