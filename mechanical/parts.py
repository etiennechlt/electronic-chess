"""CadQuery part builders for the mockup: test pucks, winding jig,
adjustable magnet bracket. Print orientation notes are in the README.
"""

from __future__ import annotations

import cadquery as cq
from common import (
    FIT_LOOSE,
    FIT_TIGHT,
    M3_CLEAR,
    M3_NUT_FLAT,
    M3_NUT_H,
    PuckDims,
)


def piece_puck(dims: PuckDims) -> cq.Workplane:
    """Test piece: cylinder with the resonator stack bored from below.

    Stack from the playing surface up (brief 3.2): felt (glued by the
    user), coil in the bottom 2 mm, capacitor in a lateral slot, hard
    ferrite magnet above the coil. A grip dome tops the puck.
    """
    body = (
        cq.Workplane("XY")
        .circle(dims.base_d / 2.0)
        .extrude(dims.height)
        .edges(">Z")
        .fillet(2.0)
    )
    # Stepped bore from the bottom: coil recess then magnet pocket.
    coil_bore_d = dims.coil_d + 2.0 * FIT_LOOSE
    magnet_bore_d = dims.magnet_d + 2.0 * FIT_TIGHT
    coil_depth = dims.coil_h + 0.3
    magnet_depth = dims.magnet_h + 0.3
    body = (
        body.faces("<Z").workplane()
        .circle(coil_bore_d / 2.0)
        .cutBlind(-coil_depth)
    )
    body = (
        body.faces("<Z").workplane(offset=-coil_depth)
        .circle(magnet_bore_d / 2.0)
        .cutBlind(-magnet_depth)
    )
    # Lateral capacitor slot next to the coil recess (0805-sized C0G
    # plus leads), reaching the outer wall for soldering access.
    slot_w, slot_h, slot_l = 3.2, 2.4, dims.base_d / 2.0
    body = (
        body.faces("<Z").workplane()
        .center(dims.coil_d / 4.0 + slot_l / 2.0 - 1.0, 0.0)
        .rect(slot_l, slot_w)
        .cutBlind(-slot_h)
    )
    return body


def winding_jig(coil_d_out: float, coil_d_in: float, coil_h: float) -> cq.Workplane:
    """Two-part winding spool printed as one piece with a break line:
    core plus bottom flange; the top flange is a separate washer.

    This builder returns the core part; `winding_jig_washer` the top.
    """
    flange_d = coil_d_out + 3.0
    core_d = coil_d_in - 2.0 * FIT_TIGHT
    part = (
        cq.Workplane("XY")
        .circle(flange_d / 2.0)
        .extrude(2.0)
        .faces(">Z").workplane()
        .circle(core_d / 2.0)
        .extrude(coil_h)
        .faces(">Z").workplane()
        .circle((core_d - 1.0) / 2.0)
        .extrude(4.0)  # stub for the washer and the drill chuck
    )
    part = part.faces(">Z").workplane().hole(M3_CLEAR, 40.0)
    # Wire exit notch through the bottom flange.
    part = (
        part.faces("<Z").workplane()
        .center(core_d / 2.0 + (flange_d - core_d) / 4.0, 0.0)
        .rect((flange_d - core_d) / 2.0 + 1.0, 1.2)
        .cutBlind(-2.0)
    )
    return part


def winding_jig_washer(coil_d_out: float, coil_d_in: float) -> cq.Workplane:
    flange_d = coil_d_out + 3.0
    core_d = coil_d_in - 2.0 * FIT_TIGHT
    return (
        cq.Workplane("XY")
        .circle(flange_d / 2.0)
        .circle((core_d - 1.0) / 2.0 + FIT_LOOSE)
        .extrude(2.0)
    )


def magnet_bracket_base(hole_spacing: float, magnet_d: float) -> cq.Workplane:
    """Plate screwed under the coil board (4 x M3 on `hole_spacing`),
    with a central M3 nut trap: the adjustment screw rides in it and
    pushes the magnet cup toward the board.
    """
    plate = hole_spacing + 12.0
    body = (
        cq.Workplane("XY")
        .rect(plate, plate)
        .extrude(4.0)
        .edges("|Z")
        .fillet(3.0)
    )
    half = hole_spacing / 2.0
    body = (
        body.faces(">Z").workplane()
        .pushPoints([(-half, -half), (half, -half), (-half, half), (half, half)])
        .hole(M3_CLEAR)
    )
    body = body.faces(">Z").workplane().hole(M3_CLEAR)
    body = (
        body.faces("<Z").workplane()
        .polygon(6, M3_NUT_FLAT + 2.0 * FIT_TIGHT, circumscribed=True)
        .cutBlind(-M3_NUT_H)
    )
    _ = magnet_d
    return body


def magnet_cup(magnet_d: float, magnet_h: float) -> cq.Workplane:
    """Cup holding the N42 disc, with a captured nut underneath so the
    M3 screw from the bracket base raises or lowers it."""
    wall = 2.0
    cup_d = magnet_d + 2.0 * FIT_TIGHT + 2.0 * wall
    body = (
        cq.Workplane("XY")
        .circle(cup_d / 2.0)
        .extrude(magnet_h + 3.0)
        .faces(">Z").workplane()
        .circle((magnet_d + 2.0 * FIT_TIGHT) / 2.0)
        .cutBlind(-(magnet_h + 0.2))
    )
    body = (
        body.faces("<Z").workplane()
        .polygon(6, M3_NUT_FLAT + 2.0 * FIT_TIGHT, circumscribed=True)
        .cutBlind(-M3_NUT_H)
    )
    return body


def surface_template(cfg, pitch: float) -> cq.Workplane:
    """Drilling template for the wooden top plate.

    Same outline as the coil board, with the four mounting holes and
    the two light dots per square over the camp LEDs. Print flat or
    export as DXF, tape onto the plywood, drill through.
    """
    mock = cfg.mockup.coil_board
    w, h = mock.size_mm
    leds = mock.leds
    o = leds.corner_inset_mm
    plate = cq.Workplane("XY").box(w, h, 2.0, centered=(False, False, True))
    inset = mock.mounting_hole_inset_mm
    holes = [(inset, inset), (w - inset, inset),
             (inset, h - inset), (w - inset, h - inset)]
    first_corner = {"S1": "SE", "S2": "NE", "S3": "SE", "S4": "NW"}
    other = {"NE": "SW", "SW": "NE", "NW": "SE", "SE": "NW"}
    centers = {
        "S1": (pitch / 2.0, pitch / 2.0),
        "S2": (3.0 * pitch / 2.0, pitch / 2.0),
        "S3": (pitch / 2.0, 3.0 * pitch / 2.0),
        "S4": (3.0 * pitch / 2.0, 3.0 * pitch / 2.0),
    }
    d = pitch / 2.0 - o
    offs = {"NW": (-d, -d), "SE": (d, d), "NE": (d, -d), "SW": (-d, d)}
    lights = []
    for sq, (cx, cy) in centers.items():
        for which in (first_corner[sq], other[first_corner[sq]]):
            dx, dy = offs[which]
            lights.append((cx + dx, cy + dy))
    plate = (plate.faces(">Z").workplane(origin=(0, 0))
             .pushPoints(holes).hole(mock.mounting_hole_d_mm))
    plate = (plate.faces(">Z").workplane(origin=(0, 0))
             .pushPoints(lights).hole(leds.light_hole_d_mm))
    return plate
