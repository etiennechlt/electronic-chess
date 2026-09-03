"""CI gate for the corridor constraint: r_mobile + r_static <= p/2 - budget.

If this file fails, the board deadlocks as early as e2-e4 and no
pathfinding can work around it. It must stay red-blocking in CI.
"""

import pytest

from chessboard_calc.config import BoardConfig, PieceType
from chessboard_calc.corridor import check_corridor, corridor_margin_mm


def test_all_pairs_pass_for_all_candidate_pitches(cfg):
    for pitch in cfg.pitch.candidates_mm:
        report = check_corridor(cfg, pitch)
        assert report.ok, f"corridor constraint violated at p={pitch}: " + ", ".join(
            f"{v.a.value}+{v.b.value} margin {v.margin_mm:.2f} mm < budget {report.budget_mm} mm"
            for v in report.violations()
        )


@pytest.mark.parametrize(
    ("pitch", "expected_worst_mm"),
    [(40.0, 2.0), (50.0, 2.5)],
)
def test_worst_pair_is_heavy_heavy_with_expected_margin(cfg, pitch, expected_worst_mm):
    report = check_corridor(cfg, pitch)
    heavy = {PieceType.ROOK, PieceType.QUEEN, PieceType.KING}
    assert report.worst.a in heavy and report.worst.b in heavy
    assert report.worst.margin_mm == pytest.approx(expected_worst_mm, abs=1e-9)


def test_margin_formula_matches_brief(cfg):
    # Two pawns at p = 40: 20 - 2 * 7 = 6 mm of corridor margin.
    margin = corridor_margin_mm(cfg, PieceType.PAWN, PieceType.PAWN, 40.0)
    assert margin == pytest.approx(6.0, abs=1e-9)


def test_pair_count_covers_all_type_combinations(cfg):
    report = check_corridor(cfg, cfg.pitch.candidates_mm[0])
    assert len(report.pairs) == 21  # 6 types, unordered pairs with repetition


def test_guard_fires_on_oversized_bases(raw_config_dict):
    raw_config_dict["pieces"]["classes"]["king"]["base_ratio"] = 0.55
    mutated = BoardConfig.model_validate(raw_config_dict)
    for pitch in mutated.pitch.candidates_mm:
        report = check_corridor(mutated, pitch)
        assert not report.ok
        violating = {(v.a, v.b) for v in report.violations()}
        assert (PieceType.KING, PieceType.KING) in violating
