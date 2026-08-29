"""Parametric engineering calculations for the LC-sensing automatic chessboard.

Every module reads its numbers from config/board.yaml through
load_config; nothing project-specific is hardcoded here.
"""

from .config import (
    DEFAULT_CONFIG_PATH,
    BoardConfig,
    Color,
    PieceType,
    base_diameter_mm,
    load_config,
    resolve_geometry,
)
from .corridor import check_corridor, corridor_margin_mm
from .coupling import coupling_k, mutual_coaxial_loops_nH, ringdown_signal, signal_vs_pitch
from .inductance import (
    mohan_L_uH,
    pcb_sense_coil,
    piece_coil_design,
    solve_turns,
    wheeler_multilayer_L_uH,
    wheeler_pancake_L_uH,
)
from .power import autonomy_h, peak_current_a, power_budget
from .resonance import check_separation, f0_hz, frequency_plan, ringdown_tau_us

__version__ = "0.1.0"

__all__ = [
    "DEFAULT_CONFIG_PATH",
    "BoardConfig",
    "Color",
    "PieceType",
    "autonomy_h",
    "base_diameter_mm",
    "check_corridor",
    "check_separation",
    "corridor_margin_mm",
    "coupling_k",
    "f0_hz",
    "frequency_plan",
    "load_config",
    "mohan_L_uH",
    "mutual_coaxial_loops_nH",
    "pcb_sense_coil",
    "peak_current_a",
    "piece_coil_design",
    "power_budget",
    "resolve_geometry",
    "ringdown_signal",
    "ringdown_tau_us",
    "signal_vs_pitch",
    "solve_turns",
    "wheeler_multilayer_L_uH",
    "wheeler_pancake_L_uH",
]
