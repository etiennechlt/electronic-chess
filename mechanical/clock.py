"""Rocker chess clock housing (ADR 0010), every dimension from config/board.yaml.

Body: sloped display face at the front (height_front to height_rear over
slope_end), flat rear top carrying the rocker bar in a recess, 2 mm
walls, open bottom closed by a screwed lid. Cutouts: display window,
encoder shaft, buzzer grille (on the slope), rocker recess with two
microswitch holes (rear), USB-C slot (rear wall). Frame: x to the
right, y toward the rear, z up, origin at the front-left-bottom corner.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import cadquery as cq
from common import Part

from chessboard_calc.config import BoardConfig

FILLET_VERTICAL = 6.0
FILLET_TOP = 2.5
RECESS_CLEARANCE = 2.0  # recess larger than the bar, per side
SWITCH_HOLE_D = 7.0
LID_PLAY = 0.4


def slope_angle(cfg: BoardConfig) -> float:
    ck = cfg.clock
    return math.atan2(ck.height_rear_mm - ck.height_front_mm, ck.slope_end_mm)


def slope_plane(cfg: BoardConfig) -> cq.Plane:
    """Plane on the sloped front face: local x = global x, local y runs up
    the slope from the front edge."""
    a = slope_angle(cfg)
    return cq.Plane(
        origin=(0, 0, cfg.clock.height_front_mm),
        xDir=(1, 0, 0),
        normal=(0, -math.sin(a), math.cos(a)),
    )


def rocker_center_y(cfg: BoardConfig) -> float:
    """The bar sits in the middle of the flat rear zone."""
    ck = cfg.clock
    return (ck.slope_end_mm + ck.body_mm[1]) / 2.0


def body(cfg: BoardConfig) -> cq.Workplane:
    ck = cfg.clock
    w, d = ck.body_mm
    prof = (
        cq.Workplane("YZ")
        .polyline(
            [
                (0, 0),
                (d, 0),
                (d, ck.height_rear_mm),
                (ck.slope_end_mm, ck.height_rear_mm),
                (0, ck.height_front_mm),
            ]
        )
        .close()
        .extrude(w)
    )
    prof = prof.edges("|Z").fillet(FILLET_VERTICAL)
    return prof.edges(">Z").fillet(FILLET_TOP)


def cutters(cfg: BoardConfig) -> cq.Workplane:
    ck = cfg.clock
    w, d = ck.body_mm
    depth = ck.wall_mm * 3.0
    top = cq.Workplane(slope_plane(cfg))
    win_w, win_h = ck.display.window_mm
    cut = top.center(w / 2.0, ck.display.up_slope_mm).rect(win_w, win_h).extrude(depth, both=True)
    cut = cut.union(
        top.pushPoints([(ck.encoder.x_mm, ck.encoder.up_slope_mm)])
        .circle(4.0)
        .extrude(depth, both=True)
    )
    gr = ck.buzzer_grille
    holes = [
        (gr.origin_mm[0] + gr.pitch_mm * i, gr.origin_mm[1] + gr.pitch_mm * j)
        for i in range(gr.holes[0])
        for j in range(gr.holes[1])
    ]
    cut = cut.union(top.pushPoints(holes).circle(gr.hole_d_mm / 2.0).extrude(depth, both=True))
    rk = ck.rocker
    y_bar = rocker_center_y(cfg)
    recess = (
        cq.Workplane("XY")
        .rect(rk.length_mm + 2 * RECESS_CLEARANCE, rk.width_mm + 2 * RECESS_CLEARANCE)
        .extrude(rk.recess_mm + 1.0)
        .translate((w / 2.0, y_bar, ck.height_rear_mm - rk.recess_mm))
    )
    cut = cut.union(recess)
    for x in switch_x(cfg):
        cut = cut.union(
            cq.Workplane("XY")
            .circle(SWITCH_HOLE_D / 2.0)
            .extrude(10.0)
            .translate((x, y_bar, ck.height_rear_mm - rk.recess_mm - 5.0))
        )
    usb_w, usb_h = ck.usb_c_slot_mm
    usb = (
        cq.Workplane("XZ")
        .center(w / 2.0, 6.0)
        .rect(usb_w, usb_h)
        .extrude(-depth)
        .translate((0, d + ck.wall_mm, 0))
    )
    return cut.union(usb)


def switch_x(cfg: BoardConfig) -> tuple[float, float]:
    ck = cfg.clock
    half = ck.rocker.length_mm / 2.0 - ck.rocker.switch_inset_mm
    return ck.body_mm[0] / 2.0 - half, ck.body_mm[0] / 2.0 + half


def shell(cfg: BoardConfig) -> cq.Workplane:
    return body(cfg).faces("<Z").shell(-cfg.clock.wall_mm).cut(cutters(cfg))


def lid(cfg: BoardConfig) -> cq.Workplane:
    ck = cfg.clock
    w, d = ck.body_mm
    inner_w, inner_d = w - 2 * ck.wall_mm - LID_PLAY, d - 2 * ck.wall_mm - LID_PLAY
    return (
        cq.Workplane("XY")
        .rect(inner_w, inner_d)
        .extrude(ck.lid_mm)
        .translate((w / 2.0, d / 2.0, 0))
    )


def rocker_bar(cfg: BoardConfig, tilt_deg: float | None = None) -> cq.Workplane:
    """Bar with rounded ends and its pivot pin, tilted about the pivot
    (positive tilt lowers the left, white, end)."""
    ck = cfg.clock
    rk = ck.rocker
    if tilt_deg is None:
        tilt_deg = rk.tilt_deg
    bar = (
        cq.Workplane("XY")
        .rect(rk.length_mm, rk.width_mm)
        .extrude(rk.thickness_mm)
        .edges("|Z")
        .fillet(rk.width_mm / 2.0 - 0.5)
        .edges(">Z")
        .fillet(2.0)
    )
    pivot = (
        cq.Workplane("XZ")
        .circle(rk.pivot_d_mm / 2.0)
        .extrude(rk.width_mm / 2.0 + 3.0, both=True)
        .translate((0, 0, -1.0))
    )
    bar = bar.union(pivot)
    # pivot height above the recess floor: the pressed end just reaches the floor
    drop = rk.length_mm / 2.0 * math.sin(math.radians(rk.tilt_deg))
    return bar.rotate((0, 0, 0), (0, 1, 0), -tilt_deg).translate(
        (ck.body_mm[0] / 2.0, rocker_center_y(cfg), ck.height_rear_mm - rk.recess_mm + drop)
    )


def knob(cfg: BoardConfig) -> cq.Workplane:
    ck = cfg.clock
    a = slope_angle(cfg)
    y = ck.encoder.up_slope_mm * math.cos(a)
    z = ck.height_front_mm + ck.encoder.up_slope_mm * math.sin(a) - 2.0
    return (
        cq.Workplane("XY")
        .circle(ck.encoder.knob_d_mm / 2.0)
        .extrude(10.0)
        .translate((ck.encoder.x_mm, y, z))
    )


def display_glass(cfg: BoardConfig) -> cq.Workplane:
    ck = cfg.clock
    a = slope_angle(cfg)
    win_w, win_h = ck.display.window_mm
    return (
        cq.Workplane(slope_plane(cfg))
        .center(ck.body_mm[0] / 2.0, ck.display.up_slope_mm)
        .rect(win_w, win_h)
        .extrude(1.0)
        .translate((0, 0, -0.5 * math.cos(a)))
    )


def internals(cfg: BoardConfig) -> list[Part]:
    """PCB, cell and switches, as placeholders sized from the yaml."""
    ck = cfg.clock
    w, d = ck.body_mm
    pcb = (
        cq.Workplane("XY")
        .box(w - 10.0, d - 10.0, 1.6, centered=(False, False, False))
        .translate((5.0, 5.0, ck.lid_mm + 1.0))
    )
    cell_r, cell_l = 9.2, 65.0
    cell = (
        cq.Workplane("YZ")
        .circle(cell_r)
        .extrude(cell_l)
        .translate((w / 2.0 - cell_l / 2.0, 22.0, ck.lid_mm + 3.0 + cell_r))
    )
    parts = [
        Part(
            "carte horloge : ESP32-C3, chargeur USB-C, buzzer", pcb.val(), "#2f3b2a", "horloge", 0.6
        ),
        Part("18650 1S, 3 Ah", cell.val(), "#5aa0c8", "horloge", 0.6),
    ]
    y_bar = rocker_center_y(cfg)
    for x, camp in zip(switch_x(cfg), ("blanc", "noir"), strict=True):
        sw = (
            cq.Workplane("XY")
            .box(6.0, 6.0, 4.0, centered=(True, True, False))
            .translate((x, y_bar, ck.height_rear_mm - ck.rocker.recess_mm - 9.0))
        )
        parts.append(Part(f"microrupteur {camp}", sw.val(), "#22262b", "horloge", 0.6))
    return parts


def assembly(cfg: BoardConfig) -> list[Part]:
    return [
        Part("fond visse", lid(cfg).val(), "#3b414a", "horloge", 0.0),
        *internals(cfg),
        Part(
            "horloge : boitier imprime, face inclinee", shell(cfg).val(), "#2f3338", "horloge", 1.4
        ),
        Part("ecran 2,4 pouces IPS", display_glass(cfg).val(), "#0f1a26", "horloge", 1.5),
        Part(
            "barre a bascule : appuyer d'un cote lance le temps de l'autre",
            rocker_bar(cfg).val(),
            "#e9e3d6",
            "horloge",
            1.8,
        ),
        Part("encodeur : menus, cadence, mode de jeu", knob(cfg).val(), "#8c8f95", "horloge", 1.8),
    ]
