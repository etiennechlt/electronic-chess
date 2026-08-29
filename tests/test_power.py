"""Power budget and autonomy pinned against the brief within model tolerance."""

import pytest

from chessboard_calc.power import autonomy_h, peak_current_a, peak_power_w, power_budget


def test_idle_budget_matches_brief(cfg):
    # Brief 3.10: 0.9 W human vs human with the Pi off. The explicit
    # fixed-overhead model lands at ~0.87 W.
    budget = power_budget(cfg, engine_on=False)
    assert 0.8 <= budget.total_w <= 1.0
    assert "pi" not in budget.loads_w and "tft" not in budget.loads_w


def test_engine_budget_matches_brief_within_model_tolerance(cfg):
    # Brief 3.10 says 3.6 W; adding the fixed overhead it did not carry
    # in this column lands at ~4.0 W, within 20 %.
    budget = power_budget(cfg, engine_on=True)
    assert 3.5 <= budget.total_w <= 4.4
    assert {"pi", "tft", "motors_avg"} <= set(budget.loads_w)


def test_autonomy_matches_brief(cfg):
    assert 60.0 <= autonomy_h(cfg, engine_on=False) <= 75.0  # brief: 65 h
    assert 13.0 <= autonomy_h(cfg, engine_on=True) <= 17.0  # brief: 17 h


def test_peak_power_and_current_match_brief(cfg):
    # Brief 3.10: ~12 W peak, ~1.1 A at 11 V.
    assert 11.0 <= peak_power_w(cfg) <= 12.5
    assert peak_current_a(cfg) == pytest.approx(1.1, abs=0.15)
    assert peak_current_a(cfg, v_bus=11.0) == pytest.approx(1.1, abs=0.15)


def test_usable_energy_derate_is_explicit(cfg):
    # The brief's 65 h figure implies ~80 % usable energy; the config
    # carries it explicitly instead of leaving it implicit.
    assert cfg.power.battery.usable_fraction == pytest.approx(0.80)


def test_move_reserve_is_sane(cfg):
    assert 0.0 < cfg.power.move_reserve_pct < 50.0
