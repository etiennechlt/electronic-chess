"""Routes drawn by hand in the front-end strip before the router runs
(seeds): what a human draws in pcbnew, kept in the generator so every
build redraws and checks them (quadgen.connect joins the rest to them).

A coil cell is four columns of parts stacked 0.1 mm apart, so nothing
passes between two parts of a column and a via fits only in a few
channels. Those channels are the same in every cell, which makes the
taps deterministic:

- west of the dual diodes, between the resistor column and them, a via
  column carries the ground of the two clamp diodes and their 5VA to an
  In1 feeder that runs along the cells and joins the 5VA bus above the
  first one (the bus itself is too far east for a cell to reach);
- the gate pull-down and the source of the N-FET drop to the ground pour
  in the channels their own row leaves free;
- the diodes of the east column tap the drive bus and the 12 V bus in
  the free rows between them, where the top layer carries no pad, and
  the ground of the freewheel diode drops there too.

Everything is placed from the real pads, so the four cells of the
reduced quadrant and the sixteen of the full one are drawn the same way.
"""

from __future__ import annotations

from .board import NET_GND, Builder
from .circuit import cell_refs
from .escape import STUB_WIDTH_MM
from .strip import BUSES_IN1

# the via column of a cell, between the resistor column (pads end at
# x = 6.63) and the dual diodes (pads start at 7.55)
CELL_VIA_X = 7.1
# the 5VA feeder along the cells on In1, between the ground drop of the
# gate pull-down and the reference vias under the bleed resistors
FEEDER_5VA_X = 6.05
FEEDER_WIDTH_MM = 0.4
# the reference (VREF) runs along the cells on In1 too, west of the 5VA
# feeder; each bleed resistor reaches it by a via under its own body,
# between its two pads, the only spot of that column a via fits in
SPINE_VREF_X = 5.2
SPINE_VREF_TURN_MM = 0.7  # how far north of the buses the spine turns east
GATE_PD_VIA_X = 6.7  # east of the 0402 pull-down, before the 0805 damping resistor
CELL_CLAMP_GAP_MM = 0.3  # the B clamp's row, that far above the damping resistor
NFET_VIA_X = 10.77  # between the damping resistor and the source of the N-FET
BUS_X = {net: x for net, x, _w in BUSES_IN1}


def _gap(a, b) -> float:
    """Middle of the free row between two pad rows of the east column."""
    return (a.y + a.h / 2.0 + b.y - b.h / 2.0) / 2.0


def hand_routes(b: Builder) -> None:
    pads = {(p.ref, p.number): p for p in b.res.pads}
    thin, lane = STUB_WIDTH_MM, b.STRIP_THIN_MM
    lay = b.lay

    def T(net, layer, pts, width):
        b.seed(net, layer, [(round(x, 3), round(y, 3)) for x, y in pts], width)

    def V(net, x, y):
        b.seed_via(net, round(x, 3), round(y, 3), *b.STRIP_VIA_MM)

    for coil in lay.coils:
        cr = cell_refs(coil.idx + 1)
        # ---- west column: the two clamp diodes, ground and 5VA
        for role in ("dual_a", "dual_b"):
            g, s = pads[(cr[role], "1")], pads[(cr[role], "2")]
            T(NET_GND, "F.Cu", [(g.x, g.y), (CELL_VIA_X, g.y)], thin)
            V(NET_GND, CELL_VIA_X, g.y)
            T("5VA", "F.Cu", [(s.x, s.y), (CELL_VIA_X, s.y)], thin)
            V("5VA", CELL_VIA_X, s.y)
            T("5VA", "In1.Cu", [(CELL_VIA_X, s.y), (FEEDER_5VA_X, s.y)], lane)
        # ---- the two ground pads of the middle columns
        # ---- each clamp resistor reaches the mux input of its own cell.
        # The two are four columns apart, with the via column and the clamp
        # diode between them; one row of each column is free, and not the
        # same one on both sides of the cell. The A clamp lies one row
        # above its diode pad: it steps down inside its own pad and runs
        # east along that row. The B clamp lies a row and a half below and
        # the reference resistor is in the way, so it runs east along its
        # own row, past the diode, and comes back down east of it.
        r_pad, d_pad = pads[(cr["clamp_a"], "2")], pads[(cr["dual_a"], "3")]
        x_jog = round(r_pad.x + r_pad.w / 2.0 - lane / 2.0, 3)
        T(
            r_pad.net,
            "F.Cu",
            [(r_pad.x, r_pad.y), (x_jog, r_pad.y), (x_jog, d_pad.y), (d_pad.x, d_pad.y)],
            lane,
        )
        r_pad, d_pad = pads[(cr["clamp_b"], "2")], pads[(cr["dual_b"], "3")]
        damp = pads[(cr["damp_r"], "1")]
        y_east = round(damp.y - damp.h / 2.0 - CELL_CLAMP_GAP_MM, 3)
        x_down = round((pads[(cr["dual_b"], "2")].x + d_pad.x) / 2.0, 3)
        T(
            r_pad.net,
            "F.Cu",
            [(r_pad.x, r_pad.y), (r_pad.x, y_east), (x_down, y_east), (x_down, d_pad.y)],
            lane,
        )
        T(r_pad.net, "F.Cu", [(x_down, d_pad.y), (d_pad.x, d_pad.y)], lane)
        # ---- the two bleed resistors reach the reference under their body
        for role in ("bleed_a", "bleed_b"):
            west, east = pads[(cr[role], "1")], pads[(cr[role], "2")]
            x_via = round((west.x + west.w / 2.0 + east.x - east.w / 2.0) / 2.0, 3)
            T("VREF", "F.Cu", [(east.x, east.y), (x_via, east.y)], thin)
            V("VREF", x_via, east.y)
        pd = pads[(cr["gate_pd"], "2")]
        T(NET_GND, "F.Cu", [(pd.x, pd.y), (GATE_PD_VIA_X, pd.y)], thin)
        V(NET_GND, GATE_PD_VIA_X, pd.y)
        nf = pads[(cr["nfet"], "2")]
        T(NET_GND, "F.Cu", [(nf.x, nf.y), (NFET_VIA_X, nf.y)], thin)
        V(NET_GND, NFET_VIA_X, nf.y)
        # ---- east column: drive bus, 12 V bus and the freewheel ground,
        # each in the free row under its own pad row
        bus = pads[(cr["bus"], "2")]  # drive bus
        fly = pads[(cr["fly"], "1")]  # 12 V, flyback
        gnd = pads[(cr["free"], "2")]  # ground of the freewheel diode
        y1 = _gap(bus, pads[(cr["fly"], "2")])
        y2 = _gap(pads[(cr["fly"], "2")], gnd)
        x_bus, x_vin = BUS_X["DRIVE_BUS"], BUS_X["VIN"]
        T("DRIVE_BUS", "F.Cu", [(bus.x, bus.y), (bus.x, y1), (x_bus, y1)], lane)
        V("DRIVE_BUS", x_bus, y1)
        T("VIN", "F.Cu", [(fly.x, fly.y), (x_vin, fly.y), (x_vin, y2)], lane)
        V("VIN", x_vin, y2)
        T(NET_GND, "F.Cu", [(gnd.x, gnd.y), (gnd.x, y2)], thin)
        V(NET_GND, gnd.x, y2)
    # the feeders: one run per band of cells, from the top of its first
    # cell to the bottom of its last, joined to its bus at the top. One run
    # per band and not one for the strip: between two bands lie the middle
    # zone and its packages, whose escapes own that room.
    pitch = b.q.strip.cell_pitch_mm
    bus_y0 = min(lay.cell_ys) - pitch / 2.0  # where the buses of the strip start
    bands: dict[int, list[float]] = {}
    for coil in lay.coils:
        bands.setdefault(coil.band, []).append(coil.cell_y)
    for ys in bands.values():
        y_top, y_bot = min(ys) - pitch / 2.0, max(ys) + pitch / 2.0
        T("5VA", "In1.Cu", [(FEEDER_5VA_X, y_top), (FEEDER_5VA_X, y_bot)], FEEDER_WIDTH_MM)
        T("5VA", "In1.Cu", [(FEEDER_5VA_X, y_top), (BUS_X["5VA"], y_top)], FEEDER_WIDTH_MM)
        # The spine reaches its bus on the top layer, in the free row just
        # past the cells (north of the first band, south of the last): the
        # analog rails run the whole strip on In1, so a link on that layer
        # would cross the 5VA bus.
        north = abs(y_top - bus_y0) < 1e-6
        y_turn = (y_top - SPINE_VREF_TURN_MM) if north else (y_bot + SPINE_VREF_TURN_MM)
        T(
            "VREF",
            "In1.Cu",
            [(SPINE_VREF_X, y_bot if north else y_top), (SPINE_VREF_X, y_turn)],
            lane,
        )
        V("VREF", SPINE_VREF_X, y_turn)
        T("VREF", "F.Cu", [(SPINE_VREF_X, y_turn), (BUS_X["VREF"], y_turn)], lane)
        V("VREF", BUS_X["VREF"], y_turn)
