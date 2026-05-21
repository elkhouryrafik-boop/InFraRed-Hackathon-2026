"""
coolspend/tests/test_calibration.py — TDD tests for the calibration study module.

Tests run offline (INFRARED_BACKEND=mock, default) — no live key required.
Live-then-cache procedure is documented in the SUMMARY.md.

Requirements tested:
  - D-02: generate_study_configs deterministic, coverage-swept (10 configs, seed=42)
  - D-03: Separate SimBudget(max_live_calls=n+1) — distinct from Top-3 cap of 3
  - D-04: compute_fit → RMSE, R², error_band_c (1.96*RMSE)
  - D-05: rank_stability BOTH ways — set-overlap headline + Spearman ρ + Kendall τ
  - T-05-08: artifact JSON contains no api key/secret
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest


# ── Fixtures / helpers ────────────────────────────────────────────────────────


def _ensure_mock_backend(monkeypatch):
    """Guarantee INFRARED_BACKEND=mock for the test (never require a live key)."""
    monkeypatch.delenv("INFRARED_BACKEND", raising=False)
    monkeypatch.delenv("INFRARED_API_KEY", raising=False)


# ── Task 1 tests: generate_study_configs ─────────────────────────────────────


class TestGenerateStudyConfigs:
    def test_returns_exactly_n_configs(self):
        """generate_study_configs(n=10) returns exactly 10 configs."""
        from coolspend.calibration import generate_study_configs
        configs = generate_study_configs(n=10, seed=42)
        assert len(configs) == 10

    def test_deterministic_same_seed(self):
        """Two calls with seed=42 produce identical configs (D-02)."""
        from coolspend.calibration import generate_study_configs
        c1 = generate_study_configs(n=10, seed=42)
        c2 = generate_study_configs(n=10, seed=42)
        # Coverage fractions must be identical
        fracs1 = [cfg["coverage_fraction"] for cfg in c1]
        fracs2 = [cfg["coverage_fraction"] for cfg in c2]
        assert fracs1 == fracs2

    def test_different_seeds_different_configs(self):
        """Different seeds produce different configs (seed isolation check)."""
        from coolspend.calibration import generate_study_configs
        c42 = generate_study_configs(n=10, seed=42)
        c99 = generate_study_configs(n=10, seed=99)
        fracs42 = [cfg["coverage_fraction"] for cfg in c42]
        fracs99 = [cfg["coverage_fraction"] for cfg in c99]
        assert fracs42 != fracs99

    def test_coverage_fraction_nondecreasing(self):
        """coverage_fraction is non-decreasing across the returned list (D-02 sweep)."""
        from coolspend.calibration import generate_study_configs
        configs = generate_study_configs(n=10, seed=42)
        fracs = [cfg["coverage_fraction"] for cfg in configs]
        for i in range(len(fracs) - 1):
            assert fracs[i] <= fracs[i + 1], (
                f"coverage_fraction not non-decreasing at index {i}: "
                f"{fracs[i]} > {fracs[i + 1]}"
            )

    def test_configs_have_required_keys(self):
        """Each config carries delta_tmrt_c, coverage_fraction, tree_count."""
        from coolspend.calibration import generate_study_configs
        configs = generate_study_configs(n=10, seed=42)
        for i, cfg in enumerate(configs):
            assert "coverage_fraction" in cfg, f"Config {i} missing coverage_fraction"
            assert "delta_tmrt_c" in cfg, f"Config {i} missing delta_tmrt_c"
            assert "tree_count" in cfg, f"Config {i} missing tree_count"

    def test_coverage_fraction_range(self):
        """coverage_fraction is in [0, 0.9] (MAX_SITE_COVERAGE cap from spatial_engine)."""
        from coolspend.calibration import generate_study_configs
        configs = generate_study_configs(n=10, seed=42)
        for cfg in configs:
            assert 0.0 <= cfg["coverage_fraction"] <= 0.9 + 1e-9

    def test_delta_tmrt_nonnegative(self):
        """delta_tmrt_c is non-negative (thermal surrogate always >= 0)."""
        from coolspend.calibration import generate_study_configs
        configs = generate_study_configs(n=10, seed=42)
        for cfg in configs:
            assert cfg["delta_tmrt_c"] >= 0.0

    def test_sweep_span(self):
        """Coverage sweep spans a meaningful range (not all identical values)."""
        from coolspend.calibration import generate_study_configs
        configs = generate_study_configs(n=10, seed=42)
        fracs = [cfg["coverage_fraction"] for cfg in configs]
        span = max(fracs) - min(fracs)
        # Require at least some spread across the sweep
        assert span > 0.0, "Coverage sweep has no spread — all configs identical"


# ── Task 1 tests: SimBudget separate cap ─────────────────────────────────────


class TestStudySimBudget:
    def test_budget_cap_is_n_plus_1(self, monkeypatch):
        """run_calibration_study uses SimBudget(max_live_calls=n+1) not cap=3 (D-03)."""
        _ensure_mock_backend(monkeypatch)
        # We inspect the budget by running the study and checking it doesn't raise
        # (n=10 → cap=11; baseline=1 + 10 interventions = 11 total calls).
        from coolspend.calibration import run_calibration_study
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = str(Path(tmpdir) / "cal_study.json")
            result = run_calibration_study(n=10, out_path=out_path)
        assert "configs" in result
        assert len(result["configs"]) == 10

    def test_budget_raises_on_excess_calls(self):
        """SimBudget raises RuntimeError past its cap (D-03 guard honored)."""
        from coolspend.sdk_client import SimBudget
        # Create a budget with cap=11 (n=10 + baseline=1)
        budget = SimBudget(max_live_calls=11)
        for i in range(11):
            budget.record(f"call {i}")
        with pytest.raises(RuntimeError, match="SimBudget exceeded"):
            budget.record("call 12 — over cap")

    def test_top3_budget_cap_unchanged(self):
        """optimizer.py Top-3 SimBudget cap=3 is unchanged (D-03 isolation check)."""
        # Grep optimizer source to confirm the literal 3 cap is still there
        optimizer_path = Path(__file__).resolve().parents[2] / "coolspend" / "optimizer.py"
        source = optimizer_path.read_text(encoding="utf-8")
        assert "SimBudget(max_live_calls=3)" in source, (
            "optimizer.py Top-3 SimBudget cap must remain =3 (D-03)"
        )


# ── Task 1 tests: run_calibration_study structure ────────────────────────────


class TestRunCalibrationStudyStructure:
    def test_returns_baseline_utci_c(self, monkeypatch):
        """run_calibration_study result contains baseline_utci_c."""
        _ensure_mock_backend(monkeypatch)
        from coolspend.calibration import run_calibration_study
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_calibration_study(n=10, out_path=str(Path(tmpdir) / "out.json"))
        assert "baseline_utci_c" in result

    def test_returns_n_configs(self, monkeypatch):
        """run_calibration_study result contains n configs."""
        _ensure_mock_backend(monkeypatch)
        from coolspend.calibration import run_calibration_study
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_calibration_study(n=10, out_path=str(Path(tmpdir) / "out.json"))
        assert result["n_configs"] == 10

    def test_configs_have_real_delta_utci(self, monkeypatch):
        """Each config carries real_delta_utci_c and real_utci_c after study run."""
        _ensure_mock_backend(monkeypatch)
        from coolspend.calibration import run_calibration_study
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_calibration_study(n=10, out_path=str(Path(tmpdir) / "out.json"))
        for i, cfg in enumerate(result["configs"]):
            assert "real_utci_c" in cfg, f"Config {i} missing real_utci_c"
            assert "real_delta_utci_c" in cfg, f"Config {i} missing real_delta_utci_c"

    def test_configs_have_surrogate_pred(self, monkeypatch):
        """Each config carries surrogate_pred_utci_delta_c (HOURS_PER_DEGC_REF path)."""
        _ensure_mock_backend(monkeypatch)
        from coolspend.calibration import run_calibration_study
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_calibration_study(n=10, out_path=str(Path(tmpdir) / "out.json"))
        for i, cfg in enumerate(result["configs"]):
            assert "surrogate_pred_utci_delta_c" in cfg, (
                f"Config {i} missing surrogate_pred_utci_delta_c"
            )

    def test_seed_recorded(self, monkeypatch):
        """run_calibration_study result records the seed used."""
        _ensure_mock_backend(monkeypatch)
        from coolspend.calibration import run_calibration_study, STUDY_SEED
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_calibration_study(n=10, out_path=str(Path(tmpdir) / "out.json"))
        assert result.get("seed") == STUDY_SEED


# ── Task 2 tests: compute_fit ────────────────────────────────────────────────


class TestComputeFit:
    def _make_configs(self, n=5, offset=0.0):
        """Build synthetic configs with known surrogate_pred and real_delta values."""
        configs = []
        for i in range(n):
            pred = 0.5 + i * 0.3
            real = pred + offset  # perfect correlation, known offset
            configs.append({
                "surrogate_pred_utci_delta_c": round(pred, 3),
                "real_delta_utci_c": round(real, 3),
            })
        return configs

    def test_returns_rmse_r2_error_band(self):
        """compute_fit returns dict with rmse, r2, error_band_c, n, band_basis."""
        from coolspend.calibration import compute_fit
        configs = self._make_configs(5, offset=0.1)
        result = compute_fit(configs)
        assert "rmse" in result
        assert "r2" in result
        assert "error_band_c" in result
        assert "n" in result
        assert "band_basis" in result

    def test_perfect_prediction_zero_rmse(self):
        """compute_fit returns rmse=0.0 for perfect surrogate predictions."""
        from coolspend.calibration import compute_fit
        configs = self._make_configs(5, offset=0.0)  # pred == real
        result = compute_fit(configs)
        assert result["rmse"] == pytest.approx(0.0, abs=1e-6)

    def test_r2_near_one_for_linear(self):
        """compute_fit returns r2 near 1.0 for linearly scaled predictions."""
        from coolspend.calibration import compute_fit
        configs = self._make_configs(10, offset=0.0)
        result = compute_fit(configs)
        assert result["r2"] == pytest.approx(1.0, abs=1e-4)

    def test_rmse_positive_for_imperfect(self):
        """compute_fit returns rmse > 0 when pred != real."""
        from coolspend.calibration import compute_fit
        configs = self._make_configs(5, offset=0.5)  # constant offset
        result = compute_fit(configs)
        assert result["rmse"] > 0.0

    def test_error_band_is_1_96_rmse(self):
        """error_band_c = 1.96 * rmse (95% band basis)."""
        from coolspend.calibration import compute_fit
        configs = self._make_configs(5, offset=0.5)
        result = compute_fit(configs)
        assert result["error_band_c"] == pytest.approx(1.96 * result["rmse"], abs=1e-3)

    def test_r2_guard_zero_ss_tot(self):
        """compute_fit returns r2=None when SS_tot==0 (all real values identical)."""
        from coolspend.calibration import compute_fit
        # All real values are the same → SS_tot = 0
        configs = [
            {"surrogate_pred_utci_delta_c": 1.0, "real_delta_utci_c": 2.0},
            {"surrogate_pred_utci_delta_c": 2.0, "real_delta_utci_c": 2.0},
            {"surrogate_pred_utci_delta_c": 3.0, "real_delta_utci_c": 2.0},
        ]
        result = compute_fit(configs)
        assert result["r2"] is None

    def test_n_matches_config_count(self):
        """compute_fit['n'] matches the number of configs passed."""
        from coolspend.calibration import compute_fit
        configs = self._make_configs(7)
        result = compute_fit(configs)
        assert result["n"] == 7


# ── Task 2 tests: rank_stability ─────────────────────────────────────────────


class TestRankStability:
    def _make_configs_rank(self, n=8, swap=False):
        """Build configs with ascending surrogate predictions.

        If swap=True, the real measurements have ranks 1 and 2 swapped relative
        to the surrogate, so rank_swaps should detect a "rank 1<->2" swap.
        """
        configs = []
        for i in range(n):
            pred = float(i) + 1.0
            configs.append({
                "surrogate_pred_utci_delta_c": pred,
                "real_delta_utci_c": pred,
            })
        if swap and n >= 2:
            # Swap the top two real values (indices n-1 and n-2)
            configs[n-1]["real_delta_utci_c"], configs[n-2]["real_delta_utci_c"] = (
                configs[n-2]["real_delta_utci_c"], configs[n-1]["real_delta_utci_c"]
            )
        return configs

    def test_returns_required_keys(self):
        """rank_stability returns dict with all required keys."""
        from coolspend.calibration import rank_stability
        configs = self._make_configs_rank(8)
        result = rank_stability(configs)
        assert "spearman_rho" in result
        assert "kendall_tau" in result
        assert "set_overlap_top3" in result
        assert "rank_swaps" in result
        assert "headline" in result

    def test_perfect_correlation_rho_1(self):
        """Spearman rho == 1.0 when surrogate and real have identical order."""
        from coolspend.calibration import rank_stability
        configs = self._make_configs_rank(8, swap=False)
        result = rank_stability(configs)
        assert result["spearman_rho"] == pytest.approx(1.0, abs=1e-3)

    def test_perfect_correlation_tau_1(self):
        """Kendall tau == 1.0 when surrogate and real have identical order."""
        from coolspend.calibration import rank_stability
        configs = self._make_configs_rank(8, swap=False)
        result = rank_stability(configs)
        assert result["kendall_tau"] == pytest.approx(1.0, abs=1e-3)

    def test_set_overlap_perfect(self):
        """set_overlap_top3 == 3 when surrogate and real Top-3 are identical."""
        from coolspend.calibration import rank_stability
        configs = self._make_configs_rank(8, swap=False)
        result = rank_stability(configs)
        assert result["set_overlap_top3"] == 3

    def test_headline_contains_fraction(self):
        """headline string contains '/3 surrogate Top-3'."""
        from coolspend.calibration import rank_stability
        configs = self._make_configs_rank(8)
        result = rank_stability(configs)
        assert "/3" in result["headline"]

    def test_rank_swaps_list(self):
        """rank_swaps is a list (may be empty for perfect order)."""
        from coolspend.calibration import rank_stability
        configs = self._make_configs_rank(8)
        result = rank_stability(configs)
        assert isinstance(result["rank_swaps"], list)

    def test_set_overlap_top3_range(self):
        """set_overlap_top3 is between 0 and 3 inclusive."""
        from coolspend.calibration import rank_stability
        configs = self._make_configs_rank(8, swap=True)
        result = rank_stability(configs)
        assert 0 <= result["set_overlap_top3"] <= 3

    def test_spearman_tau_rounded(self):
        """spearman_rho and kendall_tau are rounded to 3 decimal places."""
        from coolspend.calibration import rank_stability
        configs = self._make_configs_rank(8)
        result = rank_stability(configs)
        # Check they are floats (or None)
        assert isinstance(result["spearman_rho"], float)
        assert isinstance(result["kendall_tau"], float)


# ── Task 2 tests: artifact JSON ──────────────────────────────────────────────


class TestCalibrationArtifact:
    def test_writes_json_file(self, monkeypatch, tmp_path):
        """run_calibration_study writes outputs/calibration_study.json."""
        _ensure_mock_backend(monkeypatch)
        from coolspend.calibration import run_calibration_study
        out_path = str(tmp_path / "calibration_study.json")
        run_calibration_study(n=10, out_path=out_path)
        assert Path(out_path).exists(), "calibration_study.json was not written"

    def test_json_reloadable(self, monkeypatch, tmp_path):
        """Written JSON is valid and reloadable."""
        _ensure_mock_backend(monkeypatch)
        from coolspend.calibration import run_calibration_study
        out_path = str(tmp_path / "calibration_study.json")
        run_calibration_study(n=10, out_path=out_path)
        with open(out_path, encoding="utf-8") as fh:
            data = json.load(fh)
        assert isinstance(data, dict)

    def test_artifact_has_fit_keys(self, monkeypatch, tmp_path):
        """Artifact JSON contains fit.rmse, fit.r2, fit.error_band_c."""
        _ensure_mock_backend(monkeypatch)
        from coolspend.calibration import run_calibration_study
        out_path = str(tmp_path / "calibration_study.json")
        run_calibration_study(n=10, out_path=out_path)
        with open(out_path, encoding="utf-8") as fh:
            data = json.load(fh)
        fit = data.get("fit", {})
        assert "rmse" in fit, "artifact missing fit.rmse"
        assert "r2" in fit, "artifact missing fit.r2"
        assert "error_band_c" in fit, "artifact missing fit.error_band_c"

    def test_artifact_has_rank_stability_keys(self, monkeypatch, tmp_path):
        """Artifact JSON contains rank_stability keys."""
        _ensure_mock_backend(monkeypatch)
        from coolspend.calibration import run_calibration_study
        out_path = str(tmp_path / "calibration_study.json")
        run_calibration_study(n=10, out_path=out_path)
        with open(out_path, encoding="utf-8") as fh:
            data = json.load(fh)
        rs = data.get("rank_stability", {})
        assert "spearman_rho" in rs, "artifact missing rank_stability.spearman_rho"
        assert "kendall_tau" in rs, "artifact missing rank_stability.kendall_tau"
        assert "set_overlap_top3" in rs, "artifact missing rank_stability.set_overlap_top3"
        assert "rank_swaps" in rs, "artifact missing rank_stability.rank_swaps"

    def test_artifact_no_api_key(self, monkeypatch, tmp_path):
        """Artifact JSON must not contain INFRARED_API_KEY or any secret (T-05-08)."""
        _ensure_mock_backend(monkeypatch)
        from coolspend.calibration import run_calibration_study
        out_path = str(tmp_path / "calibration_study.json")
        run_calibration_study(n=10, out_path=out_path)
        raw = Path(out_path).read_text(encoding="utf-8")
        assert "INFRARED_API_KEY" not in raw, "INFRARED_API_KEY found in artifact JSON!"
        assert "api_key" not in raw.lower(), "api_key substring found in artifact JSON!"

    def test_artifact_has_disclaimer(self, monkeypatch, tmp_path):
        """Artifact JSON contains a disclaimer field."""
        _ensure_mock_backend(monkeypatch)
        from coolspend.calibration import run_calibration_study
        out_path = str(tmp_path / "calibration_study.json")
        run_calibration_study(n=10, out_path=out_path)
        with open(out_path, encoding="utf-8") as fh:
            data = json.load(fh)
        assert "disclaimer" in data, "artifact missing disclaimer key"

    def test_run_calibration_study_result_fit_keys(self, monkeypatch, tmp_path):
        """run_calibration_study return value contains fit and rank_stability."""
        _ensure_mock_backend(monkeypatch)
        from coolspend.calibration import run_calibration_study
        out_path = str(tmp_path / "result.json")
        result = run_calibration_study(n=10, out_path=out_path)
        assert "fit" in result, "result dict missing 'fit'"
        assert "rank_stability" in result, "result dict missing 'rank_stability'"


# ── Import contract: HOURS_PER_DEGC_REF must be imported ─────────────────────


class TestDimensionalContract:
    def test_hours_per_degc_ref_imported(self):
        """calibration.py imports HOURS_PER_DEGC_REF from coolspend.cost_model.

        This verifies the dimensional contract: the surrogate UTCI prediction
        uses the SAME conversion factor as the KPI (D-04 dimensional validity).
        """
        calibration_path = (
            Path(__file__).resolve().parents[1] / "calibration.py"
        )
        source = calibration_path.read_text(encoding="utf-8")
        assert "HOURS_PER_DEGC_REF" in source, (
            "calibration.py must import HOURS_PER_DEGC_REF from coolspend.cost_model"
        )
        assert "cost_model" in source, (
            "calibration.py must reference coolspend.cost_model for HOURS_PER_DEGC_REF"
        )

    def test_no_independent_conversion_constant(self):
        """calibration.py must not define an independent hours_per_degc constant."""
        calibration_path = (
            Path(__file__).resolve().parents[1] / "calibration.py"
        )
        source = calibration_path.read_text(encoding="utf-8")
        # The module must not reassign the constant with a literal value
        # (e.g. HOURS_PER_DEGC = 200.0 would be a violation)
        import re
        pattern = re.compile(
            r"HOURS_PER_DEGC\s*[=:]\s*\d+",
            re.IGNORECASE,
        )
        # Allow the import line; disallow standalone assignment
        for line in source.splitlines():
            if "import" in line:
                continue  # skip import lines
            if pattern.search(line):
                pytest.fail(
                    f"Independent HOURS_PER_DEGC constant found in calibration.py: {line!r}. "
                    "Import from coolspend.cost_model instead."
                )

    def test_surrogate_pred_uses_hours_per_degc_ref(self, monkeypatch, tmp_path):
        """surrogate_pred_utci_delta_c is derived from utci_hours_above / HOURS_PER_DEGC_REF."""
        _ensure_mock_backend(monkeypatch)
        from coolspend.calibration import run_calibration_study
        out_path = str(tmp_path / "out.json")
        result = run_calibration_study(n=10, out_path=out_path)
        # All preds should be >= 0 (hours_reduced / HOURS_PER_DEGC_REF >= 0)
        for cfg in result["configs"]:
            pred = cfg.get("surrogate_pred_utci_delta_c")
            assert pred is not None
            assert pred >= 0.0, f"surrogate_pred_utci_delta_c is negative: {pred}"


# ── Module-level function existence ─────────────────────────────────────────


class TestFunctionExists:
    def test_generate_study_configs_exists(self):
        from coolspend.calibration import generate_study_configs
        assert callable(generate_study_configs)

    def test_run_calibration_study_exists(self):
        from coolspend.calibration import run_calibration_study
        assert callable(run_calibration_study)

    def test_compute_fit_exists(self):
        from coolspend.calibration import compute_fit
        assert callable(compute_fit)

    def test_rank_stability_exists(self):
        from coolspend.calibration import rank_stability
        assert callable(rank_stability)

    def test_study_seed_constant(self):
        from coolspend.calibration import STUDY_SEED
        assert STUDY_SEED == 42

    def test_n_study_configs_constant(self):
        from coolspend.calibration import N_STUDY_CONFIGS
        assert N_STUDY_CONFIGS == 10
