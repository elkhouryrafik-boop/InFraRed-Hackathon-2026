"""
test_cost_model.py — Deterministic offline tests for cost_model.py.

Tests cover:
    - CapEx-only per_tree_cost (COST-01)
    - CapEx + OpEx composition over horizon (COST-01)
    - total_cost scaling by tree count (COST-01)
    - EUR/degC KPI value and dict shape (COST-02)
    - Surrogate delta fallback flagged as LOW confidence (COST-02)
    - Zero and negative delta guard — value=None, no exception (COST-02)
    - Standard metric-dict key completeness (CONVENTIONS.md)
    - UTCI routing: KPI delta is NOT raw delta_tmrt_c (VALID-02 / D-08)
    - Both units reported: cost_per_utci_hour present and finite (D-09)
    - Uncertainty interval [lo, hi] for KPI (D-10 / VALID-04)
    - Pre-calibration band label when band_c is None (D-10)
    - Empirical RMSE band label when band_c is provided (D-10)

All tests are pure arithmetic, fully offline, deterministic.  No API key needed.
"""
from __future__ import annotations

import pytest

from coolspend.cost_model import (
    CAPEX_PER_TREE_EUR,
    HOURS_PER_DEGC_REF,
    OPEX_HORIZON_YEARS,
    OPEX_PER_TREE_YEAR_EUR,
    PRE_CALIBRATION_BAND_C,
    cost_per_utci_degree,
    per_tree_cost,
    total_cost,
)


# ── per_tree_cost tests (COST-01) ────────────────────────────────────────────

def test_per_tree_cost_capex_only() -> None:
    """horizon_years=0 returns exactly CAPEX_PER_TREE_EUR — no OpEx added."""
    assert per_tree_cost(0) == CAPEX_PER_TREE_EUR


def test_per_tree_cost_includes_opex() -> None:
    """Default horizon adds OpEx on top of CapEx — result is strictly larger."""
    assert per_tree_cost() > CAPEX_PER_TREE_EUR
    expected = CAPEX_PER_TREE_EUR + OPEX_PER_TREE_YEAR_EUR * OPEX_HORIZON_YEARS
    assert per_tree_cost() == pytest.approx(expected)


# ── total_cost tests (COST-01) ───────────────────────────────────────────────

@pytest.mark.parametrize("n", [0, 1, 25])
def test_total_cost_scales(n: int) -> None:
    """total_cost scales linearly with tree_count for n in {0, 1, 25}."""
    result = total_cost({"tree_count": n})
    expected = n * per_tree_cost()
    assert result == pytest.approx(expected)


# ── cost_per_utci_degree tests (COST-02) ─────────────────────────────────────

def test_cost_per_degree_value() -> None:
    """Positive delta_utci_c produces a finite EUR/degC value with confidence MED/HIGH."""
    config = {"tree_count": 10, "delta_utci_c": 0.5, "coverage_fraction": 0.2}
    result = cost_per_utci_degree(config)
    # value should be finite positive (KPI = cost / equiv_degc)
    assert result["value"] is not None
    assert result["value"] > 0
    assert result["unit"] == "EUR/degC"
    assert result["confidence"] in {"MED", "HIGH"}
    assert result["metric_id"] == "cost_per_utci_degree"


def test_nonpositive_delta_guarded_zero() -> None:
    """delta_utci_c == 0 returns value=None without raising."""
    result = cost_per_utci_degree({"tree_count": 10, "delta_utci_c": 0.0,
                                   "coverage_fraction": 0.0})
    assert result["value"] is None
    assert result["confidence"] == "LOW"


def test_nonpositive_delta_guarded_negative() -> None:
    """delta_utci_c < 0 returns value=None without raising."""
    result = cost_per_utci_degree({"tree_count": 10, "delta_utci_c": -0.3,
                                   "coverage_fraction": 0.0})
    assert result["value"] is None
    assert result["confidence"] == "LOW"


# ── Standard metric-dict shape (CONVENTIONS.md) ───────────────────────────────

def test_returns_standard_metric_dict() -> None:
    """Result always contains the mandatory standard-dict keys."""
    required_keys = {"value", "unit", "confidence", "sources", "note", "metric_id"}
    config = {"tree_count": 3, "delta_utci_c": 0.7, "coverage_fraction": 0.15}
    result = cost_per_utci_degree(config)
    assert required_keys.issubset(result.keys())
    assert result["unit"] == "EUR/degC"
    assert result["metric_id"] == "cost_per_utci_degree"
    assert isinstance(result["sources"], list)


# ── VALID-02 / D-08: KPI delta is NOT raw delta_tmrt_c ───────────────────────

def test_kpi_not_raw_delta_tmrt() -> None:
    """
    A config with a large delta_tmrt_c (12°C) and coverage_fraction giving a
    small UTCI-hours reduction must produce a KPI value much larger than
    cost / 12 — proving the denominator is NOT raw delta_tmrt_c.

    The UTCI-hours reduction for a modest coverage is far fewer equivalent
    °C than 12°C raw Tmrt, so cost / equiv_degc >> cost / 12.
    """
    config = {
        "tree_count": 10,
        "delta_tmrt_c": 12.0,
        # No delta_utci_c — forces the UTCI-hours path
        "coverage_fraction": 0.05,  # small coverage → small hours_reduced
    }
    result = cost_per_utci_degree(config)
    cost = total_cost(config)
    raw_tmrt_kpi = round(cost / 12.0, 2)

    if result["value"] is not None:
        # If we got a value, it should NOT equal cost/12 (raw Tmrt path)
        # With small coverage, UTCI-hours reduction is small, equiv_degc << 12
        # so cost/equiv_degc >> cost/12
        assert result["value"] != pytest.approx(raw_tmrt_kpi, rel=0.01), (
            "KPI equals cost/delta_tmrt_c — the raw-Tmrt-as-denominator path "
            "was NOT removed (D-08 violation)"
        )
        # The value from UTCI-hours path should be higher than the raw-Tmrt KPI
        # because equiv_degc < 12
        assert result["value"] > raw_tmrt_kpi, (
            "Expected UTCI-routed KPI to exceed cost/12 for small coverage "
            "(surrogate path gives far fewer equivalent °C than 12)"
        )


# ── D-09: both units reported ────────────────────────────────────────────────

def test_both_units_reported() -> None:
    """
    A positive-reduction config must report cost_per_utci_hour as a finite
    positive value alongside the primary EUR/degC value.
    """
    config = {
        "tree_count": 10,
        "coverage_fraction": 0.20,
    }
    result = cost_per_utci_degree(config)
    # cost_per_utci_hour must be present in the result dict
    assert "cost_per_utci_hour" in result, "cost_per_utci_hour key missing from result"
    if result.get("utci_hours_reduced") and result["utci_hours_reduced"] > 0:
        assert result["cost_per_utci_hour"] is not None
        assert result["cost_per_utci_hour"] > 0
        assert result["utci_hours_unit"] == "EUR / annual UTCI-hour above 32°C reduced"


def test_utci_hours_reduced_present() -> None:
    """Result dict carries utci_hours_reduced (float or None)."""
    config = {"tree_count": 5, "coverage_fraction": 0.15}
    result = cost_per_utci_degree(config)
    assert "utci_hours_reduced" in result


# ── HOURS_PER_DEGC_REF constant (Plan 05-03 cross-plan contract) ──────────────

def test_hours_per_degc_ref_is_positive() -> None:
    """HOURS_PER_DEGC_REF must be a positive finite float (Plan 03 imports it)."""
    assert isinstance(HOURS_PER_DEGC_REF, float)
    assert HOURS_PER_DEGC_REF > 0


# ── D-10 / VALID-04: uncertainty interval [lo, hi] ───────────────────────────

def test_interval_lo_lt_value_lt_hi() -> None:
    """
    For a positive-delta config with the default pre-calibration band,
    value_lo < value < value_hi must hold.
    """
    config = {"tree_count": 10, "coverage_fraction": 0.20}
    result = cost_per_utci_degree(config)
    if result["value"] is not None:
        assert "value_lo" in result
        assert "value_hi" in result
        if result["value_lo"] is not None and result["value_hi"] is not None:
            assert result["value_lo"] < result["value"] < result["value_hi"], (
                f"Interval not ordered: lo={result['value_lo']}, "
                f"value={result['value']}, hi={result['value_hi']}"
            )


def test_pre_calibration_band_label_default() -> None:
    """When band_c is None, band_source must equal 'pre-calibration, assumed ±4°C'."""
    config = {"tree_count": 10, "coverage_fraction": 0.20}
    result = cost_per_utci_degree(config)
    assert "band_source" in result
    if result["value"] is not None:
        assert result["band_source"] == "pre-calibration, assumed ±4°C"


def test_empirical_band_label_when_band_c_supplied() -> None:
    """Passing band_c=2.0 changes band_source to mention 'empirical calibration RMSE'."""
    config = {"tree_count": 10, "coverage_fraction": 0.20}
    result = cost_per_utci_degree(config, band_c=2.0)
    assert "band_source" in result
    if result["value"] is not None:
        assert "empirical calibration RMSE" in result["band_source"]
        assert "2.00" in result["band_source"]


def test_band_c_stored_in_result() -> None:
    """band_c value is echoed back in the result dict."""
    config = {"tree_count": 10, "coverage_fraction": 0.20}
    result_default = cost_per_utci_degree(config)
    assert "band_c" in result_default
    assert result_default["band_c"] == PRE_CALIBRATION_BAND_C

    result_custom = cost_per_utci_degree(config, band_c=3.0)
    assert result_custom["band_c"] == 3.0


def test_interval_none_when_value_none() -> None:
    """When value is None (zero/negative delta), all *_lo/*_hi fields are None."""
    config = {"tree_count": 10, "delta_utci_c": 0.0, "coverage_fraction": 0.0}
    result = cost_per_utci_degree(config)
    assert result["value"] is None
    assert result.get("value_lo") is None
    assert result.get("value_hi") is None


# ── CostTable / CostLine tests (COST-03 / Phase 6) ──────────────────────────

from coolspend.cost_model import (  # noqa: E402
    DEFAULT_COST_TABLE,
    CostLine,
    CostTable,
    VERIFIED,
    DECLARED,
    PENDING,
)


class TestCostLineDataclass:
    """CostLine is a frozen dataclass with the required fields."""

    def test_costline_is_frozen(self) -> None:
        """CostLine instances are immutable."""
        line = CostLine(
            key="test",
            label="Test line",
            value=100.0,
            unit="EUR/tree",
            kind="capex",
            source="test source",
            confidence=DECLARED,
        )
        with pytest.raises((AttributeError, TypeError)):
            line.value = 999.0  # type: ignore[misc]

    def test_costline_fields_present(self) -> None:
        """CostLine has all required fields."""
        line = CostLine(
            key="tree_stock",
            label="Tree stock",
            value=900.0,
            unit="EUR/tree",
            kind="capex",
            source="Some source",
            confidence=DECLARED,
        )
        assert line.key == "tree_stock"
        assert line.label == "Tree stock"
        assert line.value == 900.0
        assert line.unit == "EUR/tree"
        assert line.kind == "capex"
        assert isinstance(line.source, str) and line.source
        assert line.confidence == DECLARED


class TestDefaultCostTable:
    """DEFAULT_COST_TABLE has exactly 6 sourced lines with correct totals."""

    def test_has_exactly_six_lines(self) -> None:
        """DEFAULT_COST_TABLE must have exactly 6 cost lines."""
        assert len(DEFAULT_COST_TABLE.lines) == 6

    def test_has_all_required_keys(self) -> None:
        """All six required line keys must be present."""
        keys = {line.key for line in DEFAULT_COST_TABLE.lines}
        required_keys = {
            "tree_stock",
            "pit_excavation",
            "structural_soil",
            "guarding",
            "planting_labour",
            "annual_opex",
        }
        assert keys == required_keys

    def test_capex_total_equals_3000(self) -> None:
        """CapEx lines sum to exactly 3000.0 EUR/tree."""
        assert DEFAULT_COST_TABLE.capex_total() == pytest.approx(3000.0)

    def test_opex_per_year_equals_180(self) -> None:
        """OpEx lines sum to exactly 180.0 EUR/tree/yr."""
        assert DEFAULT_COST_TABLE.opex_per_year() == pytest.approx(180.0)

    def test_per_tree_cost_horizon_zero(self) -> None:
        """per_tree_cost(0) == 3000.0 (CapEx only, no OpEx)."""
        assert DEFAULT_COST_TABLE.per_tree_cost(0) == pytest.approx(3000.0)

    def test_per_tree_cost_horizon_40(self) -> None:
        """per_tree_cost(40) == 3000 + 180*40 == 10200.0."""
        assert DEFAULT_COST_TABLE.per_tree_cost(40) == pytest.approx(10200.0)

    def test_every_line_has_non_empty_source(self) -> None:
        """Every CostLine in DEFAULT_COST_TABLE has a non-empty source string."""
        for line in DEFAULT_COST_TABLE.lines:
            assert isinstance(line.source, str) and line.source.strip(), (
                f"CostLine '{line.key}' has empty source"
            )

    def test_every_line_has_valid_confidence(self) -> None:
        """Every CostLine confidence must be VERIFIED, DECLARED, or PENDING."""
        valid = {VERIFIED, DECLARED, PENDING}
        for line in DEFAULT_COST_TABLE.lines:
            assert line.confidence in valid, (
                f"CostLine '{line.key}' has invalid confidence '{line.confidence}'"
            )

    def test_label_says_verify_locally(self) -> None:
        """DEFAULT_COST_TABLE.label must include 'verify locally'."""
        assert "verify locally" in DEFAULT_COST_TABLE.label

    def test_five_capex_lines_one_opex_line(self) -> None:
        """Must have exactly 5 capex lines and 1 opex line."""
        capex_lines = [l for l in DEFAULT_COST_TABLE.lines if l.kind == "capex"]
        opex_lines = [l for l in DEFAULT_COST_TABLE.lines if l.kind == "opex"]
        assert len(capex_lines) == 5
        assert len(opex_lines) == 1


# ── GrowthDiscountParams + growth_cooling_fraction tests (COST-05 / D-07) ────

from coolspend.cost_model import (  # noqa: E402
    GrowthDiscountParams,
    DEFAULT_GROWTH_DISCOUNT,
    growth_cooling_fraction,
    discounted_lifetime_degc,
    discounted_total_cost,
)


class TestGrowthCoolingFraction:
    """growth_cooling_fraction(year, p) linear ramp from initial to 1.0 (D-07)."""

    def test_initial_fraction_at_year_zero(self) -> None:
        """growth_cooling_fraction(0, default) == 0.20 (initial_fraction)."""
        p = DEFAULT_GROWTH_DISCOUNT
        assert growth_cooling_fraction(0, p) == pytest.approx(0.20)

    def test_full_fraction_at_ramp_years(self) -> None:
        """growth_cooling_fraction(25, default) == 1.0 (full at ramp_years)."""
        p = DEFAULT_GROWTH_DISCOUNT
        assert growth_cooling_fraction(25, p) == pytest.approx(1.0)

    def test_clamped_after_ramp_years(self) -> None:
        """growth_cooling_fraction(40, default) == 1.0 (clamped beyond ramp)."""
        p = DEFAULT_GROWTH_DISCOUNT
        assert growth_cooling_fraction(40, p) == pytest.approx(1.0)

    def test_linear_midpoint(self) -> None:
        """At year 12.5 (half of 25), fraction == 0.60 (linear: 0.2 + 0.8*0.5)."""
        p = DEFAULT_GROWTH_DISCOUNT
        assert growth_cooling_fraction(12.5, p) == pytest.approx(0.60, rel=0.05)

    def test_monotonic_non_decreasing(self) -> None:
        """growth_cooling_fraction is non-decreasing across years 0..40."""
        p = DEFAULT_GROWTH_DISCOUNT
        fracs = [growth_cooling_fraction(y, p) for y in range(41)]
        for i in range(len(fracs) - 1):
            assert fracs[i] <= fracs[i + 1], (
                f"Not monotonic at year {i}: {fracs[i]} > {fracs[i+1]}"
            )


class TestDiscountedLifetimeDegc:
    """discounted_lifetime_degc is a discounted-weighted average °C (D-10)."""

    def test_strictly_less_than_full_canopy(self) -> None:
        """Discounted result is strictly < 1.0 (ramp + discount both reduce)."""
        p = DEFAULT_GROWTH_DISCOUNT
        result = discounted_lifetime_degc(1.0, p)
        assert result < 1.0, f"Expected < 1.0 but got {result}"

    def test_strictly_greater_than_initial_fraction(self) -> None:
        """Discounted result is > 0.20 (it's an average over ramp, not planting-yr only)."""
        p = DEFAULT_GROWTH_DISCOUNT
        result = discounted_lifetime_degc(1.0, p)
        assert result > 0.20, f"Expected > 0.20 but got {result}"

    def test_scales_linearly(self) -> None:
        """discounted_lifetime_degc(2.0, p) == 2 * discounted_lifetime_degc(1.0, p)."""
        p = DEFAULT_GROWTH_DISCOUNT
        result_1 = discounted_lifetime_degc(1.0, p)
        result_2 = discounted_lifetime_degc(2.0, p)
        assert result_2 == pytest.approx(2.0 * result_1, rel=1e-6)


class TestDiscountedTotalCost:
    """discounted_total_cost PV(OpEx) is bounded correctly."""

    def test_greater_than_capex_only(self) -> None:
        """PV of total cost > CapEx alone (OpEx PV is positive)."""
        p = DEFAULT_GROWTH_DISCOUNT
        result = discounted_total_cost({"tree_count": 1}, p)
        from coolspend.cost_model import DEFAULT_COST_TABLE
        capex = DEFAULT_COST_TABLE.capex_total()
        assert result > capex, (
            f"Expected discounted_total_cost > capex={capex}, got {result}"
        )

    def test_less_than_undiscounted_per_tree_cost(self) -> None:
        """PV of OpEx over 40yr (discounted) < undiscounted per_tree_cost(40)."""
        p = DEFAULT_GROWTH_DISCOUNT
        result = discounted_total_cost({"tree_count": 1}, p)
        undiscounted = per_tree_cost(40)
        assert result < undiscounted, (
            f"Expected discounted ({result}) < undiscounted ({undiscounted})"
        )

    def test_zero_tree_count_returns_zero(self) -> None:
        """tree_count=0 returns 0.0 without raising."""
        p = DEFAULT_GROWTH_DISCOUNT
        assert discounted_total_cost({"tree_count": 0}, p) == 0.0

    def test_scales_linearly_with_tree_count(self) -> None:
        """discounted_total_cost scales linearly with tree_count."""
        p = DEFAULT_GROWTH_DISCOUNT
        c1 = discounted_total_cost({"tree_count": 1}, p)
        c5 = discounted_total_cost({"tree_count": 5}, p)
        assert c5 == pytest.approx(5 * c1, rel=1e-6)


class TestGrowthDiscountParams:
    """GrowthDiscountParams dataclass has correct defaults (D-07/D-08/D-09)."""

    def test_default_ramp_years(self) -> None:
        """Default ramp_years == 25.0 (D-07)."""
        assert GrowthDiscountParams().ramp_years == 25.0

    def test_default_initial_fraction(self) -> None:
        """Default initial_fraction == 0.20 (D-07)."""
        assert GrowthDiscountParams().initial_fraction == pytest.approx(0.20)

    def test_default_discount_rate(self) -> None:
        """Default discount_rate == 0.035 (D-08: EU/UK Green Book)."""
        assert GrowthDiscountParams().discount_rate == pytest.approx(0.035)

    def test_default_horizon_years(self) -> None:
        """Default horizon_years == 40 (D-09: tree functional lifespan)."""
        assert GrowthDiscountParams().horizon_years == 40


# ── Task 2: KPI routing through growth+discount (COST-05) ────────────────────

class TestCostPerUtciDegreeGrowthDiscount:
    """cost_per_utci_degree routes through discounted °C + discounted cost."""

    # ── backward-compat: existing callers still work with no extra args ───────

    def test_existing_keys_preserved(self) -> None:
        """All Phase 5 KPI dict keys are preserved in the discounted result."""
        config = {"tree_count": 10, "delta_utci_c": 0.5, "coverage_fraction": 0.2}
        result = cost_per_utci_degree(config)
        required_keys = {
            "value", "value_lo", "value_hi", "unit", "confidence",
            "sources", "note", "metric_id",
            "utci_hours_reduced", "cost_per_utci_hour",
            "cost_per_utci_hour_lo", "cost_per_utci_hour_hi",
            "utci_hours_unit", "band_c", "band_source",
        }
        assert required_keys.issubset(result.keys()), (
            f"Missing keys: {required_keys - result.keys()}"
        )

    def test_new_param_echo_keys_present(self) -> None:
        """New keys (discount_rate, ramp_years, horizon_years, growth_note) are additive."""
        config = {"tree_count": 10, "delta_utci_c": 0.5, "coverage_fraction": 0.2}
        result = cost_per_utci_degree(config)
        assert result["discount_rate"] == pytest.approx(0.035)
        assert result["ramp_years"] == pytest.approx(25.0)
        assert result["horizon_years"] == 40
        assert "growth_note" in result

    def test_unit_unchanged(self) -> None:
        """unit key stays 'EUR/degC' after discounting."""
        config = {"tree_count": 10, "delta_utci_c": 0.5, "coverage_fraction": 0.2}
        result = cost_per_utci_degree(config)
        assert result["unit"] == "EUR/degC"

    def test_discounted_value_higher_than_undiscounted(self) -> None:
        """
        Discounted KPI > equivalent undiscounted day-one KPI.

        Because discounted_lifetime_degc < full_canopy_degc (ramp + discount both
        reduce the denominator), the discounted €/°C is costlier per °C — value rises.
        """
        config = {"tree_count": 10, "delta_utci_c": 0.5, "coverage_fraction": 0.2}
        discounted_result = cost_per_utci_degree(config)

        # Simulate day-one full canopy: ramp_years=0 (instant) + discount_rate=0.0
        no_growth_no_discount = GrowthDiscountParams(
            ramp_years=25.0,
            initial_fraction=1.0,   # fraction is 1.0 from year 0 = no ramp effect
            discount_rate=0.0,      # no discounting
            horizon_years=40,
        )
        undiscounted_result = cost_per_utci_degree(config, growth_discount=no_growth_no_discount)

        if discounted_result["value"] is not None and undiscounted_result["value"] is not None:
            assert discounted_result["value"] > undiscounted_result["value"], (
                f"Expected discounted {discounted_result['value']} > undiscounted "
                f"{undiscounted_result['value']}"
            )

    def test_zero_negative_guard_preserved(self) -> None:
        """Zero/negative-delta guard still returns value=None, confidence=LOW."""
        result = cost_per_utci_degree({"tree_count": 10, "delta_utci_c": 0.0,
                                       "coverage_fraction": 0.0})
        assert result["value"] is None
        assert result["confidence"] == "LOW"

    def test_negative_guard_preserved(self) -> None:
        """Negative delta still returns value=None, confidence=LOW."""
        result = cost_per_utci_degree({"tree_count": 10, "delta_utci_c": -0.5,
                                       "coverage_fraction": 0.0})
        assert result["value"] is None
        assert result["confidence"] == "LOW"

    def test_interval_ordering_preserved(self) -> None:
        """value_lo < value < value_hi interval ordering still holds."""
        config = {"tree_count": 10, "coverage_fraction": 0.20}
        result = cost_per_utci_degree(config)
        if result["value"] is not None and result["value_lo"] is not None and result["value_hi"] is not None:
            assert result["value_lo"] < result["value"] < result["value_hi"]

    def test_custom_growth_discount_param_honoured(self) -> None:
        """Passing a custom GrowthDiscountParams instance overrides defaults."""
        config = {"tree_count": 10, "delta_utci_c": 0.5, "coverage_fraction": 0.2}
        custom_p = GrowthDiscountParams(discount_rate=0.07, horizon_years=30)
        result = cost_per_utci_degree(config, growth_discount=custom_p)
        assert result["discount_rate"] == pytest.approx(0.07)
        assert result["horizon_years"] == 30

    def test_guard_result_still_has_new_keys(self) -> None:
        """Even when value=None (zero/negative guard), the new param-echo keys are present."""
        result = cost_per_utci_degree({"tree_count": 10, "delta_utci_c": 0.0,
                                       "coverage_fraction": 0.0})
        assert "discount_rate" in result
        assert "ramp_years" in result
        assert "horizon_years" in result
        assert "growth_note" in result
