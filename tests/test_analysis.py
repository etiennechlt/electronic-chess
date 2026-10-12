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


# ---------------------------------------------------------------------------
# Hall + RFID mockup (note 25): M12 to M14 on synthetic data
# ---------------------------------------------------------------------------

import dataclasses  # noqa: E402
import math  # noqa: E402

import numpy as np  # noqa: E402
from analysis import (  # noqa: E402
    ChainRow,
    CohabRow,
    FlatnessRow,
    HallRow,
    PickupRow,
    RfidRow,
    TxStateRow,
    binomial_upper_bound,
    cluster_sensor_offsets_mm,
    counts_to_mT,
    crossing_radius_mm,
    differential_z_from_one_port,
    differential_z_from_s,
    field_from_pickup,
    field_margin_from_gap,
    flatness,
    grid_covered_half_side_mm,
    hall_scale,
    load_chain_csv,
    load_cohab_csv,
    load_flatness_csv,
    load_hall_csv,
    load_pickup_csv,
    load_rfid_csv,
    load_touchstone,
    load_tx_state_csv,
    m12a_fit_rows,
    m12a_scale_factor,
    m12b_cluster_coverage,
    m12b_detection_radius,
    m12c_presence,
    m13a_activation_threshold,
    m13a_thresholds,
    match_frequency_hz,
    mean_shift,
    min_safe_distance,
    mockup_criteria,
    pooled_std,
    r_drive_from_tvdd,
    radii_by_direction,
    read_summary,
    resonance_q,
    rx_amplitude_vpp,
    settling_time_us,
    tag_variants,
)
from scipy.optimize import brentq  # noqa: E402

from chessboard_calc import nfc  # noqa: E402
from chessboard_calc.config import PieceType, resolve_geometry  # noqa: E402
from chessboard_calc.hall import disc_bz_mT, hall_budget, piece_bz_mT  # noqa: E402

TEMPLATES = Path(__file__).resolve().parents[1] / "measurements" / "data" / "templates"


def _hall_row(scale, field_mT, zero=2000.0, **kw):
    """A HallRow whose counts encode field_mT through the scale."""
    base = dict(test="m12a", square="A1", sensor="A1", path="direct", piece="pawn1",
                magnet_id="m1", magnet_d_mm=12.0, magnet_t_mm=4.0, grade="Y30", lift_mm=0.0,
                z_mm=7.0, x_mm=0.0, y_mm=0.0, n_samples=256, mean_counts=0.0,
                std_counts=3.0, zero_counts=zero, rail_half_counts=math.nan)
    base.update(kw)
    counts = zero + field_mT * scale.sensitivity_mv_per_mt / scale.lsb_mv
    return HallRow(**{**base, "mean_counts": counts})


@pytest.mark.parametrize(
    ("name", "loader", "cls"),
    [
        ("m12_hall.csv", load_hall_csv, HallRow),
        ("m12d_chaine.csv", load_chain_csv, ChainRow),
        ("m12_planeite.csv", load_flatness_csv, FlatnessRow),
        ("m13_rfid.csv", load_rfid_csv, RfidRow),
        ("m13b_etats_tx.csv", load_tx_state_csv, TxStateRow),
        ("m13_vignette.csv", load_pickup_csv, PickupRow),
        ("m14_cohabitation.csv", load_cohab_csv, CohabRow),
    ],
)
def test_each_mockup_template_parses_with_its_loader(name, loader, cls):
    path = TEMPLATES / name
    header = path.read_text(encoding="utf-8").splitlines()[0].split(",")
    assert header == [f.name for f in dataclasses.fields(cls)]
    rows = loader(path)
    assert len(rows) == 1 and isinstance(rows[0], cls)


def test_tag_variants_follow_the_trims_and_name_the_template_examples(cfg):
    trims = cfg.hall_rfid.mockup.tags.trims_pF
    names = tag_variants(cfg)
    assert len(names) == len(set(names)) == sum(len(v) for v in trims.values())
    for size, values in trims.items():
        if 0.0 in values:
            assert f"{size}0" in names
    known = set(names) | {"MURATA", "REF"}
    assert load_rfid_csv(TEMPLATES / "m13_rfid.csv")[0].variant in known
    assert load_cohab_csv(TEMPLATES / "m14_cohabitation.csv")[0].variant in known


def test_loader_reads_hex_registers_and_empty_cells_and_refuses_missing_columns(tmp_path):
    rows = load_cohab_csv(TEMPLATES / "m14_cohabitation.csv")
    assert rows[0].cwgsp == 0x20 and rows[0].trials == -1 and math.isnan(rows[0].distance_mm)
    bad = tmp_path / "bad.csv"
    bad.write_text("# comment\nx_mm,y_mm\n0,0\n", encoding="utf-8")
    with pytest.raises(ValueError, match="h_mm"):
        load_flatness_csv(bad)


def test_mockup_criteria_come_from_the_yaml(cfg):
    crit = mockup_criteria(cfg)
    assert crit.pitch_mm == cfg.pitch.mockup_mm
    assert crit.z_max_mm - crit.z_nominal_mm == pytest.approx(crit.max_gap_shim_mm)
    assert crit.max_gap_shim_mm == pytest.approx(cfg.gap.max_total_mm - cfg.gap.nominal_total_mm)
    assert crit.max_detune_rel == pytest.approx(0.5 / cfg.hall_rfid.mockup.matching.q_loaded)
    assert crit.model_threshold_mT == pytest.approx(hall_budget(cfg, crit.pitch_mm).threshold_mT)
    offsets = cluster_sensor_offsets_mm(cfg)
    a = cfg.hall_rfid.mockup.hall.cluster_offset_ratio * crit.pitch_mm
    assert len(offsets) == 1 + len(cfg.hall_rfid.mockup.mux_channels.cluster)
    assert sorted(set(abs(v) for xy in offsets.values() for v in xy)) == [0.0, pytest.approx(a)]


def test_mockup_criteria_return_the_yaml_criteria_and_feed_the_defaults(cfg):
    crit = mockup_criteria(cfg)
    yaml_crit = cfg.hall_rfid.mockup.criteria
    for name in type(yaml_crit).model_fields:
        assert getattr(crit, name) == getattr(yaml_crit, name), name
    # the statistical functions take their defaults from those keys
    n = yaml_crit.read_trials
    assert binomial_upper_bound(0, n) == binomial_upper_bound(0, n, yaml_crit.confidence)
    levels, trials = [3.0, 2.0, 1.0], [n, n, n]
    succ = [n, n, math.floor(yaml_crit.read_target_rate * n) - 1]
    assert m13a_activation_threshold(levels, trials, succ).level == 2.0


def test_counts_to_mT_inverts_the_sensor_and_follows_the_rail(cfg):
    scale = hall_scale(cfg)
    b = np.array([-0.2, 3.0, 25.0])
    zero, rail_ref = 2180.0, 2179.0
    counts = zero + b * scale.sensitivity_mv_per_mt / scale.lsb_mv
    assert counts_to_mT(counts, zero, scale) == pytest.approx(b)
    # rail 2 % high: zero and sensitivity both follow it (ratiometric)
    r = 1.02
    counts_r = zero * r + b * scale.sensitivity_mv_per_mt * r / scale.lsb_mv
    assert counts_to_mT(counts_r, zero, scale, rail_ref * r, rail_ref) == pytest.approx(b)


def test_m12a_recovers_the_scale_factor_on_the_lift_staircase(cfg):
    crit = mockup_criteria(cfg)
    scale = hall_scale(cfg)
    br = cfg.piece_magnet.br_T
    prints = cfg.hall_rfid.mockup.prints
    rng = np.random.default_rng(1)
    k_true = {"pawn": 0.92, "king": 1.07}
    rows = []
    for mid, d in (("pawn", 12.04), ("king", 17.96)):
        for lift in np.arange(0.0, prints.lift_max_mm + 1e-9, prints.lift_step_mm):
            z = crit.z_nominal_mm + lift + rng.normal(0.0, 0.02)  # caliper reading
            b = k_true[mid] * disc_bz_mT(br, d / 2.0, 3.98, z) * (1 + rng.normal(0.0, 0.005))
            rows.append(_hall_row(scale, b, magnet_id=mid, magnet_d_mm=d, magnet_t_mm=3.98,
                                  lift_mm=float(lift), z_mm=z))
    # beyond the residual window a point may be far off: it must not count
    rows.append(_hall_row(scale, 50.0, magnet_id="pawn", magnet_d_mm=12.04, magnet_t_mm=3.98,
                          lift_mm=prints.lift_max_mm + 1.0, z_mm=crit.z_nominal_mm + 21.0))
    fits = m12a_fit_rows(rows, scale, br, max_lift_mm=crit.lift_detect_mm)
    for mid, k in k_true.items():
        assert fits[mid].factor == pytest.approx(k, rel=0.01)
        assert 0.0 < fits[mid].factor_sigma < 0.01
        assert fits[mid].max_residual < 0.03
        assert fits[mid].n == int(crit.lift_detect_mm / prints.lift_step_mm) + 1


def test_m12a_scale_factor_weighs_every_point_alike():
    # 20 % high on a weak point, exact on a strong one: the factor is the
    # mean ratio, not the strong point's least-squares verdict
    fit = m12a_scale_factor([10.0, 1.2], [10.0, 1.0])
    assert fit.factor == pytest.approx(1.1)
    assert fit.max_residual == pytest.approx(1.2 / 1.1 - 1.0)
    # standard error of the mean ratio: sample deviation over the root of n
    assert fit.factor_sigma == pytest.approx(np.std([1.0, 1.2], ddof=1) / math.sqrt(2.0))


def _pawn_profile(cfg):
    """Field of the pawn at the maximum stack against offset, and the threshold
    the firmware would set from the centred reading."""
    crit = mockup_criteria(cfg)
    geo = resolve_geometry(cfg, crit.pitch_mm)
    r = geo.classes[PieceType.PAWN].magnet_d_mm / 2.0
    t = cfg.piece_magnet.thickness_mm

    def field(rho):
        return disc_bz_mT(cfg.piece_magnet.br_T, r, t, crit.z_max_mm, rho)

    return field, crit.threshold_fraction * field(0.0)


def test_detection_radius_interpolates_to_half_a_millimetre(cfg):
    field, thr = _pawn_profile(cfg)
    prints = cfg.hall_rfid.mockup.prints
    rho = np.arange(0.0, prints.offset_max_mm + 1e-9, prints.offset_step_mm)
    exact = brentq(lambda r: field(r) - thr, 0.0, prints.offset_max_mm)
    got = crossing_radius_mm(rho, [field(r) for r in rho], thr)
    assert got == pytest.approx(exact, abs=0.5)
    assert crossing_radius_mm(rho, [field(r) for r in rho], 2 * field(0.0)) == 0.0
    assert crossing_radius_mm(rho, [field(r) for r in rho], -1.0) == math.inf
    # the same profile on four rays and the diagonal
    xs, ys, fs = [0.0], [0.0], [field(0.0)]
    for ux, uy in ((1, 0), (0, 1), (-1, 0), (0, -1), (1, 1)):
        for s in rho[1:]:
            xs.append(ux * s)
            ys.append(uy * s)
            fs.append(field(math.hypot(ux * s, uy * s)))
    radii = radii_by_direction(xs, ys, fs, thr)
    assert set(radii) == {0, 45, 90, 180, 270}
    assert all(v == pytest.approx(exact, abs=0.5) for v in radii.values())


def _cluster_rows(cfg, scale, field, sensors, step):
    prints = cfg.hall_rfid.mockup.prints
    grid = np.arange(0.0, prints.offset_max_mm + 1e-9, step)
    rows = []
    for x in grid:
        for y in grid:
            for name, (sx, sy) in sensors.items():
                b = field(math.hypot(x - sx, y - sy))
                rows.append(_hall_row(scale, b, test="m12b", sensor=name,
                                      path="direct" if name == "A1" else "mux",
                                      x_mm=float(x), y_mm=float(y)))
    return rows


def test_m12b_rows_give_the_radius_and_the_cluster_coverage(cfg):
    scale = hall_scale(cfg)
    field, thr = _pawn_profile(cfg)
    sensors = cluster_sensor_offsets_mm(cfg)
    prints = cfg.hall_rfid.mockup.prints
    exact_r = brentq(lambda r: field(r) - thr, 0.0, prints.offset_max_mm)
    rows = _cluster_rows(cfg, scale, field, sensors, prints.offset_step_mm)
    centre = cfg.hall_rfid.mockup.hall.cluster_square
    radii = m12b_detection_radius(rows, scale, thr, centre, directions=(0, 45, 90, 180))
    assert set(radii) == {0, 45, 90}   # one quadrant of the jig: no -x ray
    assert all(v == pytest.approx(exact_r, abs=0.5) for v in radii.values())
    # one centred sensor covers the square inscribed in its detection disc
    single = m12b_cluster_coverage(rows, scale, thr, [centre])
    assert single == pytest.approx(exact_r / math.sqrt(2.0), abs=0.3)
    # the cluster: against the same grid method on a fine grid
    coarse = m12b_cluster_coverage(rows, scale, thr, sensors)
    fine_step = prints.offset_step_mm / 8.0
    grid = np.arange(0.0, prints.offset_max_mm + 1e-9, fine_step)
    gx, gy = np.meshgrid(grid, grid)
    margin = np.max([np.vectorize(field)(np.hypot(gx - sx, gy - sy))
                     for sx, sy in sensors.values()], axis=0) - thr
    fine = grid_covered_half_side_mm(gx.ravel(), gy.ravel(), margin.ravel())
    assert coarse == pytest.approx(fine, abs=0.5)
    assert coarse > single + 2.0


def test_grid_coverage_edge_cases():
    xs, ys = [0.0, 2.0, 0.0, 2.0], [0.0, 0.0, 2.0, 2.0]
    assert grid_covered_half_side_mm(xs, ys, [1.0, 1.0, 1.0, 1.0]) == math.inf
    assert grid_covered_half_side_mm(xs, ys, [-1.0, 1.0, 1.0, 1.0]) == 0.0
    # only the corner fails, halfway in margin: the diagonal crossing at 1 mm
    assert grid_covered_half_side_mm(xs, ys, [1.0, 1.0, 1.0, -1.0]) == pytest.approx(1.0)


def test_m12c_presence_reproduces_the_hall_budget_on_model_fields(cfg):
    crit = mockup_criteria(cfg)
    p = crit.pitch_mm
    budget = hall_budget(cfg, p)
    z_lift = crit.z_nominal_mm + crit.lift_detect_mm
    rep = m12c_presence(
        weakest_mT=budget.weakest_present_mT,
        lifted_mT=piece_bz_mT(cfg, PieceType.KING, p, z_lift),
        side_mT=piece_bz_mT(cfg, PieceType.KING, p, crit.z_nominal_mm, rho_mm=p),
        diag_mT=piece_bz_mT(cfg, PieceType.KING, p, crit.z_nominal_mm, rho_mm=p * math.sqrt(2)),
        threshold_fraction=crit.threshold_fraction,
        hysteresis_fraction=crit.hysteresis_fraction,
        neighbors=crit.neighbors,
    )
    assert rep.threshold_mT == pytest.approx(budget.threshold_mT)
    assert rep.release_mT == pytest.approx(budget.release_mT)
    assert rep.lift_margin == pytest.approx(budget.lift_margin)
    assert rep.neighbors_mT == pytest.approx(budget.neighbors_sum_mT)
    assert rep.crosstalk_db == pytest.approx(budget.crosstalk_db)


def test_neighbour_field_by_difference_and_pooled_noise():
    rng = np.random.default_rng(2)
    n, sigma, delta = 256, 3.0, -0.3
    a = rng.normal(2180.0, sigma, n)
    b = rng.normal(2180.0 + delta, sigma, n)
    shift, err = mean_shift(a.mean(), a.std(ddof=1), n, b.mean(), b.std(ddof=1), n)
    assert err == pytest.approx(sigma * math.sqrt(2.0 / n), rel=0.15)
    assert abs(shift - delta) < 4.0 * err
    assert pooled_std([2.0, 2.0, 4.0], [10, 10, 10]) == pytest.approx(math.sqrt(8.0))


def test_settling_time_of_an_exponential_step():
    tau, amp, tol = 30.0, 11.0, 1.0
    d = np.arange(0.0, 400.0, 5.0)
    v = 2180.0 + amp * np.exp(-d / tau)
    got = settling_time_us(d, v, tol)
    assert got == pytest.approx(tau * math.log(amp / tol), abs=5.0)
    assert settling_time_us(d, v, tol, final_counts=2170.0) == math.inf
    assert settling_time_us(d, np.full_like(d, 2180.0), tol) == 0.0


def test_flatness_removes_the_plane():
    rows = []
    for x in (-25.0, 0.0, 25.0):
        for y in (-25.0, 0.0, 25.0):
            bump = 0.1 if (x, y) == (0.0, 0.0) else 0.0
            rows.append(FlatnessRow(x, y, 5.5 + 0.004 * x - 0.002 * y + bump))
    f = flatness(rows)
    assert f.pv_mm == pytest.approx(0.004 * 50 + 0.002 * 50, abs=0.11)
    assert f.residual_pv_mm == pytest.approx(0.1, rel=0.01)
    assert f.slope == pytest.approx(math.hypot(0.004, 0.002), rel=0.05)


def test_binomial_bounds_follow_the_rule_of_three():
    assert binomial_upper_bound(0, 100, 0.95) == pytest.approx(0.0295, abs=0.0005)
    assert binomial_upper_bound(0, 300, 0.95) == pytest.approx(0.00994, abs=0.0002)
    assert binomial_upper_bound(0, 100, confidence=0.95) < 3.0 / 100
    assert binomial_upper_bound(5, 100, 0.95) > 0.05
    assert binomial_upper_bound(100, 100) == 1.0


def test_activation_threshold_recovers_the_field_where_reads_become_certain():
    rng = np.random.default_rng(3)
    h50, width, n = 0.80, 0.03, 100   # A/m: logistic read probability
    levels = np.arange(0.5, 2.0, 0.05)
    p = 1.0 / (1.0 + np.exp(-(levels - h50) / width))
    succ = rng.binomial(n, p)
    th = m13a_activation_threshold(levels, [n] * len(levels), succ, 1.0, 0.95)
    # where p reaches 1 - 1/(10 n) or so, and above the 50 % point
    assert h50 < th.level < h50 + 10 * width
    assert th.failing_level == pytest.approx(th.level - 0.05)
    assert th.successes == th.trials == n
    assert th.fail_high == pytest.approx(binomial_upper_bound(0, n, 0.95))
    # a lucky full series below the first miss does not count
    lv, tr, sc = [2.0, 1.5, 1.0, 0.9], [100] * 4, [100, 100, 98, 100]
    assert m13a_activation_threshold(lv, tr, sc, 1.0).level == 1.5
    # gap as the level: larger is harder
    gaps = [6.4, 8.4, 10.4, 12.4]
    th_gap = m13a_activation_threshold(gaps, tr, [100, 100, 100, 40], 1.0,
                                       higher_is_easier=False)
    assert th_gap.level == 10.4 and th_gap.failing_level == 12.4
    nothing = m13a_activation_threshold([1.0], [100], [50], 1.0)
    assert math.isnan(nothing.level) and nothing.failing_level == 1.0


def test_activation_threshold_refuses_a_reading_outside_the_calibration():
    lv, tr, sc = [math.nan, 3.5, 2.5, 1.5, 1.2], [100] * 5, [100, 100, 100, 100, 90]
    with pytest.raises(ValueError, match="A1/P-07.*calibration table"):
        m13a_activation_threshold(lv, tr, sc, 1.0, series="A1/P-07")
    assert m13a_activation_threshold(lv[1:], tr[1:], sc[1:], 1.0).level == 1.5
    # through the rows: a field tag reading beyond the table names its group
    cal = [PickupRow(0.0, 0.0, "x"), PickupRow(500.0, 5.0, "x")]
    rows = [RfidRow("m13a", "A1", "L60x3", "NXP", "P-07", "P0", "A1", 6.4, 0.0, 0.0, "held",
                    0x20, 0x8, 100, 100, 40.0, mv, 6.0, 7.0) for mv in (600.0, 300.0)]
    with pytest.raises(ValueError, match="P-07"):
        m13a_thresholds(rows, 1.0, cal)


def test_field_tag_calibration_and_margins():
    cal = [PickupRow(100.0, 1.0, "nanovna"), PickupRow(300.0, 4.0, "nanovna"),
           PickupRow(200.0, 2.0, "nanovna")]
    assert field_from_pickup(150.0, cal) == pytest.approx(1.5)
    assert field_from_pickup(np.array([250.0]), cal) == pytest.approx([3.0])
    assert math.isnan(field_from_pickup(400.0, cal))

    # on-axis field of a circular loop at constant current: the gap method
    a = 15.0

    def h(z):
        return a * a / (2.0 * (a * a + z * z) ** 1.5)

    assert field_margin_from_gap(12.0, 6.4, h) == pytest.approx(h(6.4) / h(12.0))
    assert field_margin_from_gap(12.0, 6.4, h) > 1.0


def test_m13a_rows_and_read_summary():
    def row(level_mv, succ, square="A1", test="m13a", tag_square="A1"):
        return RfidRow(test, square, "L60x3", "NXP", "P-07", "P0", tag_square, 6.4, 0.0, 0.0,
                       "held", 0x20, 0x8, 100, succ, 40.0, level_mv, 6.0, 7.0)

    cal = [PickupRow(0.0, 0.0, "x"), PickupRow(1000.0, 10.0, "x")]
    rows = [row(600.0, 100), row(400.0, 100), row(300.0, 97), row(200.0, 0),
            row(600.0, 0, test="m13b", tag_square="B1")]
    th = m13a_thresholds(rows, 1.0, cal)
    assert list(th) == [("A1", "P-07", 6.4, 0.0, 0.0)]
    assert th[("A1", "P-07", 6.4, 0.0, 0.0)].level == pytest.approx(4.0)
    stats = read_summary(rows, ("test", "tag_square"))
    stray = stats[("m13b", "B1")]
    assert stray.successes == 0 and stray.read_high == pytest.approx(binomial_upper_bound(0, 100))
    assert stats[("m13a", "A1")].trials == 400


def _ladder_z(f, l0, c0, c1, c2, rq, l_loop, r_loop, asym=1.0):
    """2 x 2 impedance matrix, at the two half-network inputs, of the
    symmetric matching network: per side L0 in series, C0 to ground, C1 in
    series, C2 to ground, Rq, then the loop between the two sides. asym
    scales the C2 of side 2 (component tolerance)."""
    w = 2.0 * math.pi * f
    nodes = ["in1", "n1", "m1", "e1", "e2", "m2", "n2", "in2"]
    idx = {n: i for i, n in enumerate(nodes)}
    y = np.zeros((8, 8), dtype=complex)

    def series(a, b, z):
        ia, ib = idx[a], idx[b]
        y[ia, ia] += 1 / z
        y[ib, ib] += 1 / z
        y[ia, ib] -= 1 / z
        y[ib, ia] -= 1 / z

    def shunt(a, z):
        y[idx[a], idx[a]] += 1 / z

    for s, k in (("1", 1.0), ("2", asym)):
        series(f"in{s}", f"n{s}", 1j * w * l0 + w * l0 / 30.0)
        shunt(f"n{s}", 1 / (1j * w * c0))
        series(f"n{s}", f"m{s}", 1 / (1j * w * c1))
        shunt(f"m{s}", 1 / (1j * w * c2 * k))
        series(f"m{s}", f"e{s}", rq)
    series("e1", "e2", 1j * w * l_loop + r_loop)
    ports, inner = [0, 7], list(range(1, 7))
    ypp = y[np.ix_(ports, ports)] - y[np.ix_(ports, inner)] @ np.linalg.solve(
        y[np.ix_(inner, inner)], y[np.ix_(inner, ports)])
    return np.linalg.inv(ypp)


@pytest.mark.parametrize("asym", [1.0, 1.02])
def test_nanovna_methods_recover_the_differential_impedance(asym):
    f = np.linspace(12.5e6, 14.5e6, 201)
    zmat = np.array([_ladder_z(fi, 560e-9, 220e-12, 85e-12, 750e-12, 0.5, 0.34e-6, 0.4, asym)
                     for fi in f])
    z11, z12, z21, z22 = zmat[:, 0, 0], zmat[:, 0, 1], zmat[:, 1, 0], zmat[:, 1, 1]
    zdiff = z11 + z22 - z12 - z21
    # two-port sweep (balun-free mixed-mode conversion)
    z0 = 50.0
    eye = np.eye(2)
    s = np.array([(zm - z0 * eye) @ np.linalg.inv(zm + z0 * eye) for zm in zmat])
    got_s = differential_z_from_s(s[:, 0, 0], s[:, 1, 0], s[:, 1, 1], s[:, 0, 1], z0)
    assert np.allclose(got_s, zdiff, rtol=1e-9)
    # one-port: other input open, then grounded
    z_grounded = z11 - z12 * z21 / z22
    got_1 = differential_z_from_one_port(z11, z_grounded, z22)
    near = np.abs(f - 13.56e6) < 0.5e6
    assert np.allclose(got_1[near], zdiff[near], rtol=1e-6)
    # the grounded half alone is not half the differential impedance
    k = int(np.argmin(np.abs(f - 13.56e6)))
    assert abs(z_grounded[k] - zdiff[k] / 2.0) > 0.3 * abs(zdiff[k] / 2.0)
    # the match frequency moves with a detuned network
    f_match = match_frequency_hz(f, zdiff, abs(zdiff[k]))
    assert 12.5e6 < f_match < 14.5e6


def test_drive_resistance_inverts_the_nfc_source_model(cfg):
    v = cfg.hall_rfid.mockup.power.regulator.v_out
    z, r = complex(48.0, 6.0), 2.5
    i_ma = 8.0 * v / (math.pi**2 * abs(2.0 * r + z)) * 1e3
    assert r_drive_from_tvdd(i_ma + 7.0, z, v, i_tvdd_off_ma=7.0) == pytest.approx(r)
    assert math.isnan(r_drive_from_tvdd(10.0 * i_ma, z, v))
    # the same relation as chessboard_calc.nfc: its matched network and TVDD
    # current give back the drive resistance of the yaml
    for loop in cfg.hall_rfid.mockup.loops:
        mt = nfc.matching(cfg, cfg.pitch.mockup_mm, loop)
        assert r_drive_from_tvdd(mt.i_tvdd_ma, mt.z_ohm, v) == pytest.approx(
            cfg.hall_rfid.mockup.reader.r_drive_ohm, rel=1e-6)


def test_rx_amplitude_scales_the_model_by_the_divider_and_the_current():
    got = rx_amplitude_vpp(0.02 + 0.01j, 0.1 + 0.05j, 7.5, 45.0, 50.0)
    assert got == pytest.approx(0.2 * 7.5 * 0.9)


def test_resonance_q_of_a_lorentzian():
    f0, q = 13.56e6, 24.0
    f = np.linspace(12.0e6, 15.0e6, 301)
    mag = 1.0 / np.sqrt(1.0 + (2.0 * q * (f - f0) / f0) ** 2)
    got_f0, got_q = resonance_q(f, mag)
    assert got_f0 == pytest.approx(f0, rel=1e-3)
    assert got_q == pytest.approx(q, rel=0.02)


def test_touchstone_one_and_two_ports(tmp_path):
    s1 = tmp_path / "a.s1p"
    s1.write_text("! NanoVNA\n# MHz S RI R 50\n13.0 0.5 -0.25\n13.5 0.1 0.0\n",
                  encoding="utf-8")
    f, s, z0 = load_touchstone(s1)
    assert f.tolist() == [13.0e6, 13.5e6] and z0 == 50.0
    assert s[0] == pytest.approx(0.5 - 0.25j)
    s2 = tmp_path / "b.s2p"
    s2.write_text("# Hz S DB R 50\n13560000 -6.0206 0 -20 90 -20 90 -40 180\n",
                  encoding="utf-8")
    f, s, _ = load_touchstone(s2)
    assert s.shape == (1, 2, 2)
    assert s[0, 0, 0] == pytest.approx(0.5, rel=1e-4)
    assert s[0, 1, 0] == pytest.approx(0.1j, rel=1e-6)    # S21, second pair of the line
    assert s[0, 1, 1] == pytest.approx(-0.01, rel=1e-6)


def test_min_safe_distance_needs_every_farther_point():
    d = [5.0, 10.0, 20.0, 30.0, 20.0]
    assert min_safe_distance(d, [False, True, True, True, True]) == 10.0
    assert min_safe_distance(d, [True, False, True, True, True]) == 20.0
    assert min_safe_distance(d, [True, True, True, True, False]) == 30.0
    assert math.isnan(min_safe_distance(d, [True, True, True, False, True]))
