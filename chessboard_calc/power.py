"""Power budget, autonomy and peak current.

Loss model: a fixed conversion overhead (forced-PWM buck no-load loss,
BMS and gauge quiescent) plus a proportional regulation loss. The fixed
term reconciles the brief's 0.9 W idle total, whose line items alone
sum to 0.5 W.
"""

from __future__ import annotations

from dataclasses import dataclass

from .config import BoardConfig


@dataclass(frozen=True)
class PowerBudget:
    engine_on: bool
    loads_w: dict[str, float]
    load_sum_w: float
    fixed_overhead_w: float
    proportional_loss_w: float
    total_w: float


def _budget(cfg: BoardConfig, loads: dict[str, float], engine_on: bool) -> PowerBudget:
    load_sum = sum(loads.values())
    proportional = load_sum * cfg.power.regulation_loss_pct / 100.0
    fixed = cfg.power.fixed_overhead_w
    return PowerBudget(
        engine_on=engine_on,
        loads_w=loads,
        load_sum_w=load_sum,
        fixed_overhead_w=fixed,
        proportional_loss_w=proportional,
        total_w=load_sum + proportional + fixed,
    )


def power_budget(cfg: BoardConfig, engine_on: bool) -> PowerBudget:
    lw = cfg.power.loads_w
    loads = {"stm32_analog": lw.stm32_analog, "ui_idle": lw.ui_idle}
    if engine_on:
        loads.update({"pi": lw.pi, "tft": lw.tft, "motors_avg": lw.motors_avg})
    return _budget(cfg, loads, engine_on)


def autonomy_h(cfg: BoardConfig, engine_on: bool) -> float:
    usable_wh = cfg.power.battery.energy_wh * cfg.power.battery.usable_fraction
    return usable_wh / power_budget(cfg, engine_on).total_w


def peak_power_w(cfg: BoardConfig) -> float:
    lw = cfg.power.loads_w
    loads = {
        "stm32_analog": lw.stm32_analog,
        "ui_idle": lw.ui_idle,
        "pi": lw.pi,
        "tft": lw.tft,
        "motors_peak": lw.motors_peak,
    }
    return _budget(cfg, loads, engine_on=True).total_w


def peak_current_a(cfg: BoardConfig, v_bus: float | None = None) -> float:
    if v_bus is None:
        v_lo, v_hi = cfg.power.battery.v_range
        v_bus = (v_lo + v_hi) / 2.0  # 3S NMC nominal
    return peak_power_w(cfg) / v_bus
