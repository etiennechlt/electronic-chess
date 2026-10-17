"""Square NFC reader loops drawn on the board (note 25, paragraph 4.2;
note 27): concentric turns on the top layer, the inner end brought back
out by a bridge on the back layer, both ends leaving the south side of
the loop toward its reader.

Copper plan of one loop of n turns, centre (cx, cy), half-sides h[k]
of the turn centrelines (outer first):

- the top-side polyline starts on the south side, feed_offset west of
  the centre, runs west, north, east and south around turn 0, steps in
  to the south level of turn 1 on the east side, and so on; after the
  last turn's east side it steps in once more, one pitch inside that
  turn's south side (a tail that keeps the last turn whole: ending on
  the south side itself would short it), and runs west to pad 1 of the
  net tie footprint (hallrfid:NetTie_NFC_Loop), whose origin sits one
  tie step east of the bridge line; this copper is the net of the
  loop's first end;
- a via on pad 2 of the tie (bridge_offset east of the centre), a bridge
  on the back layer straight south under the turns, and a via back up
  past the outer turn carry the net of the second end to its series
  resistor;
- the first end reaches its own resistor by a short top-side track
  south from the start point.

The two pads of the tie are a clearance apart and joined by the
footprint's own copper: KiCad's net_tie_pad_groups makes that legal,
the turn's end cap stays clear of pad 2, and the generator's checks
know the tie (GenericBoard.ties). Everything here is geometry;
boardgen.hallrfid seeds it into the board.
"""

from __future__ import annotations

from dataclasses import dataclass

from chessboard_calc.hallrfid_demo import BRIDGE_OFFSET_MM, FEED_OFFSET_MM, FEED_TRACK_MM

XY = tuple[float, float]

TIE_STEP_MM = 1.5  # pad 1 of hallrfid:NetTie_NFC_Loop (its origin), from pad 2 along +x
TIE_PAD_MM = 1.0
BRIDGE_PAST_MM = 1.3  # the bridge comes back up this far past the outer turn centreline
BRIDGE_TRACK_MM = 0.5


@dataclass(frozen=True)
class LoopDrawing:
    centre: XY
    half_sides: tuple[float, ...]  # turn centreline half-sides, outer first
    track_mm: float
    turns: tuple[XY, ...]  # the top-side polyline, electrical order
    start: XY  # its first point, on the south side (feed of end 1)
    tie_at: XY  # origin of the tie footprint (pad 1), rotation 0
    bridge_via: XY  # on pad 2, down to the back layer
    bridge_end: XY  # past the outer turn, back up (feed of end 2)
    outline: tuple[float, float, float, float]  # outer copper edge
    opening_mm: float


def square_loop(
    cx: float, cy: float, side_mm: float, turns: int, track_mm: float, gap_mm: float
) -> LoopDrawing:
    """The drawing of a loop of `turns` concentric square turns whose
    outer copper edge is side_mm wide."""
    pitch = track_mm + gap_mm
    h = tuple(side_mm / 2.0 - track_mm / 2.0 - k * pitch for k in range(turns))
    tail_y = cy + h[-1] - pitch  # the inner tail, one pitch inside the last south side
    pts: list[XY] = [(cx - FEED_OFFSET_MM, cy + h[0])]
    for k, hk in enumerate(h):
        pts += [(cx - hk, cy + hk), (cx - hk, cy - hk), (cx + hk, cy - hk)]
        if k + 1 < turns:
            pts.append((cx + hk, cy + h[k + 1]))
        else:
            pts.append((cx + hk, tail_y))
            pts.append((cx + BRIDGE_OFFSET_MM + TIE_STEP_MM, tail_y))  # pad 1's centre
    tie_at = (cx + BRIDGE_OFFSET_MM + TIE_STEP_MM, tail_y)
    bridge_via = (cx + BRIDGE_OFFSET_MM, tail_y)  # pad 2's centre, over the feed line
    bridge_end = (bridge_via[0], cy + h[0] + BRIDGE_PAST_MM)
    outline = (cx - side_mm / 2.0, cy - side_mm / 2.0, cx + side_mm / 2.0, cy + side_mm / 2.0)
    opening = side_mm - 2.0 * (turns * track_mm + (turns - 1) * gap_mm)
    return LoopDrawing(
        centre=(cx, cy),
        half_sides=h,
        track_mm=track_mm,
        turns=tuple((round(x, 3), round(y, 3)) for x, y in pts),
        start=(round(pts[0][0], 3), round(pts[0][1], 3)),
        tie_at=(round(tie_at[0], 3), round(tie_at[1], 3)),
        bridge_via=(round(bridge_via[0], 3), round(bridge_via[1], 3)),
        bridge_end=(round(bridge_end[0], 3), round(bridge_end[1], 3)),
        outline=outline,
        opening_mm=opening,
    )


def seed_loop(gb, drawing: LoopDrawing, net_1: str, net_2: str, pad_1: XY, pad_2: XY) -> None:
    """Seed the loop into a GenericBoard: the turns and the feed of end 1
    on the top layer, the bridge of end 2 (via, back-layer run, via) and
    its top-side lead to the resistor pad. `pad_1` and `pad_2` are the
    pad centres the two ends must reach."""
    gb.seed(net_1, "F.Cu", list(drawing.turns), drawing.track_mm)
    gb.seed(net_1, "F.Cu", [drawing.start, (drawing.start[0], pad_1[1]), pad_1], FEED_TRACK_MM)
    gb.seed_via(net_2, *drawing.bridge_via)
    gb.seed(net_2, gb.layers[-1], [drawing.bridge_via, drawing.bridge_end], BRIDGE_TRACK_MM)
    gb.seed_via(net_2, *drawing.bridge_end)
    gb.seed(net_2, "F.Cu", [drawing.bridge_end, pad_2], FEED_TRACK_MM)


def router_blocks(
    drawing: LoopDrawing, keepout_mm: float, corridor: tuple[float, float, float, float]
) -> list[tuple[float, float, float, float, str]]:
    """Rectangles the router must keep out of around a loop: the turns
    and the ground keepout on the north, west and east sides, the turns
    on the south side except the corridor where the sensor trios leave
    the opening (its x range; the feed zone south of the outer turn
    stays open for the matching network)."""
    x0, y0, x1, y1 = drawing.outline
    k = keepout_mm
    half = drawing.opening_mm / 2.0
    cx, cy = drawing.centre
    ix0, iy0, ix1, iy1 = cx - half, cy - half, cx + half, cy + half
    south = y1 + 0.6  # just past the outer turn's copper
    cx0, _cy0, cx1, _cy1 = corridor
    name = "loop"
    return [
        (x0 - k, y0 - k, x1 + k, iy0, name),
        (x0 - k, iy0, ix0, iy1, name),
        (ix1, iy0, x1 + k, iy1, name),
        (x0 - k, iy1, cx0, south, name),
        (cx1, iy1, x1 + k, south, name),
    ]
