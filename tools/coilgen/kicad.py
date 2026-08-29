"""Minimal KiCad 7 board writer: s-expression emitters for the pieces
this project needs (segments, vias, through-hole and NPTH pads, text,
edge outline). Validated against kicad-cli in the test suite.
"""

from __future__ import annotations

from dataclasses import dataclass, field

KICAD_VERSION = 20221018

_LAYER_TABLE = """    (0 "F.Cu" signal)
    (1 "In1.Cu" signal)
    (2 "In2.Cu" signal)
    (31 "B.Cu" signal)
    (32 "B.Adhes" user "B.Adhesive")
    (33 "F.Adhes" user "F.Adhesive")
    (34 "B.Paste" user)
    (35 "F.Paste" user)
    (36 "B.SilkS" user "B.Silkscreen")
    (37 "F.SilkS" user "F.Silkscreen")
    (38 "B.Mask" user)
    (39 "F.Mask" user)
    (40 "Dwgs.User" user "User.Drawings")
    (41 "Cmts.User" user "User.Comments")
    (42 "Eco1.User" user "User.Eco1")
    (43 "Eco2.User" user "User.Eco2")
    (44 "Edge.Cuts" user)
    (45 "Margin" user)
    (46 "B.CrtYd" user "B.Courtyard")
    (47 "F.CrtYd" user "F.Courtyard")
    (48 "B.Fab" user)
    (49 "F.Fab" user)"""


def _f(v: float) -> str:
    """KiCad-friendly float: fixed 6 decimals, trailing zeros trimmed."""
    s = f"{v:.6f}".rstrip("0").rstrip(".")
    return s if s not in ("-0", "") else "0"


@dataclass
class Board:
    """Accumulates board content and serializes a .kicad_pcb file."""

    thickness_mm: float = 1.6
    title: str = ""
    nets: list[str] = field(default_factory=lambda: [""])
    body: list[str] = field(default_factory=list)

    def net(self, name: str) -> int:
        if name in self.nets:
            return self.nets.index(name)
        self.nets.append(name)
        return len(self.nets) - 1

    def segment(self, x1, y1, x2, y2, width_mm: float, layer: str, net: int) -> None:
        self.body.append(
            f"  (segment (start {_f(x1)} {_f(y1)}) (end {_f(x2)} {_f(y2)}) "
            f"(width {_f(width_mm)}) (layer \"{layer}\") (net {net}))"
        )

    def polyline(self, points, width_mm: float, layer: str, net: int) -> None:
        for i in range(len(points) - 1):
            self.segment(
                points[i][0], points[i][1], points[i + 1][0], points[i + 1][1],
                width_mm, layer, net,
            )

    def via(self, x, y, size_mm: float, drill_mm: float, net: int) -> None:
        self.body.append(
            f"  (via (at {_f(x)} {_f(y)}) (size {_f(size_mm)}) (drill {_f(drill_mm)}) "
            f"(layers \"F.Cu\" \"B.Cu\") (net {net}))"
        )

    def gr_line(self, x1, y1, x2, y2, layer: str, width_mm: float = 0.1) -> None:
        self.body.append(
            f"  (gr_line (start {_f(x1)} {_f(y1)}) (end {_f(x2)} {_f(y2)}) "
            f"(stroke (width {_f(width_mm)}) (type solid)) (layer \"{layer}\"))"
        )

    def gr_rect(self, x1, y1, x2, y2, layer: str, width_mm: float = 0.1) -> None:
        self.body.append(
            f"  (gr_rect (start {_f(x1)} {_f(y1)}) (end {_f(x2)} {_f(y2)}) "
            f"(stroke (width {_f(width_mm)}) (type solid)) (fill none) (layer \"{layer}\"))"
        )

    def gr_circle(self, cx, cy, r_mm, layer: str, width_mm: float = 0.1) -> None:
        self.body.append(
            f"  (gr_circle (center {_f(cx)} {_f(cy)}) (end {_f(cx + r_mm)} {_f(cy)}) "
            f"(stroke (width {_f(width_mm)}) (type solid)) (fill none) (layer \"{layer}\"))"
        )

    def gr_text(
        self, text: str, x, y, layer: str, size_mm: float = 1.5,
        thickness_mm: float = 0.2, mirror: bool = False,
    ) -> None:
        just = " (justify mirror)" if mirror else ""
        self.body.append(
            f"  (gr_text \"{text}\" (at {_f(x)} {_f(y)}) (layer \"{layer}\")\n"
            f"    (effects (font (size {_f(size_mm)} {_f(size_mm)}) "
            f"(thickness {_f(thickness_mm)})){just})\n  )"
        )

    def tht_pad_footprint(
        self, ref: str, value: str, x, y,
        pads: list[tuple[str, float, float, float, float, int, str]],
    ) -> None:
        """One footprint with plated through-hole pads.

        pads: (number, dx, dy, pad_d, drill_d, net_index, net_name).
        """
        lines = [
            f"  (footprint \"coilgen:{value}\" (layer \"F.Cu\") (at {_f(x)} {_f(y)})",
            "    (attr through_hole)",
            f"    (fp_text reference \"{ref}\" (at 0 -2.6) (layer \"F.SilkS\")",
            "      (effects (font (size 1 1) (thickness 0.15)))",
            "    )",
            f"    (fp_text value \"{value}\" (at 0 2.6) (layer \"F.Fab\")",
            "      (effects (font (size 1 1) (thickness 0.15)))",
            "    )",
        ]
        for num, dx, dy, pad_d, drill_d, net_i, net_name in pads:
            lines.append(
                f"    (pad \"{num}\" thru_hole circle (at {_f(dx)} {_f(dy)}) "
                f"(size {_f(pad_d)} {_f(pad_d)}) (drill {_f(drill_d)}) "
                f"(layers \"*.Cu\" \"*.Mask\") (net {net_i} \"{net_name}\"))"
            )
        lines.append("  )")
        self.body.append("\n".join(lines))

    def npth_hole(self, x, y, drill_mm: float, ref: str = "H") -> None:
        self.body.append(
            "\n".join(
                [
                    f"  (footprint \"coilgen:NPTH_{_f(drill_mm)}\" (layer \"F.Cu\") "
                    f"(at {_f(x)} {_f(y)})",
                    "    (attr exclude_from_pos_files exclude_from_bom)",
                    f"    (fp_text reference \"{ref}\" (at 0 -2.6) (layer \"F.Fab\")",
                    "      (effects (font (size 1 1) (thickness 0.15)))",
                    "    )",
                    "    (fp_text value \"NPTH\" (at 0 2.6) (layer \"F.Fab\")",
                    "      (effects (font (size 1 1) (thickness 0.15)))",
                    "    )",
                    f"    (pad \"\" np_thru_hole circle (at 0 0) "
                    f"(size {_f(drill_mm)} {_f(drill_mm)}) (drill {_f(drill_mm)}) "
                    "(layers \"*.Cu\" \"*.Mask\"))",
                    "  )",
                ]
            )
        )

    def serialize(self) -> str:
        nets = "\n".join(f"  (net {i} \"{n}\")" for i, n in enumerate(self.nets))
        header = (
            f"(kicad_pcb (version {KICAD_VERSION}) (generator coilgen)\n\n"
            f"  (general\n    (thickness {_f(self.thickness_mm)})\n  )\n\n"
            "  (paper \"A4\")\n"
            f"  (title_block\n    (title \"{self.title}\")\n  )\n\n"
            f"  (layers\n{_LAYER_TABLE}\n  )\n\n"
            "  (setup\n"
            "    (pad_to_mask_clearance 0)\n"
            "    (aux_axis_origin 0 0)\n"
            "  )\n\n"
        )
        return header + nets + "\n\n" + "\n".join(self.body) + "\n)\n"
