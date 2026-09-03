"""The measurement analysis pipeline against synthetic ringdowns."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "measurements"))

from analysis import (  # noqa: E402
    ScanRow,
    ab_compare,
    crosstalk_db,
    dispersion_pct,
    q_from_ringdown,
    q_from_spectrum,
    synth_ringdown,
)

FS = 3_780_000.0


@pytest.mark.parametrize(("f0", "q"), [(217e3, 35.0), (288e3, 50.0), (413e3, 60.0)])
def test_q_extraction_within_15_percent(f0, q):
    samples = synth_ringdown(f0, q, FS)
    f_env, q_env = q_from_ringdown(samples, FS)
    f_spec, q_spec = q_from_spectrum(samples, FS)
    assert f_env == pytest.approx(f0, rel=0.02)
    assert f_spec == pytest.approx(f0, rel=0.05)
    assert q_env == pytest.approx(q, rel=0.15)
    # 512 samples cannot resolve the true linewidth: the spectral value
    # only lower-bounds Q (window mainlobe limited).
    assert q_spec < q * 1.1


def test_crosstalk_and_dispersion_helpers():
    assert crosstalk_db(1000.0, 100.0) == pytest.approx(-20.0)
    assert dispersion_pct([217000, 219000, 221000, 223000]) == pytest.approx(
        (223000 - 217000) / 220000 * 100 / 2, rel=0.05
    )


def test_ab_compare_reports_bias_and_validity():
    rows = [
        ScanRow(1, 217000, 217150, 500, 40),
        ScanRow(1, 217020, 217180, 500, 40),
        ScanRow(1, 217010, 0, 500, 10),
    ]
    rep = ab_compare(rows)
    assert rep.n == 3 and rep.n_b_valid == 2
    assert rep.bias_hz == pytest.approx(155.0, abs=1.0)
