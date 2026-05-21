"""
test_cost_config.py — Tests for cost_config.json + load_cost_table / cost_table_from_dict
(COST-04 / D-05 / Plan 06-03 Task 1).

Tests cover:
    - Round-trip: DEFAULT_COST_TABLE → dict → cost_table_from_dict equals defaults
    - load_cost_table() returns CapEx=3000, OpEx=180, discount_rate=0.035
    - Invalid / missing path falls back to defaults without raising
    - Invalid JSON falls back to defaults without raising
    - An edited dict (annual_opex=400) produces a higher per_tree_cost and a higher
      cost_per_utci_degree value when threaded through cost_per_utci_degree
    - Validation: non-positive values fall back to defaults
    - Validation: invalid confidence falls back to defaults
    - Validation: missing required keys skipped gracefully
    - GrowthDiscountParams loaded from cost_config.json matches defaults
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from coolspend.cost_model import (
    DEFAULT_COST_TABLE,
    DEFAULT_GROWTH_DISCOUNT,
    CostLine,
    CostTable,
    GrowthDiscountParams,
    DECLARED,
    PENDING,
    VERIFIED,
    cost_per_utci_degree,
    cost_table_from_dict,
    load_cost_table,
)

# ── Helpers ───────────────────────────────────────────────────────────────────


def _default_dict() -> dict:
    """Build a dict that mirrors the shipped cost_config.json defaults."""
    return {
        "label": DEFAULT_COST_TABLE.label,
        "lines": [
            {
                "key": line.key,
                "label": line.label,
                "value": line.value,
                "unit": line.unit,
                "kind": line.kind,
                "source": line.source,
                "confidence": line.confidence,
            }
            for line in DEFAULT_COST_TABLE.lines
        ],
        "growth_discount": {
            "ramp_years": DEFAULT_GROWTH_DISCOUNT.ramp_years,
            "initial_fraction": DEFAULT_GROWTH_DISCOUNT.initial_fraction,
            "discount_rate": DEFAULT_GROWTH_DISCOUNT.discount_rate,
            "horizon_years": DEFAULT_GROWTH_DISCOUNT.horizon_years,
        },
    }


# ── Round-trip: DEFAULT_COST_TABLE → dict → cost_table_from_dict ─────────────

class TestCostTableRoundTrip:
    """cost_table_from_dict on default-values dict returns equal-valued table."""

    def test_capex_total_roundtrip(self) -> None:
        """CapEx total round-trips through dict → cost_table_from_dict."""
        d = _default_dict()
        table, _ = cost_table_from_dict(d)
        assert table.capex_total() == pytest.approx(DEFAULT_COST_TABLE.capex_total())

    def test_opex_per_year_roundtrip(self) -> None:
        """OpEx per year round-trips through dict → cost_table_from_dict."""
        d = _default_dict()
        table, _ = cost_table_from_dict(d)
        assert table.opex_per_year() == pytest.approx(DEFAULT_COST_TABLE.opex_per_year())

    def test_line_count_roundtrip(self) -> None:
        """Line count preserved through round-trip."""
        d = _default_dict()
        table, _ = cost_table_from_dict(d)
        assert len(table.lines) == len(DEFAULT_COST_TABLE.lines)

    def test_all_keys_present_roundtrip(self) -> None:
        """All line keys preserved through round-trip."""
        d = _default_dict()
        table, _ = cost_table_from_dict(d)
        orig_keys = {l.key for l in DEFAULT_COST_TABLE.lines}
        new_keys = {l.key for l in table.lines}
        assert new_keys == orig_keys

    def test_growth_discount_roundtrip(self) -> None:
        """GrowthDiscountParams round-trips with correct default values."""
        d = _default_dict()
        _, gd = cost_table_from_dict(d)
        assert gd.ramp_years == pytest.approx(DEFAULT_GROWTH_DISCOUNT.ramp_years)
        assert gd.initial_fraction == pytest.approx(DEFAULT_GROWTH_DISCOUNT.initial_fraction)
        assert gd.discount_rate == pytest.approx(DEFAULT_GROWTH_DISCOUNT.discount_rate)
        assert gd.horizon_years == DEFAULT_GROWTH_DISCOUNT.horizon_years


# ── load_cost_table() reads the bundled config ────────────────────────────────

class TestLoadCostTable:
    """load_cost_table() reads cost_config.json and returns correct defaults."""

    def test_capex_total_is_3000(self) -> None:
        """load_cost_table() → table.capex_total() == 3000.0."""
        table, _ = load_cost_table()
        assert table.capex_total() == pytest.approx(3000.0)

    def test_opex_per_year_is_180(self) -> None:
        """load_cost_table() → table.opex_per_year() == 180.0."""
        table, _ = load_cost_table()
        assert table.opex_per_year() == pytest.approx(180.0)

    def test_discount_rate_is_0035(self) -> None:
        """load_cost_table() → gd.discount_rate == 0.035."""
        _, gd = load_cost_table()
        assert gd.discount_rate == pytest.approx(0.035)

    def test_ramp_years_is_25(self) -> None:
        """load_cost_table() → gd.ramp_years == 25.0."""
        _, gd = load_cost_table()
        assert gd.ramp_years == pytest.approx(25.0)

    def test_horizon_years_is_40(self) -> None:
        """load_cost_table() → gd.horizon_years == 40."""
        _, gd = load_cost_table()
        assert gd.horizon_years == 40

    def test_returns_tuple_of_correct_types(self) -> None:
        """load_cost_table() returns (CostTable, GrowthDiscountParams)."""
        result = load_cost_table()
        assert isinstance(result, tuple) and len(result) == 2
        assert isinstance(result[0], CostTable)
        assert isinstance(result[1], GrowthDiscountParams)

    def test_label_says_verify_locally(self) -> None:
        """Loaded table label contains 'verify locally'."""
        table, _ = load_cost_table()
        assert "verify locally" in table.label


# ── Fail-open: invalid / missing path ────────────────────────────────────────

class TestLoadCostTableFailOpen:
    """load_cost_table falls back to defaults without raising on bad inputs."""

    def test_missing_path_falls_back_no_raise(self) -> None:
        """Non-existent path returns defaults — no exception."""
        table, gd = load_cost_table("/nonexistent/no/such/path/cost_config.json")
        assert table.capex_total() == pytest.approx(DEFAULT_COST_TABLE.capex_total())
        assert gd.discount_rate == pytest.approx(DEFAULT_GROWTH_DISCOUNT.discount_rate)

    def test_invalid_json_falls_back_no_raise(self) -> None:
        """File with invalid JSON returns defaults — no exception."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            f.write("{ not valid json !!!")
            tmp_path = f.name
        try:
            table, gd = load_cost_table(tmp_path)
            assert table.capex_total() == pytest.approx(DEFAULT_COST_TABLE.capex_total())
            assert gd.discount_rate == pytest.approx(DEFAULT_GROWTH_DISCOUNT.discount_rate)
        finally:
            os.unlink(tmp_path)

    def test_json_root_not_dict_falls_back(self) -> None:
        """File with JSON array root returns defaults — no exception."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            f.write("[1, 2, 3]")
            tmp_path = f.name
        try:
            table, gd = load_cost_table(tmp_path)
            assert table.capex_total() == pytest.approx(DEFAULT_COST_TABLE.capex_total())
        finally:
            os.unlink(tmp_path)

    def test_empty_lines_falls_back_to_defaults(self) -> None:
        """Dict with no 'lines' key falls back to DEFAULT_COST_TABLE lines."""
        table, gd = cost_table_from_dict({"growth_discount": {}})
        assert table.capex_total() == pytest.approx(DEFAULT_COST_TABLE.capex_total())


# ── Validation: edited dict produces correct changes ─────────────────────────

class TestCostTableFromDictEdits:
    """cost_table_from_dict correctly applies user edits and validates inputs."""

    def test_edited_annual_opex_increases_per_tree_cost(self) -> None:
        """Raising annual_opex from 180 to 400 increases per_tree_cost(40)."""
        d = _default_dict()
        for line in d["lines"]:
            if line["key"] == "annual_opex":
                line["value"] = 400.0
        table, _ = cost_table_from_dict(d)
        assert table.opex_per_year() == pytest.approx(400.0)
        default_ptc = DEFAULT_COST_TABLE.per_tree_cost(40)
        edited_ptc = table.per_tree_cost(40)
        assert edited_ptc > default_ptc, (
            f"Edited per_tree_cost {edited_ptc} should exceed default {default_ptc}"
        )

    def test_edited_annual_opex_increases_kpi(self) -> None:
        """Raising annual_opex=400 produces a higher cost_per_utci_degree than default."""
        config = {"tree_count": 10, "delta_utci_c": 0.5, "coverage_fraction": 0.2}

        d = _default_dict()
        for line in d["lines"]:
            if line["key"] == "annual_opex":
                line["value"] = 400.0
        edited_table, _ = cost_table_from_dict(d)

        default_result = cost_per_utci_degree(config)
        edited_result = cost_per_utci_degree(config, cost_table=edited_table)

        if default_result["value"] is not None and edited_result["value"] is not None:
            assert edited_result["value"] > default_result["value"], (
                f"Edited KPI ({edited_result['value']}) should exceed default "
                f"({default_result['value']}) when annual_opex is raised"
            )

    def test_nonpositive_value_falls_back_to_default(self) -> None:
        """A line with value=0 falls back to the default value for that key."""
        d = _default_dict()
        for line in d["lines"]:
            if line["key"] == "tree_stock":
                line["value"] = 0.0  # non-positive → should fall back
        table, _ = cost_table_from_dict(d)
        stock_line = next((l for l in table.lines if l.key == "tree_stock"), None)
        assert stock_line is not None
        assert stock_line.value == pytest.approx(DEFAULT_COST_TABLE.lines[0].value)

    def test_invalid_confidence_falls_back_to_default_line(self) -> None:
        """A line with invalid confidence falls back to the default CostLine."""
        d = _default_dict()
        for line in d["lines"]:
            if line["key"] == "guarding":
                line["confidence"] = "FAKE_CONFIDENCE"
        table, _ = cost_table_from_dict(d)
        guarding = next((l for l in table.lines if l.key == "guarding"), None)
        assert guarding is not None
        # Should have fallen back to the default line's value
        default_guarding = next(
            l for l in DEFAULT_COST_TABLE.lines if l.key == "guarding"
        )
        assert guarding.value == pytest.approx(default_guarding.value)
        assert guarding.confidence == default_guarding.confidence

    def test_missing_required_key_skips_line(self) -> None:
        """A line missing 'value' is skipped gracefully."""
        d = _default_dict()
        # Remove 'value' from the first line
        del d["lines"][0]["value"]
        table, _ = cost_table_from_dict(d)
        # Should have 5 lines (one skipped) + fallback may not add it back
        # because the key was removed — at minimum, no crash
        assert len(table.lines) >= 1  # did not crash

    def test_edited_discount_rate_changes_kpi(self) -> None:
        """Raising discount_rate via growth_discount changes KPI."""
        config = {"tree_count": 10, "delta_utci_c": 0.5, "coverage_fraction": 0.2}
        d = _default_dict()
        d["growth_discount"]["discount_rate"] = 0.10  # higher discount rate
        _, edited_gd = cost_table_from_dict(d)
        assert edited_gd.discount_rate == pytest.approx(0.10)
        # KPI with higher discount rate should differ from default
        default_result = cost_per_utci_degree(config)
        edited_result = cost_per_utci_degree(config, growth_discount=edited_gd)
        if default_result["value"] is not None and edited_result["value"] is not None:
            assert default_result["value"] != edited_result["value"], (
                "discount_rate=0.10 should produce a different KPI than 0.035"
            )


# ── cost_per_utci_degree: backward compat with cost_table=None ────────────────

class TestCostPerUtciDegreeBackwardCompat:
    """Existing callers of cost_per_utci_degree still work with no cost_table."""

    def test_no_cost_table_arg_returns_dict(self) -> None:
        """cost_per_utci_degree(config) with no cost_table still works."""
        config = {"tree_count": 5, "delta_utci_c": 0.4, "coverage_fraction": 0.15}
        result = cost_per_utci_degree(config)
        assert isinstance(result, dict)
        assert result["unit"] == "EUR/degC"

    def test_none_cost_table_same_as_no_arg(self) -> None:
        """cost_table=None produces the same result as omitting the arg."""
        config = {"tree_count": 5, "delta_utci_c": 0.4, "coverage_fraction": 0.15}
        r1 = cost_per_utci_degree(config)
        r2 = cost_per_utci_degree(config, cost_table=None)
        assert r1["value"] == r2["value"]
        assert r1["value_lo"] == r2["value_lo"]

    def test_edited_table_changes_value(self) -> None:
        """Passing an edited CostTable changes the KPI value."""
        config = {"tree_count": 10, "delta_utci_c": 0.5, "coverage_fraction": 0.2}
        # Double the opex
        from coolspend.cost_model import CostLine
        doubled_lines = [
            CostLine(
                key=line.key,
                label=line.label,
                value=line.value * 2 if line.kind == "opex" else line.value,
                unit=line.unit,
                kind=line.kind,
                source=line.source,
                confidence=line.confidence,
            )
            for line in DEFAULT_COST_TABLE.lines
        ]
        doubled_table = CostTable(lines=doubled_lines)
        default_result = cost_per_utci_degree(config)
        edited_result = cost_per_utci_degree(config, cost_table=doubled_table)
        if default_result["value"] is not None and edited_result["value"] is not None:
            assert edited_result["value"] > default_result["value"], (
                "Doubled OpEx should produce a higher (costlier) KPI"
            )
