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

Seven joints stay out of the router's reach and are drawn here as well:
the connector pin whose only way out is a half-millimetre gap in a
fan-out field, the two cell signals whose lane runs the length of the
strip, the amplifier input whose pad a bus straddles, and the decoupling
capacitor whose ground drop lands in a pocket of the pour. Note 04 of
docs/notes tells what makes each of them unreachable.

Everything is placed from the real pads, so the four cells of the
reduced quadrant and the sixteen of the full one are drawn the same way.
"""

from __future__ import annotations

from .board import NET_GND, Builder
from .circuit import cell_refs
from .escape import STUB_WIDTH_MM, runway_end
from .strip import BUSES_IN1
from .variant import is_reduced

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
CELL_WEST_VIA_X = 4.2  # west of the gate pull-down, before the escape lanes
CELL_GATE_LANE_MM = 1.1  # the gate's lane under the cell, that far below its pad
NFET_VIA_X = 10.77  # between the damping resistor and the source of the N-FET
BUS_X = {net: x for net, x, _w in BUSES_IN1}

# ---- the lanes of the links below. The x layout of the strip does not
# depend on the cell pitch, so they are fixed columns like those of a cell.
LINK_MUX_X = 11.45  # a mux input running south: east of the gate vias, west of the logic rail
LINK_DAMP_X = 3.1  # a damping gate running south: west of the cells and of the exit corridors
# The exit of the PULSE_EN pin threads the only gap of its fan-out field:
# it dips north of the via of the next pin, then passes south of the chain
# via of the pin before it. 0.21 mm of clearance at the worst point.
LINK_PULSE_DIP = (9.35, 13.65)
LINK_PULSE_RISE = (9.95, 13.9)
# The gain pair runs on the top layer, in the free row between the filter
# resistors and the amplifiers and then down the corridor between the two
# pin columns of the package, under its body. Only one column of the top
# layer gets out of the amplifier column, so the pad the other end takes
# goes down an inner layer to the same row.
LINK_GAIN_COL_X = 11.925  # the one free column of the top layer, east of the filters
LINK_GAIN_VIA_X = 10.9  # the inner-layer descent, west of the lane of the second cell
LINK_GAIN_ROWS = (87.1, 87.7)  # the two lanes of the pair, north one to the near pin
LINK_GAIN_DOWN_X = (4.5, 5.4)  # where each turns down, under the body of the amplifier


def _gap(a, b) -> float:
    """Middle of the free row between two pad rows of the east column."""
    return (a.y + a.h / 2.0 + b.y - b.h / 2.0) / 2.0


def _escape_via(b: Builder, net: str) -> tuple[float, float]:
    """The fan-out via ending the escape stub of a net. Every net linked
    below has exactly one fine-pitch pad, so one stub."""
    ends = [runway_end(pts, run) for n, pts, run, via, *_ in b.stubs if n == net and via]
    if len(ends) != 1:
        raise AssertionError(f"{net}: {len(ends)} escape vias, one expected")
    return ends[0]


def _channel_x(pads, cr) -> float:
    """The via channel of a cell east of the dual diodes, between their pad
    column and the FET column: the only spot of that row a via fits in."""
    diode, fet = pads[(cr["dual_a"], "3")], pads[(cr["pfet"], "1")]
    return (diode.x + diode.w / 2.0 + fet.x - fet.w / 2.0) / 2.0


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
        # ---- the gate of the exciting FET: its pull-down is in the west
        # column and the FET in the east one, and the only way across the
        # cell is under it, on the inner layer the 5 V grid leaves free
        gate, pull = pads[(cr["nfet"], "1")], pads[(cr["gate_pd"], "1")]
        y_lane = round(gate.y + CELL_GATE_LANE_MM, 3)
        T(pull.net, "F.Cu", [(pull.x, pull.y), (CELL_WEST_VIA_X, pull.y)], thin)
        V(pull.net, CELL_WEST_VIA_X, pull.y)
        T(
            pull.net,
            "In2.Cu",
            [
                (CELL_WEST_VIA_X, pull.y),
                (CELL_WEST_VIA_X, y_lane),
                (NFET_VIA_X, y_lane),
                (NFET_VIA_X, gate.y),
            ],
            lane,
        )
        V(pull.net, NFET_VIA_X, gate.y)
        T(pull.net, "F.Cu", [(NFET_VIA_X, gate.y), (gate.x, gate.y)], lane)
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
    # The links below belong to the reduced quadrant, the board being
    # made: they are placed from its real pads, but which pieces stay open
    # depends on how the strip is packed, and the full quadrant packs it
    # differently (its amplifier column and its muxes sit elsewhere, and
    # its mux pins escape without a via). It will get its own links when
    # its turn to be routed comes.
    if is_reduced(b.cfg):
        _links(b, pads, T, V)


def _links(b: Builder, pads: dict, T, V) -> None:
    """The joints the lattice router leaves open on the reduced quadrant,
    each out of its reach for a reason of its own (note 04): a channel
    narrower than the router's own track, a lane the length of the strip
    that no cost function would pick, a pad a bus straddles, a pocket of
    the pour. Drawn before it runs, so it routes the board around them."""
    thin, lane = STUB_WIDTH_MM, b.STRIP_THIN_MM

    # ---- PULSE_EN, in four pieces: the connector pin, the gate of the
    # pulse FET, its pull-down east of the LED rail, and the inverter of
    # the middle zone that makes the complement. The pin escapes east
    # through the gap of its fan-out field into the gate pad, the only
    # place a via fits; from that via one lane runs down the west edge of
    # the strip to the inverter and one runs east to the pull-down, under
    # the pad row of the zone.
    esc = _escape_via(b, "PULSE_EN")
    gate, pull, inv = pads[("Q2", "1")], pads[("R8", "1")], pads[("U6", "2")]
    # the via sits as far south in the gate pad as it fits: the chain lane
    # of the connector runs on In1 just north of it
    y_gate = gate.y + gate.h / 2.0 - b.STRIP_VIA_MM[0] / 2.0
    T("PULSE_EN", "In1.Cu", [esc, LINK_PULSE_DIP, LINK_PULSE_RISE, (gate.x, y_gate)], lane)
    V("PULSE_EN", gate.x, y_gate)
    y_cross = _gap(pads[("J1", "MP")], pads[("TP1", "1")])  # free row under the connector
    y_inv = _gap(pads[("U6", "4")], inv)  # between the two pad rows of the inverter
    # On In1: In2 west of the strip is the one layer the west pins of the
    # middle zone escape on, and a lane there walls them in.
    T(
        "PULSE_EN",
        "In1.Cu",
        [(gate.x, y_gate), (gate.x, y_cross), (inv.x, y_cross), (inv.x, y_inv)],
        lane,
    )
    V("PULSE_EN", inv.x, y_inv)
    T("PULSE_EN", "F.Cu", [(inv.x, y_inv), (inv.x, inv.y)], lane)
    y_east = _gap(gate, pads[("R10", "2")])
    # the middle of the room the LED rail leaves in the pull-down pad
    x_pull = (b.bus_5v_x + b.rt.ring_track_mm / 2.0 + b.clr + pull.x + pull.w / 2.0) / 2.0
    T("PULSE_EN", "In1.Cu", [(gate.x, y_gate), (gate.x, y_east), (x_pull, y_east)], lane)
    V("PULSE_EN", x_pull, y_east)
    T("PULSE_EN", "F.Cu", [(x_pull, y_east), (x_pull, pull.y)], lane)

    # ---- the mux input of the second cell: out of the cell by the via
    # channel east of its dual diode, then one lane south, at the width of
    # a stub because it ends between two vias of the mux fan-out field.
    cr = cell_refs(2)
    diode, mux = pads[(cr["dual_a"], "3")], _escape_via(b, "M2_A")
    x_ch = _channel_x(pads, cr)
    T("M2_A", "F.Cu", [(diode.x, diode.y), (x_ch, diode.y)], lane)
    V("M2_A", x_ch, diode.y)
    T("M2_A", "In1.Cu", [(x_ch, diode.y), (LINK_MUX_X, diode.y), (LINK_MUX_X, mux[1]), mux], thin)

    # ---- the damping gate of the fourth cell, from its decoder: the same
    # channel, then the row the via column of the cell leaves free, then
    # one lane down the west of the strip to the escape of the decoder pin.
    cr = cell_refs(4)
    fet, dec = pads[(cr["pfet"], "1")], _escape_via(b, "DAMP4_N")
    x_ch = _channel_x(pads, cr)
    y_row = (pads[(cr["dual_a"], "1")].y + pads[(cr["dual_a"], "2")].y) / 2.0
    T("DAMP4_N", "F.Cu", [(fet.x, fet.y), (x_ch, fet.y)], lane)
    V("DAMP4_N", x_ch, fet.y)
    T(
        "DAMP4_N",
        "In2.Cu",
        [(x_ch, fet.y), (x_ch, y_row), (LINK_DAMP_X, y_row), (LINK_DAMP_X, dec[1]), dec],
        lane,
    )

    # ---- the column of the amplifiers, three pads. The two analog rails
    # run the length of the strip on the inner layers and cross that
    # column: between them they leave 0.5 mm, where a via with its
    # clearance needs 0.75, and no via fits in the pads they straddle. The
    # three are reached on the top layer instead, each by the free row its
    # own neighbours leave, exactly as the cells are.
    # the positive input, out by the row between the two pads of its
    # coupling capacitor, east to the resistor that biases it
    cap, below = pads[("C14", "2")], pads[("C14", "1")]
    bias = pads[("R12", "1")]
    y_row = _gap(cap, below)
    T(
        "INA_INP",
        "F.Cu",
        [(cap.x, cap.y), (cap.x, y_row), (bias.x, y_row), (bias.x, bias.y)],
        lane,
    )
    # the reference divider, south into the row between the filter
    # resistors and the amplifier, then east to the other pad of the net
    div, other = pads[("R16", "2")], pads[("R18", "2")]
    y_row = _gap(pads[("R17", "1")], pads[("U7", "8")])
    T("VREF", "F.Cu", [(div.x, div.y), (div.x, y_row), (other.x, y_row), (other.x, other.y)], lane)
    # the two ends of the gain resistor: no pad of either net is within
    # reach on the top layer, and the amplifier is ten millimetres west, so
    # the pair leaves the column, runs the free row above the amplifiers
    # and turns down between its two pin columns, under its body. The pad
    # above the resistor goes to the pin below and the other way round;
    # they cross once, in the descent out of the column, where one takes
    # the top layer and the other an inner one.
    near, far = pads[("U5", "2")], pads[("U5", "3")]
    gain_near, gain_far = pads[("R14", "1")], pads[("R14", "2")]
    y_near, y_far = LINK_GAIN_ROWS
    x_near, x_far = LINK_GAIN_DOWN_X
    T(
        "RG_A",
        "F.Cu",
        [
            (gain_near.x, gain_near.y),
            (LINK_GAIN_COL_X, gain_near.y),
            (LINK_GAIN_COL_X, y_near),
            (x_near, y_near),
            (x_near, near.y),
            (near.x, near.y),
        ],
        lane,
    )
    T("RG_B", "F.Cu", [(gain_far.x, gain_far.y), (LINK_GAIN_VIA_X, gain_far.y)], lane)
    V("RG_B", LINK_GAIN_VIA_X, gain_far.y)
    T("RG_B", "In2.Cu", [(LINK_GAIN_VIA_X, gain_far.y), (LINK_GAIN_VIA_X, y_far)], lane)
    V("RG_B", LINK_GAIN_VIA_X, y_far)
    T(
        "RG_B",
        "F.Cu",
        [(LINK_GAIN_VIA_X, y_far), (x_far, y_far), (x_far, far.y), (far.x, far.y)],
        lane,
    )

    # ---- the ground of the 5VA decoupling capacitor of the middle zone:
    # its own drop lands in a pocket of the pour that the routes around the
    # capacitor cut off from the plane. It ties instead to the ground pad
    # of the capacitor below it, in the same column, whose drop reaches it.
    top, bottom = pads[("C7", "2")], pads[("C5", "2")]
    # The lane crosses the 5VA pad of the capacitor between the two, and a
    # via bores every layer: it hugs the west edge of the column so that
    # pad keeps, east of it, the room its own via needs.
    x_col = top.x - top.w / 2.0 + lane / 2.0
    V(NET_GND, x_col, top.y)
    T(NET_GND, "In2.Cu", [(x_col, top.y), (x_col, bottom.y)], lane)
    V(NET_GND, x_col, bottom.y)

    # ---- the 5VA of that same capacitor needs no route, only its via, and
    # the room for it: the column is 0.95 mm wide, the ground lane takes
    # its west side, and what is left holds exactly one via. Placed here,
    # it survives the routing of the lanes around it, and it gives the
    # router what the pad alone never had, a landing on all four layers
    # (the top one is walled in by the pads of the zone).
    rail = pads[("C7", "1")]
    V("5VA", rail.x + rail.w / 2.0 - b.STRIP_VIA_MM[0] / 2.0, rail.y)
