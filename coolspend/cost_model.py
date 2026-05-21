"""
cost_model.py — Per-tree CapEx + OpEx cost model and euro-per-degC KPI.

CoolSpend — Tree Budget Optimizer (infrared.city SDK Buildathon, Tree Budget track)

Purpose:
    Computes the headline decision metric: euros of tree-planting investment per
    degree Celsius of UTCI street-comfort relief.  This KPI drives the NSGA-II
    ranking in Phase 2 and the allocation display cards in Phase 3.

Constant status:
    CAPEX_PER_TREE_EUR, OPEX_PER_TREE_YEAR_EUR, and OPEX_HORIZON_YEARS are
    DECLARED assumptions (urban street-tree midrange estimates).  They are
    NOT independently verified figures.  Each carries a
    # SOURCE: REQUIRES_VERIFICATION comment.  See MOCKS.md for the ledger row.

    HOURS_PER_DEGC_REF is a documented conversion factor: the number of annual
    UTCI-hours-above-32°C that are considered equivalent to 1°C of mean-UTCI drop.
    Derivation: Barcelona summer strong heat stress (UTCI 32–38°C) has a typical
    mean UTCI excess of ≈3°C above the 32°C threshold.  If the baseline plaza
    accumulates ≈600 h/yr in that band, then 600 / 3 ≈ 200 h per 1°C equivalent.
    This is consistent with the literature note that "12°C Tmrt ≈ 3–5°C UTCI"
    (surrogate ceiling of 12°C Tmrt maps to ≈3–5°C UTCI, and at 20% coverage the
    UTCI-hours reduction is in the 600–1000 h/yr range → equiv_degc ≈ 3–5°C).
    Plan 05-03's calibration module imports HOURS_PER_DEGC_REF BY THIS EXACT NAME
    to re-anchor the constant against empirical RMSE once a calibration artifact
    is available.

KPI uncertainty band (D-10 / VALID-04):
    PRE_CALIBRATION_BAND_C = ±4°C is the assumed surrogate band before empirical
    calibration.  Once Plan 05-03 produces a calibration RMSE, pass it as
    ``band_c`` to cost_per_utci_degree() to replace this assumed band with the
    measured one.  The KPI is always reported as an interval [value_lo, value_hi],
    never as a bare point estimate.

Key functions:
    per_tree_cost(horizon_years) -> float          euros per tree over horizon
    total_cost(config)           -> float          total euros for config
    cost_per_utci_degree(config, band_c) -> dict   standard metric dict EUR/degC
"""
from __future__ import annotations

from typing import Any

# ── Confidence constants ──────────────────────────────────────────────────────
HIGH = "HIGH"
MED  = "MED"
LOW  = "LOW"

# ── CapEx / OpEx constants (DECLARED assumptions — COST-01) ──────────────────
#
# These are midrange estimates for urban street-tree planting programmes.
# Each value is a DECLARED assumption pending sourcing from municipal data.
# Do NOT present these as verified figures.
#
# SOURCE: REQUIRES_VERIFICATION — no municipal procurement data confirmed yet.
# See MOCKS.md row "CapEx/OpEx tree cost constants".
# COST MAGNITUDE FIX: Phase 6 / COST-03 (owner: Phase 6).

CAPEX_PER_TREE_EUR: float = 350.0
# planting: nursery stock + labour + initial irrigation (DECLARED assumption,
# urban street-tree midrange, e.g. Madrid / Barcelona municipal programmes)
# UNIT: EUR per tree   SOURCE: REQUIRES_VERIFICATION

OPEX_PER_TREE_YEAR_EUR: float = 35.0
# annual maintenance: watering, pruning, inspection (DECLARED assumption)
# UNIT: EUR per tree per year   SOURCE: REQUIRES_VERIFICATION

OPEX_HORIZON_YEARS: int = 10
# amortisation horizon for OpEx in the headline KPI (DECLARED assumption)
# UNIT: years   SOURCE: REQUIRES_VERIFICATION

# ── UTCI-hours → equivalent mean-°C conversion factor (Plan 05-03 contract) ──
#
# HOURS_PER_DEGC_REF: annual UTCI-hours-above-32°C reduction equivalent to 1°C
# of mean-UTCI drop.
#
# Derivation (documented):
#   Barcelona strong heat stress band = 32–38°C UTCI.
#   Mean UTCI excess above threshold ≈ 3°C (midpoint of 32–38°C band).
#   Baseline plaza ≈ 600 h/yr in strong heat stress (EPW Barcelona TMYx 2011-2025).
#   600 h/yr ÷ 3°C mean excess ≈ 200 h/yr per 1°C equivalent mean-UTCI drop.
#
#   Cross-check: a 12°C Tmrt surrogate cap at 20% coverage gives ≈600-1000 h/yr
#   UTCI-hours reduction (see nature_metrics.utci_hours_above).  Dividing by 200
#   yields ≈3–5°C UTCI equivalent, consistent with the literature note
#   "12°C Tmrt ≈ 3–5°C UTCI" (STATE.md / Schrodi 2023 surrogate anchor).
#
# Plan 05-03 (calibration module) imports this constant BY EXACT NAME to
# re-anchor it against empirical RMSE once the calibration study is complete.
# SOURCE: derived from EPW Barcelona + literature; REQUIRES_VERIFICATION.

HOURS_PER_DEGC_REF: float = 200.0
# UNIT: annual UTCI-hours-above-32°C per °C equivalent mean-UTCI drop
# SOURCE: derived (Barcelona EPW mean excess + "12°C Tmrt ≈ 3-5°C UTCI" anchor)
# REQUIRES_VERIFICATION: Plan 05-03 replaces with empirical calibration RMSE.

# ── Uncertainty band constants (D-10 / VALID-04) ─────────────────────────────
#
# PRE_CALIBRATION_BAND_C: the assumed surrogate ΔTmrt band before empirical
# calibration.  Replaced by the calibration RMSE from Plan 05-03.
# When band_c=None in cost_per_utci_degree(), this value is used.

PRE_CALIBRATION_BAND_C: float = 4.0
# UNIT: °C   SOURCE: pre-calibration assumed band (not empirically grounded)
# Label used in output: "pre-calibration, assumed ±4°C"
# Replaced by Plan 05-03 calibration RMSE when available.

# ── Numerical guard ───────────────────────────────────────────────────────────
_EPS: float = 1e-6

# ── Internal source tag used in every result dict ─────────────────────────────
_COST_SOURCE = "DECLARED: CapEx/OpEx assumptions (REQUIRES_VERIFICATION)"


# ── Public API ────────────────────────────────────────────────────────────────

def per_tree_cost(horizon_years: int = OPEX_HORIZON_YEARS) -> float:
    """
    Return the total lifecycle cost per tree over *horizon_years*.

    Cost = CAPEX_PER_TREE_EUR + OPEX_PER_TREE_YEAR_EUR * horizon_years.

    With horizon_years=0 only the CapEx (planting cost) is returned; no OpEx
    is amortised.  Uses the module-level DECLARED constants — see module
    docstring for honesty status.

    Returns a finite positive float in EUR.
    """
    return CAPEX_PER_TREE_EUR + OPEX_PER_TREE_YEAR_EUR * horizon_years


def total_cost(config: dict[str, Any]) -> float:
    """
    Return the total planting + maintenance cost for all trees in *config*.

    Reads tree_count = int(config.get("tree_count", 0)).
    If tree_count <= 0 returns 0.0.

    Returns a finite non-negative float in EUR.
    """
    tree_count = int(config.get("tree_count", 0))
    if tree_count <= 0:
        return 0.0
    return tree_count * per_tree_cost()


def cost_per_utci_degree(  # noqa: C901 (complexity OK — linear decision tree)
    config: dict[str, Any],
    band_c: float | None = None,
) -> dict[str, Any]:
    """
    Return the headline euro-per-degC KPI for *config* as a standard metric dict.

    UTCI routing (D-08 / VALID-02):
        The °C denominator is ALWAYS derived from UTCI-hours-above-threshold
        (via nature_metrics.utci_hours_above), never from raw config["delta_tmrt_c"].
        The config["delta_tmrt_c"] field informs coverage_fraction derivation only.

    Prefer-measured rule:
        If config["delta_utci_c"] is a positive float (validated UTCI from Infrared),
        it is used as the °C drop (confidence MED/HIGH).  The UTCI-hours path is
        still called to populate cost_per_utci_hour for dual-unit reporting (D-09).
        Otherwise the equivalent mean-°C drop is derived from the UTCI-hours
        reduction via HOURS_PER_DEGC_REF.

    Dual units (D-09):
        Primary: EUR/degC (equiv mean-UTCI °C drop, preserving v1 framing).
        Secondary: EUR per annual UTCI-hour above 32°C reduced (cost_per_utci_hour).

    Uncertainty interval (D-10 / VALID-04):
        The KPI is reported as an interval [value_lo, value_hi] using band_c.
        value_lo = cost / (degc_drop + band)   — more cooling → cheaper per °C
        value_hi = cost / max(degc_drop - band, EPS) — less cooling → costlier
        If degc_drop - band <= 0, value_hi is None (upper bound unbounded).
        The same proportional band is applied to cost_per_utci_hour_lo/hi via
        HOURS_PER_DEGC_REF scaling.

    Parameters
    ----------
    config : dict
        Must contain tree_count.  May contain:
          - coverage_fraction (0–1): fraction of plaza under canopy.  If absent,
            derived from active trees via spatial_engine.core_weighted_coverage_fraction.
          - delta_utci_c: validated UTCI delta (°C) from real/cached Infrared.
            If positive, used as the °C drop (prefer-measured rule).
          - delta_tmrt_c: surrogate Tmrt delta (°C).  NEVER used as KPI denominator.
    band_c : float | None
        Empirical calibration RMSE (°C) from Plan 05-03.  If None, falls back to
        PRE_CALIBRATION_BAND_C (4.0°C) labelled "pre-calibration, assumed ±4°C".

    Zero / negative delta guard (T-01-10 / Rule 6 honest framing):
        If the UTCI-hours reduction is None, zero, or negative (no comfort gain),
        value=None is returned with confidence LOW and an explanatory note.
        The prefer-measured path is still attempted when delta_utci_c is present.

    Returns a standard metric dict with keys:
        value, value_lo, value_hi, unit, confidence, sources, note, metric_id,
        utci_hours_reduced, cost_per_utci_hour, cost_per_utci_hour_lo,
        cost_per_utci_hour_hi, utci_hours_unit, band_c, band_source.
    """
    # ── Band setup ─────────────────────────────────────────────────────────────
    if band_c is None:
        band = PRE_CALIBRATION_BAND_C
        band_source = "pre-calibration, assumed ±4°C"
    else:
        band = float(band_c)
        band_source = f"empirical calibration RMSE ±{band:.2f}°C"

    # ── Coverage fraction ──────────────────────────────────────────────────────
    cov = config.get("coverage_fraction")
    if cov is None:
        try:
            from coolspend.spatial_engine import core_weighted_coverage_fraction  # noqa: PLC0415
            active_trees = [t for t in config.get("trees", []) if t.get("active", True)]
            cov = core_weighted_coverage_fraction(active_trees)
        except Exception:  # noqa: BLE001
            cov = 0.0  # safe fallback — no coverage info → baseline UTCI

    cov = float(cov) if cov is not None else 0.0

    # ── UTCI-hours routing (D-08) ──────────────────────────────────────────────
    hours_reduced: float | None = None
    utci_hours_note: str = ""

    try:
        from nature_metrics import utci_hours_above  # noqa: PLC0415
        uh = utci_hours_above(32.0, cov)
        if "error" in uh or uh.get("value") is None:
            utci_hours_note = "UTCI-hours unavailable (EPW missing)"
        else:
            raw_delta = uh.get("delta", 0.0)
            # delta is negative (reduction); flip sign to positive hours_reduced
            hours_reduced = float(-raw_delta) if raw_delta is not None else None
            if hours_reduced is not None and hours_reduced < 0:
                hours_reduced = 0.0  # guard: should not happen but be safe
    except Exception as exc:  # noqa: BLE001
        utci_hours_note = f"UTCI-hours unavailable ({exc})"

    # ── Determine °C drop and confidence ──────────────────────────────────────
    note_parts: list[str] = []
    degc_drop: float | None = None
    confidence = LOW

    measured_delta = config.get("delta_utci_c")
    if isinstance(measured_delta, (int, float)) and float(measured_delta) > 0:
        # Prefer-measured path: validated Infrared UTCI delta
        degc_drop = float(measured_delta)
        confidence = MED  # MED because cost constants are still DECLARED
    elif hours_reduced is not None and hours_reduced > 0:
        # UTCI-hours-derived path (D-08): never raw Tmrt
        degc_drop = hours_reduced / HOURS_PER_DEGC_REF
        note_parts.append(
            "UTCI-hours→equiv mean-°C conversion (documented, surrogate-derived; "
            f"hours_reduced={hours_reduced:.1f} / HOURS_PER_DEGC_REF={HOURS_PER_DEGC_REF})"
        )
        confidence = LOW

    if utci_hours_note:
        note_parts.append(utci_hours_note)

    # ── Zero / negative delta guard (T-01-10) ─────────────────────────────────
    if degc_drop is None or degc_drop <= 0:
        if not note_parts:
            if hours_reduced is not None and hours_reduced <= 0:
                note_parts.append(
                    f"UTCI-hours reduction is {hours_reduced} h/yr (no comfort gain) — "
                    "KPI undefined"
                )
            else:
                note_parts.append(
                    "No positive UTCI-hours reduction and no validated delta_utci_c — "
                    "cannot compute EUR/degC KPI"
                )
        return {
            "value": None,
            "value_lo": None,
            "value_hi": None,
            "unit": "EUR/degC",
            "confidence": LOW,
            "sources": [_COST_SOURCE],
            "note": "; ".join(note_parts),
            "metric_id": "cost_per_utci_degree",
            "utci_hours_reduced": hours_reduced,
            "cost_per_utci_hour": None,
            "cost_per_utci_hour_lo": None,
            "cost_per_utci_hour_hi": None,
            "utci_hours_unit": "EUR / annual UTCI-hour above 32°C reduced",
            "band_c": band,
            "band_source": band_source,
        }

    # ── Compute primary KPI (€/°C) ────────────────────────────────────────────
    cost = total_cost(config)
    value = round(cost / degc_drop, 2)

    # Interval propagation: band on °C drop (D-10)
    # More cooling (degc_drop + band) → cheaper per °C → lower bound
    value_lo = round(cost / (degc_drop + band), 2)
    degc_minus_band = degc_drop - band
    if degc_minus_band <= _EPS:
        value_hi = None  # upper bound unbounded — band exceeds estimate
        note_parts.append("upper bound unbounded (band exceeds °C estimate)")
    else:
        value_hi = round(cost / degc_minus_band, 2)

    # ── Compute secondary KPI (€/UTCI-hour) ──────────────────────────────────
    cost_per_utci_hour: float | None = None
    cost_per_utci_hour_lo: float | None = None
    cost_per_utci_hour_hi: float | None = None

    if hours_reduced is not None and hours_reduced > 0:
        cost_per_utci_hour = round(cost / hours_reduced, 2)
        # Propagate band into hours via HOURS_PER_DEGC_REF
        hours_band = band * HOURS_PER_DEGC_REF
        hours_hi = hours_reduced + hours_band  # more hours → cheaper per hour
        hours_lo = hours_reduced - hours_band  # fewer hours → costlier per hour
        cost_per_utci_hour_lo = round(cost / hours_hi, 2)
        if hours_lo <= _EPS:
            cost_per_utci_hour_hi = None  # upper bound unbounded
        else:
            cost_per_utci_hour_hi = round(cost / hours_lo, 2)

    # ── Build note ────────────────────────────────────────────────────────────
    note_parts.append(
        f"KPI interval [value_lo={value_lo}, value={value}, value_hi={value_hi}] "
        f"EUR/degC; band={band_source}. "
        "Delta is UTCI (routed through utci_hours_above), never raw Tmrt (D-08). "
        "Both units: EUR/degC (primary) and EUR/annual-UTCI-hour (secondary, D-09). "
        "Interval is never a bare point estimate (D-10/VALID-04). "
        "KNOWN MOCK DEBT: CAPEX_PER_TREE_EUR=350/OPEX placeholders — "
        "magnitude fix is Phase 6 / COST-03."
    )

    return {
        "value": value,
        "value_lo": value_lo,
        "value_hi": value_hi,
        "unit": "EUR/degC",
        "confidence": confidence,
        "sources": [_COST_SOURCE],
        "note": "; ".join(note_parts),
        "metric_id": "cost_per_utci_degree",
        "utci_hours_reduced": hours_reduced,
        "cost_per_utci_hour": cost_per_utci_hour,
        "cost_per_utci_hour_lo": cost_per_utci_hour_lo,
        "cost_per_utci_hour_hi": cost_per_utci_hour_hi,
        "utci_hours_unit": "EUR / annual UTCI-hour above 32°C reduced",
        "band_c": band,
        "band_source": band_source,
    }


# ── Smoke test / integration sample ──────────────────────────────────────────

if __name__ == "__main__":
    import json

    sample_config = {"tree_count": 20, "coverage_fraction": 0.20, "delta_utci_c": 0.42}

    print("=== cost_model.py smoke test ===")
    print(f"per_tree_cost()        = {per_tree_cost():.2f} EUR")
    print(f"per_tree_cost(0)       = {per_tree_cost(0):.2f} EUR  (CapEx only)")
    print(f"total_cost(20 trees)   = {total_cost(sample_config):.2f} EUR")
    print()
    result = cost_per_utci_degree(sample_config)
    print("cost_per_utci_degree result:")
    print(json.dumps(result, indent=2))
    print()

    # Demonstrate zero-delta guard
    zero_delta_result = cost_per_utci_degree({"tree_count": 10, "coverage_fraction": 0.0})
    print("Zero-delta guard result (coverage=0):")
    print(json.dumps(zero_delta_result, indent=2))
    print()

    # Demonstrate pre-calibration band
    band_result = cost_per_utci_degree(sample_config)
    print("Pre-calibration band result:")
    print(f"  band_source: {band_result['band_source']}")
    print(f"  value_lo: {band_result['value_lo']}, value: {band_result['value']}, "
          f"value_hi: {band_result['value_hi']}")
