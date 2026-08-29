"""Parametric KiCad spiral and coil-board generator.

Reads every dimension from config/board.yaml through chessboard_calc.
Outputs a complete, orderable .kicad_pcb plus rendering for review.
"""

from .board import build_coil_board
from .geometry import LayerPath, spiral_stack

__all__ = ["LayerPath", "build_coil_board", "spiral_stack"]
