"""
cost_model.py — Per-tree CapEx + OpEx cost model and euro-per-degC KPI.

CoolSpend — Tree Budget Optimizer (infrared.city SDK Buildathon, Tree Budget track)

Purpose:
    Computes the headline decision metric: euros of tree-planting investment per
    degree Celsius of UTCI street-comfort relief.  This KPI drives the NSGA-II
    ranking in Phase 2 and the allocation display cards in Phase 3.

Constant status (Phase 6 / COST-03 — itemized CostTable):
    CAPEX_PER_TREE_EUR, OPEX_PER_TREE_YEAR_EUR, and OPEX_HORIZON_YEARS are now
    DERIVED from DEFAULT_COST_TABLE (single source of truth — D-15).  They are
    preserved as module-level names for backward compatibility; do NOT redefine
    them independently.  See MOCKS.md cost-line ledger for per-line source tags.

    Default values: CapEx ≈ €2,200/tree (fully loaded — vs old €350 which was
    ~6× too low); OpEx ≈ €60/tree/yr; horizon = 40 yr (D-09: tree functional
    lifespan, urban sealed-site context).

    Lifecycle cost literature context (PENDING — paywalled, cited venue only):
    German 5-city life-cycle study (Riegel / ScienceDirect 2025) — sealed-pit
    payback ≈34 yrs, discount-rate-sensitive.  Barcelona-specific procurement =
    PENDING; defaults are labelled "illustrative European mid-range, verify
    locally".  User supplies local figures via the editable CostTable (Plan 06-03
    / COST-04).

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

Growth-horizon discount (COST-05 / D-07..D-10):
    A tree does not deliver full-canopy cooling on day one.  Counting day-one full
    benefit overstates cooling and understates €/°C.  The following three functions
    implement an auditable growth-ramp + social-discount model:

    1. growth_cooling_fraction(year, p) — linear ramp (D-07 / MODELLING CHOICE):
       A linear ramp was chosen over logistic or exponential for auditability; any
       auditor can verify the numbers without specialist ecological modelling.
         frac(y) = p.initial_fraction + (1 - p.initial_fraction) * min(y / p.ramp_years, 1.0)
       At year 0  → p.initial_fraction (≈20% cooling from young tree shade).
       At year 25 → 1.0 (full-canopy cooling, clamped to 1.0 thereafter).

    2. discounted_lifetime_degc(full_canopy_degc, p) — annual summation (D-10 / MODELLING CHOICE):
       A closed-form discount integral exists but annual summation was chosen for
       auditability — each year's contribution can be inspected in a spreadsheet.
       For each year y in 0..(horizon_years-1):
         weight_y   = growth_cooling_fraction(y, p) / (1 + r)^y
         disc_year  = 1 / (1 + r)^y
       Returns: full_canopy_degc * (Σ weight_y / Σ disc_year_y)
       This is the discounted-weighted *average* cooling fraction times the full
       canopy °C, i.e. an "equivalent steady-state °C drop" (D-10).  Routing this
       value into the KPI denominator keeps units in €/°C and the [lo,hi] band
       propagates cleanly.

    3. discounted_total_cost(config, p) — present value of lifecycle cost (D-08):
       CapEx (year 0, undiscounted) + PV(OpEx over horizon at rate r) × tree_count.
       Used only in the REPORTED KPI; the optimizer's budget constraint continues
       to use total_cost() (nominal) for NSGA-II feasibility (Do NOT change).

    See GrowthDiscountParams for editable defaults; Plan 06-03 (COST-04) exposes
    these via Gradio inputs.

    DECLARED modelling choices (REQUIRES_VERIFICATION):
      - Linear ramp shape (not calibrated growth model); species-specific canopy
        growth would replace this (i-Tree or local arboricultural data).
      - 3.5% discount rate = EU/UK Green Book social convention; locale-editable.
      - 40-yr horizon = urban sealed-site functional lifespan; locale-editable.

Key functions:
    per_tree_cost(horizon_years) -> float             euros per tree over horizon
    total_cost(config)           -> float             total euros for config
    growth_cooling_fraction(year, p) -> float         ramp fraction at year y
    discounted_lifetime_degc(full_canopy_degc, p) -> float  equiv discounted °C
    discounted_total_cost(config, p) -> float         PV of lifecycle cost
    cost_per_utci_degree(config, band_c, growth_discount) -> dict  EUR/degC KPI
"""
from __future__ import annotations

import json
import logging
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_log = logging.getLogger(__name__)

# ── Confidence constants ──────────────────────────────────────────────────────
HIGH = "HIGH"
MED  = "MED"
LOW  = "LOW"

# Phase 6 / COST-03 confidence tags for cost-line audit trail (D-04)
VERIFIED = "VERIFIED"  # cited, independently confirmed
DECLARED = "DECLARED"  # named source anchor + reasonable magnitude, not locally verified
PENDING  = "PENDING"   # source identified but unconfirmed / paywalled / region-mismatch


# ── CostLine / CostTable dataclasses (COST-03 / D-01..D-04) ─────────────────

@dataclass(frozen=True)
class CostLine:
    """One itemized lifecycle cost line (CapEx or OpEx)."""

    key: str          # machine key, e.g. "tree_stock"
    label: str        # human label, e.g. "Tree stock (large-caliper nursery)"
    value: float      # EUR (CapEx lines) or EUR/yr (opex line)
    unit: str         # "EUR/tree" | "EUR/tree/yr"
    kind: str         # "capex" | "opex"
    source: str       # named source anchor — NO fabricated DOIs
    confidence: str   # VERIFIED | DECLARED | PENDING


@dataclass
class CostTable:
    """
    Editable per-tree lifecycle cost table (COST-03 / D-05).

    Plan 06-03 (COST-04) loads and edits this via a JSON config and Gradio
    inputs; the KPI recomputes live from the edited values.

    label describes the default provenance — "illustrative European mid-range —
    verify locally" — so it is never mistaken for verified local procurement.
    """

    lines: list[CostLine]
    label: str = "illustrative European mid-range — verify locally"

    def capex_total(self) -> float:
        """Sum of all CapEx line values (EUR/tree)."""
        return sum(l.value for l in self.lines if l.kind == "capex")

    def opex_per_year(self) -> float:
        """Sum of all OpEx line values (EUR/tree/yr)."""
        return sum(l.value for l in self.lines if l.kind == "opex")

    def per_tree_cost(self, horizon_years: int) -> float:
        """
        Total lifecycle cost per tree over *horizon_years*.

        = capex_total() + opex_per_year() * horizon_years.
        horizon_years=0 returns CapEx only.
        """
        return self.capex_total() + self.opex_per_year() * horizon_years


# ── DEFAULT_COST_TABLE — Barcelona-anchored lifecycle costs (D-02/D-03) ─────
#
# 2026-05-27: OpEx VERIFIED against BCN IMPJ 2023 activity-based costing
# (€61.28/tree/yr → rounded to €60 for clean benchmark).  CapEx anchored to
# Diputació de Barcelona replacement grant (€500/tree, existing alcorques)
# scaled up for NEW pit construction (pavement break + structural soil).
# Individual CapEx line items are DECLARED (BCN-tender-consistent but not
# directly extracted from a published unit-price schedule).  Editable via
# cost_config.json or Gradio CostTable inputs (Plan 06-03 / COST-04).
#
# CapEx lines (5 lines, sum = 2200.0 EUR/tree for NEW pit construction):
#   tree_stock       600.0  DECLARED  BCN Verd Urbà large-caliper (20–25 cm)
#   pit_excavation   500.0  DECLARED  BCN pavement-cut + excavation, new alcorque
#   structural_soil  600.0  DECLARED  structural sand/soil 6–8 m³ installed
#   guarding         200.0  VERIFIED  Diputació BCN grant staking+guard component
#   planting_labour  300.0  VERIFIED  Diputació BCN grant labour component
#
# OpEx line (1 line, sum = 60.0 EUR/tree/yr):
#   annual_opex       60.0  VERIFIED  BCN IMPJ Activity 0214 (2023):
#     €12,658,229 / 206,556 trees = €61.28/tree/yr (pruning, watering,
#     health inspections, pest control, risk assessment)

DEFAULT_COST_TABLE: CostTable = CostTable(
    label="Barcelona-anchored — new pit construction (Diputació grant floor + soil + excavation)",
    lines=[
        CostLine(
            key="tree_stock",
            label="Tree stock (large-caliper nursery, 20–25 cm circ.)",
            value=600.0,
            unit="EUR/tree",
            kind="capex",
            source=(
                "Barcelona Verd Urbà / viver municipal large-caliper nursery stock; "
                "consistent with Diputació de Barcelona replacement grant tree component "
                "(€500/tree total replacement bundle for 16–18 cm stock); "
                "PENDING direct BCN tender unit-price extraction"
            ),
            confidence=DECLARED,
        ),
        CostLine(
            key="pit_excavation",
            label="Pit excavation and preparation (new alcorque)",
            value=500.0,
            unit="EUR/tree",
            kind="capex",
            source=(
                "Barcelona pavement cut + excavation for new tree pit (2×2×1.2 m); "
                "scaled from BCN municipal construction benchmarks and tender 23/0157 "
                "works component; PENDING direct BCN tender unit-price extraction"
            ),
            confidence=DECLARED,
        ),
        CostLine(
            key="structural_soil",
            label="Structural soil / sand mix (installed)",
            value=600.0,
            unit="EUR/tree",
            kind="capex",
            source=(
                "Structural soil/sand mix for new pit (~€80–100/m³ installed × 6–8 m³); "
                "BCN standard practice per Pla Director de l'Arbrat; "
                "PENDING direct BCN soil-cell tender unit-price extraction"
            ),
            confidence=DECLARED,
        ),
        CostLine(
            key="guarding",
            label="Guarding, staking, and aeration tube",
            value=200.0,
            unit="EUR/tree",
            kind="capex",
            source=(
                "Diputació de Barcelona street tree replacement grant (Catàleg 2024–2027) "
                "includes staking system + aeration tube within €500/tree bundle; "
                "BCN metal tree guard (escorxador) + 2–3 stakes + drip ring"
            ),
            confidence=VERIFIED,
        ),
        CostLine(
            key="planting_labour",
            label="Planting labour",
            value=300.0,
            unit="EUR/tree",
            kind="capex",
            source=(
                "Diputació de Barcelona replacement grant labour component; "
                "consistent with BCN tender 23/0157 direct labour breakdown "
                "(€49,797.60 salaries component of €518,448.70 total)"
            ),
            confidence=VERIFIED,
        ),
        CostLine(
            key="annual_opex",
            label="Annual maintenance (pruning, watering, inspection, pest control)",
            value=60.0,
            unit="EUR/tree/yr",
            kind="opex",
            source=(
                "Barcelona IMPJ Activity 0214 — Arbrat Viari (2023): "
                "€12,658,229 total / 206,556 street trees = €61.28/tree/yr "
                "(rounded to €60). Includes pruning (poda), watering (reg), "
                "health inspections (avaluació de risc cada 2 anys), "
                "pest treatments (tractaments fitosanitaris), and replacement. "
                "Source: Ajuntament de Barcelona activity-based costing, "
                "BCN_MC23 (Management Indicators by Activity)."
            ),
            confidence=VERIFIED,
        ),
    ],
)

# ── CapEx / OpEx constants (D-15 backward-compat — DERIVED from CostTable) ──
#
# These names are preserved for all existing callers (optimizer.py, tests, app).
# They are NOT independent constants — they mirror DEFAULT_COST_TABLE so there
# is ONE source of truth.  Do NOT hardcode new values here; edit CostTable.

CAPEX_PER_TREE_EUR: float = DEFAULT_COST_TABLE.capex_total()
# DERIVED from DEFAULT_COST_TABLE.capex_total() — currently 2200.0 EUR/tree
# (was 350.0 — that figure covered only stock+labour, ~6× low fully-loaded)
# UNIT: EUR per tree   SOURCE: see DEFAULT_COST_TABLE lines

OPEX_PER_TREE_YEAR_EUR: float = DEFAULT_COST_TABLE.opex_per_year()
# DERIVED from DEFAULT_COST_TABLE.opex_per_year() — currently 60.0 EUR/tree/yr
# (was 35.0 — replaced by itemized fully-loaded annual maintenance)
# UNIT: EUR per tree per year   SOURCE: see DEFAULT_COST_TABLE "annual_opex" line

OPEX_HORIZON_YEARS: int = 40
# Tree functional lifespan in urban sealed-site context (D-09).
# CHANGED from 10 yr (was: amortisation shorthand) to 40 yr (documented lifespan).
# UNIT: years   SOURCE: D-09 functional lifespan convention

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
# ROLE: documented FALLBACK only. The live value is computed from the in-repo
# Barcelona TMYx EPW by hours_per_degc() below; this literal is used only when
# the EPW / ladybug are unavailable.
# NOTE (2026-05-31): the EPW-derived value is ~47 h/°C (band-mean 0.5–2°C),
# NOT 200 — the 200 figure assumed a 600 h/yr baseline, but the EPW baseline at
# UTCI>32°C is 98 h/yr. The live calibration study (calibration.py, surrogate-
# vs-measured RMSE) is the definitive arbiter; hours_per_degc() supersedes 200.

_HOURS_PER_DEGC_CACHE: dict[str, float] = {}


def hours_per_degc(threshold_c: float = 32.0) -> float:
    """EPW-derived hours-above-threshold removed per °C uniform UTCI cooling.

    Computed once from the Barcelona TMYx EPW (cached); falls back to the
    documented HOURS_PER_DEGC_REF literal if the EPW/ladybug are unavailable.
    Replaces the former hand-derived REQUIRES_VERIFICATION constant.
    """
    key = f"hpd_{threshold_c}"
    if key in _HOURS_PER_DEGC_CACHE:
        return _HOURS_PER_DEGC_CACHE[key]
    value = HOURS_PER_DEGC_REF
    try:
        from nature_metrics import hours_per_degc_uniform_shift  # noqa: PLC0415

        r = hours_per_degc_uniform_shift(threshold_c)
        if r.get("value"):
            value = float(r["value"])
    except Exception:  # noqa: BLE001 — EPW/ladybug optional; fall back to literal
        pass
    _HOURS_PER_DEGC_CACHE[key] = value
    return value

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
_COST_SOURCE = (
    "Barcelona-anchored CostTable lifecycle cost (Phase 6 / COST-03); "
    "OpEx VERIFIED (BCN IMPJ 2023 activity-based costing); "
    "CapEx DECLARED (anchored to Diputació de Barcelona grant + scaled for new-pit construction); "
    "see DEFAULT_COST_TABLE lines for per-item source anchors and MOCKS.md ledger"
)


# ── GrowthDiscountParams — editable growth-curve + discount params (COST-05) ─

@dataclass
class GrowthDiscountParams:
    """
    Editable growth-curve + discounting parameters (COST-05 / D-07..D-09).

    All three fields are user-editable via Gradio inputs (Plan 06-03 / COST-04).
    Defaults represent DECLARED modelling choices — REQUIRES_VERIFICATION against
    local species data and municipal finance guidance (see MOCKS.md).
    """
    ramp_years: float = 25.0
    # D-07: establishment→maturity duration (years).
    # DECLARED: linear ramp shape is a modelling choice for auditability.
    # UNIT: years   SOURCE: urban arboricultural context (illustrative)
    # REQUIRES_VERIFICATION: replace with species-specific canopy growth curve
    #   from i-Tree or local arboricultural data.

    initial_fraction: float = 0.20
    # D-07: effective cooling fraction at planting (year 0).
    # Young tree provides ~20% of full-canopy cooling via partial shade.
    # DECLARED   REQUIRES_VERIFICATION.

    discount_rate: float = 0.035
    # D-08: social discount rate — EU / UK Green Book convention (3.5%/yr).
    # Editable per locale; see MOCKS.md.
    # DECLARED   SOURCE: EU / UK HM Treasury Green Book (2022)

    horizon_years: int = 40
    # D-09: tree functional lifespan in urban sealed-site context.
    # DECLARED   SOURCE: German 5-city LCC study (Riegel/ScienceDirect 2025,
    #   venue-only PENDING) + urban tree lifespan literature.
    # REQUIRES_VERIFICATION: local tree-survival / lifespan data.


DEFAULT_GROWTH_DISCOUNT: "GrowthDiscountParams" = GrowthDiscountParams()
# Single-source default instance — used when cost_per_utci_degree receives
# growth_discount=None (backward-compat default).


# ── JSON config helpers (COST-04 / D-05) — load + validate ───────────────────

_VALID_CONFIDENCE = {"VERIFIED", "DECLARED", "PENDING"}
_REQUIRED_LINE_KEYS = {"key", "label", "value", "unit", "kind", "source", "confidence"}
_VALID_KINDS = {"capex", "opex"}

_DEFAULT_CONFIG_PATH = Path(__file__).parent / "cost_config.json"


def cost_table_from_dict(d: dict) -> "tuple[CostTable, GrowthDiscountParams]":
    """Build a CostTable + GrowthDiscountParams from a parsed JSON dict.

    Falls back to DEFAULT_COST_TABLE / DEFAULT_GROWTH_DISCOUNT for any
    missing or malformed field (fail-open — D-05 / T-06-07).

    Validates:
      - Each line has all required keys: key, label, value, unit, kind, source, confidence
      - confidence in {VERIFIED, DECLARED, PENDING}
      - value is a finite positive number (negative/zero gets replaced with default)
      - kind in {capex, opex}

    Parameters
    ----------
    d : dict  Parsed JSON dict (from cost_config.json or user-edited dict).

    Returns
    -------
    (CostTable, GrowthDiscountParams)  Validated pair; any missing/invalid
    fields fall back to DEFAULT_COST_TABLE / DEFAULT_GROWTH_DISCOUNT values.
    """
    # Build a lookup from the default table so we can fall back per-line
    default_by_key = {line.key: line for line in DEFAULT_COST_TABLE.lines}

    raw_lines = d.get("lines", [])
    built_lines: list[CostLine] = []

    for i, raw in enumerate(raw_lines):
        if not isinstance(raw, dict):
            _log.warning("cost_table_from_dict: line[%d] is not a dict — skipping", i)
            continue

        missing = _REQUIRED_LINE_KEYS - raw.keys()
        if missing:
            _log.warning(
                "cost_table_from_dict: line[%d] missing keys %s — skipping", i, missing
            )
            continue

        key = str(raw["key"])
        label = str(raw["label"])
        source = str(raw["source"])

        # confidence validation (T-06-07)
        confidence = str(raw["confidence"])
        if confidence not in _VALID_CONFIDENCE:
            _log.warning(
                "cost_table_from_dict: line '%s' confidence '%s' not in %s — "
                "falling back to default line",
                key, confidence, _VALID_CONFIDENCE,
            )
            if key in default_by_key:
                built_lines.append(default_by_key[key])
                continue
            confidence = "DECLARED"  # safe fallback if key not in defaults

        # kind validation
        kind = str(raw["kind"])
        if kind not in _VALID_KINDS:
            _log.warning(
                "cost_table_from_dict: line '%s' kind '%s' not in %s — skipping",
                key, kind, _VALID_KINDS,
            )
            continue

        # value validation: must be a finite positive number
        try:
            value = float(raw["value"])
        except (TypeError, ValueError):
            _log.warning(
                "cost_table_from_dict: line '%s' value %r is not numeric — "
                "falling back to default",
                key, raw["value"],
            )
            value = default_by_key[key].value if key in default_by_key else 0.0

        if value <= 0:
            _log.warning(
                "cost_table_from_dict: line '%s' value %.4f is non-positive — "
                "falling back to default",
                key, value,
            )
            value = default_by_key[key].value if key in default_by_key else 0.0

        unit = str(raw["unit"])

        built_lines.append(
            CostLine(
                key=key,
                label=label,
                value=value,
                unit=unit,
                kind=kind,
                source=source,
                confidence=confidence,
            )
        )

    # If no lines were successfully parsed, fall back entirely to defaults
    if not built_lines:
        _log.warning(
            "cost_table_from_dict: no valid lines parsed — returning DEFAULT_COST_TABLE"
        )
        built_lines = list(DEFAULT_COST_TABLE.lines)

    table_label = d.get("label", DEFAULT_COST_TABLE.label)
    cost_table = CostTable(lines=built_lines, label=str(table_label))

    # ── GrowthDiscountParams ────────────────────────────────────────────────────
    raw_gd = d.get("growth_discount", {})
    if not isinstance(raw_gd, dict):
        raw_gd = {}

    def _float_or(val, default: float) -> float:
        try:
            result = float(val)
            return result if result > 0 else default
        except (TypeError, ValueError):
            return default

    def _int_or(val, default: int) -> int:
        try:
            result = int(float(val))
            return result if result > 0 else default
        except (TypeError, ValueError):
            return default

    gd = GrowthDiscountParams(
        ramp_years=_float_or(raw_gd.get("ramp_years"), DEFAULT_GROWTH_DISCOUNT.ramp_years),
        initial_fraction=_float_or(
            raw_gd.get("initial_fraction"), DEFAULT_GROWTH_DISCOUNT.initial_fraction
        ),
        discount_rate=_float_or(raw_gd.get("discount_rate"), DEFAULT_GROWTH_DISCOUNT.discount_rate),
        horizon_years=_int_or(raw_gd.get("horizon_years"), DEFAULT_GROWTH_DISCOUNT.horizon_years),
    )

    return cost_table, gd


def load_cost_table(path: str | None = None) -> "tuple[CostTable, GrowthDiscountParams]":
    """Load coolspend/cost_config.json (or *path*) and return (CostTable, GrowthDiscountParams).

    Fail-open: on missing or invalid file, logs a warning and returns
    (DEFAULT_COST_TABLE, DEFAULT_GROWTH_DISCOUNT) — never raises (D-05 / T-06-08).

    Parameters
    ----------
    path : str | None
        Path to a JSON config file.  If None, uses the bundled
        ``cost_config.json`` next to this module file.

    Returns
    -------
    (CostTable, GrowthDiscountParams)
    """
    config_path = Path(path) if path is not None else _DEFAULT_CONFIG_PATH
    try:
        text = config_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        _log.warning(
            "load_cost_table: config file not found at '%s' — using DEFAULT_COST_TABLE",
            config_path,
        )
        return DEFAULT_COST_TABLE, DEFAULT_GROWTH_DISCOUNT
    except OSError as exc:
        _log.warning(
            "load_cost_table: cannot read '%s' (%s) — using DEFAULT_COST_TABLE",
            config_path, exc,
        )
        return DEFAULT_COST_TABLE, DEFAULT_GROWTH_DISCOUNT

    try:
        d = json.loads(text)
    except json.JSONDecodeError as exc:
        _log.warning(
            "load_cost_table: invalid JSON in '%s' (%s) — using DEFAULT_COST_TABLE",
            config_path, exc,
        )
        return DEFAULT_COST_TABLE, DEFAULT_GROWTH_DISCOUNT

    if not isinstance(d, dict):
        _log.warning(
            "load_cost_table: JSON root in '%s' is not an object — using DEFAULT_COST_TABLE",
            config_path,
        )
        return DEFAULT_COST_TABLE, DEFAULT_GROWTH_DISCOUNT

    return cost_table_from_dict(d)


# ── Growth-ramp + discount functions (COST-05 / D-07..D-10) ──────────────────

def growth_cooling_fraction(year: float, p: GrowthDiscountParams) -> float:
    """
    Effective cooling fraction in *year* years since planting.

    Linear ramp from p.initial_fraction at year 0 to 1.0 at p.ramp_years,
    clamped to 1.0 beyond ramp_years (D-07).

    Modelling choice: linear ramp was chosen over logistic for auditability —
    each year's contribution can be verified in a plain spreadsheet.

    Parameters
    ----------
    year  : float  Years since planting (0 = planting year).
    p     : GrowthDiscountParams

    Returns
    -------
    float  in [p.initial_fraction, 1.0]
    """
    frac = p.initial_fraction + (1.0 - p.initial_fraction) * min(year / p.ramp_years, 1.0)
    return min(frac, 1.0)


def discounted_lifetime_degc(full_canopy_degc: float, p: GrowthDiscountParams) -> float:
    """
    Present-value-weighted equivalent °C drop over the tree's functional lifespan.

    Computes the discounted-weighted *average* cooling fraction times
    full_canopy_degc.  The result is an "equivalent steady-state °C drop" (D-10):
    routing this into the KPI denominator keeps units in €/°C and the [lo,hi]
    band propagates cleanly.

    Annual summation (closed-form avoided for auditability — D-10 MODELLING CHOICE):
      For y in 0..(horizon_years-1):
        weight_y  = growth_cooling_fraction(y, p) / (1 + r)^y
        disc_y    = 1 / (1 + r)^y
      Returns: full_canopy_degc * (Σ weight_y / Σ disc_y)

    Parameters
    ----------
    full_canopy_degc : float  °C drop at full-canopy maturity (day-one assumption
                              is replaced by this discounted equivalent).
    p                : GrowthDiscountParams

    Returns
    -------
    float  Discounted-lifetime equivalent mean-°C drop, in (0, full_canopy_degc].
    """
    total_weight = 0.0
    total_disc = 0.0
    r = p.discount_rate
    for y in range(p.horizon_years):
        disc_factor = (1.0 + r) ** y
        total_weight += growth_cooling_fraction(y, p) / disc_factor
        total_disc += 1.0 / disc_factor
    if total_disc <= 0.0:  # guard: should never occur with horizon_years >= 1
        return full_canopy_degc * p.initial_fraction
    return full_canopy_degc * (total_weight / total_disc)


def discounted_total_cost(
    config: dict,
    p: GrowthDiscountParams,
    cost_table: "CostTable | None" = None,
) -> float:
    """
    Present value of the full lifecycle cost for all trees in *config*.

    CapEx (year 0, undiscounted) + PV(OpEx over horizon_years at rate r),
    multiplied by tree_count.

    IMPORTANT: This is used for the REPORTED KPI only.  The optimizer's NSGA-II
    budget constraint uses total_cost() (nominal, no discounting) for NSGA-II
    feasibility — do NOT change the optimizer path.

    Parameters
    ----------
    config      : dict  Must contain tree_count.
    p           : GrowthDiscountParams
    cost_table  : CostTable | None
        Edited cost table to use for the KPI numerator.  If None, falls back
        to DEFAULT_COST_TABLE (backward-compat — D-15 / COST-04).

    Returns
    -------
    float  Total present-value lifecycle cost in EUR.
    """
    tree_count = int(config.get("tree_count", 0))
    if tree_count <= 0:
        return 0.0
    ct = cost_table if cost_table is not None else DEFAULT_COST_TABLE
    capex = ct.capex_total()  # year-0, undiscounted
    opex_pv = sum(
        ct.opex_per_year() / (1.0 + p.discount_rate) ** y
        for y in range(p.horizon_years)
    )
    return tree_count * (capex + opex_pv)


# ── Public API ────────────────────────────────────────────────────────────────

def per_tree_cost(horizon_years: int = OPEX_HORIZON_YEARS) -> float:
    """
    Return the total lifecycle cost per tree over *horizon_years*.

    Delegates to DEFAULT_COST_TABLE.per_tree_cost(horizon_years).
    With horizon_years=0 only the CapEx (planting cost) is returned; no OpEx
    is amortised.

    Backward-compatible: callers that used CAPEX_PER_TREE_EUR / OPEX_PER_TREE_YEAR_EUR
    directly still work because those constants are now derived from the same table.

    Returns a finite positive float in EUR.
    """
    return DEFAULT_COST_TABLE.per_tree_cost(horizon_years)


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
    growth_discount: "GrowthDiscountParams | None" = None,
    cost_table: "CostTable | None" = None,
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

    Growth-horizon discount (COST-05 / D-07..D-10):
        The °C denominator is routed through discounted_lifetime_degc() so the
        KPI reflects the equivalent discounted-lifetime °C drop (not day-one full
        canopy).  The cost numerator uses discounted_total_cost() (PV of OpEx).
        The optimizer's NSGA-II budget constraint uses total_cost() (nominal) and
        is NOT affected by this parameter.

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
    growth_discount : GrowthDiscountParams | None
        Growth-curve + discount parameters (COST-05 / D-07..D-09).  If None,
        uses DEFAULT_GROWTH_DISCOUNT (ramp_years=25, initial_fraction=0.20,
        discount_rate=3.5%, horizon_years=40).  Pass a custom instance to
        override any parameter (Plan 06-03 / COST-04 exposes these via Gradio).
    cost_table : CostTable | None
        Edited per-city cost table (COST-04 / D-05).  When supplied, both
        the CapEx and OpEx from this table are used in the KPI numerator
        (via discounted_total_cost).  When None, falls back to DEFAULT_COST_TABLE
        (backward-compat — existing callers unchanged).

    Zero / negative delta guard (T-01-10 / Rule 6 honest framing):
        If the UTCI-hours reduction is None, zero, or negative (no comfort gain),
        value=None is returned with confidence LOW and an explanatory note.
        The prefer-measured path is still attempted when delta_utci_c is present.

    Returns a standard metric dict with keys:
        value, value_lo, value_hi, unit, confidence, sources, note, metric_id,
        utci_hours_reduced, cost_per_utci_hour, cost_per_utci_hour_lo,
        cost_per_utci_hour_hi, utci_hours_unit, band_c, band_source.
        New keys (additive, COST-05): discount_rate, ramp_years, horizon_years,
        growth_note.
    """
    # ── Growth-discount params ─────────────────────────────────────────────────
    gd: GrowthDiscountParams = growth_discount if growth_discount is not None else DEFAULT_GROWTH_DISCOUNT
    # ── Cost table (COST-04 / D-05) — None → DEFAULT_COST_TABLE (backward compat)
    ct: CostTable = cost_table if cost_table is not None else DEFAULT_COST_TABLE

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
        if uh.get("error") or uh.get("value") is None:
            utci_hours_note = "UTCI-hours unavailable (EPW missing)"
        else:
            # utci_hours_above returns value (hours-above with canopy) and
            # baseline_value (hours-above with no canopy). The reduction is
            # baseline - value (NOT a "delta" key — that key does not exist).
            val = uh.get("value")
            base = uh.get("baseline_value")
            if val is not None and base is not None:
                hours_reduced = float(base) - float(val)
                if hours_reduced < 0:
                    hours_reduced = 0.0  # guard: canopy never increases hot hours
            else:
                hours_reduced = None
                utci_hours_note = "UTCI-hours baseline unavailable"
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
        hpd = hours_per_degc()
        degc_drop = hours_reduced / hpd
        note_parts.append(
            "UTCI-hours→equiv mean-°C conversion (EPW-derived; "
            f"hours_reduced={hours_reduced:.1f} / hours_per_degc={hpd:.1f})"
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
            # Growth-discount param echo (COST-05) — additive, does not remove existing keys
            "discount_rate": gd.discount_rate,
            "ramp_years": gd.ramp_years,
            "horizon_years": gd.horizon_years,
            "growth_note": (
                f"Benefit ramped over {gd.ramp_years:.0f}yr growth curve and discounted at "
                f"{gd.discount_rate:.1%} over {gd.horizon_years}yr (COST-05/D-07..D-10); "
                "denominator is discounted-lifetime equivalent degC, not day-one full canopy."
            ),
        }

    # ── Apply growth-horizon discount to °C denominator (COST-05 / D-07..D-10) ─
    # Route degc_drop through discounted_lifetime_degc() BEFORE computing any
    # KPI values.  This makes the °C an equivalent discounted-lifetime drop
    # (not day-one full canopy).  The band propagation, interval math, dual-unit
    # cost_per_utci_hour, and zero-guard ALL remain structurally identical —
    # only the cost and degc_drop magnitudes change.
    degc_drop = discounted_lifetime_degc(degc_drop, gd)

    # Scale the uncertainty band through the SAME growth/discount factor so it
    # stays proportional to the (now discounted) °C estimate. Without this, an
    # absolute ±4°C band applied to a discounted ~3°C estimate makes degc_drop-band
    # go negative and nulls value_hi (the upper cost bound) — an artifact, not real
    # uncertainty. discounted_lifetime_degc is linear in its input, so this is
    # band × the same discount factor applied to degc_drop. (band_hours below stays
    # on the RAW per-year hours scale — annual hours are not lifetime-discounted.)
    band_degc = discounted_lifetime_degc(band, gd)

    # ── Compute primary KPI (€/°C) ────────────────────────────────────────────
    # Numerator: present value of lifecycle cost (discounted OpEx, D-08).
    # NOTE: total_cost() (nominal, no discounting) is preserved for the
    # optimizer's NSGA-II budget constraint — do NOT change that path.
    # Pass ct (edited or default CostTable) so the KPI numerator uses the
    # same table as the Gradio inputs (COST-04 / D-05).
    cost = discounted_total_cost(config, gd, cost_table=ct)
    value = round(cost / degc_drop, 2)

    # Interval propagation: band on °C drop (D-10)
    # More cooling (degc_drop + band) → cheaper per °C → lower bound
    value_lo = round(cost / (degc_drop + band_degc), 2)
    degc_minus_band = degc_drop - band_degc
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
        # Propagate band into hours via the EPW-derived hours/°C
        hours_band = band * hours_per_degc()
        hours_hi = hours_reduced + hours_band  # more hours → cheaper per hour
        hours_lo = hours_reduced - hours_band  # fewer hours → costlier per hour
        cost_per_utci_hour_lo = round(cost / hours_hi, 2)
        if hours_lo <= _EPS:
            cost_per_utci_hour_hi = None  # upper bound unbounded
        else:
            cost_per_utci_hour_hi = round(cost / hours_lo, 2)

    # ── Build note ────────────────────────────────────────────────────────────
    growth_note = (
        f"Benefit ramped over {gd.ramp_years:.0f}yr growth curve and discounted at "
        f"{gd.discount_rate:.1%} over {gd.horizon_years}yr (COST-05/D-07..D-10); "
        "denominator is discounted-lifetime equivalent degC, not day-one full canopy."
    )
    note_parts.append(
        f"KPI interval [value_lo={value_lo}, value={value}, value_hi={value_hi}] "
        f"EUR/degC; band={band_source}. "
        "Delta is UTCI (routed through utci_hours_above), never raw Tmrt (D-08). "
        "Both units: EUR/degC (primary) and EUR/annual-UTCI-hour (secondary, D-09). "
        "Interval is never a bare point estimate (D-10/VALID-04). "
        "Cost uses itemized fully-loaded lifecycle CostTable (Phase 6 / COST-03): "
        f"CapEx={ct.capex_total():.0f} EUR/tree, OpEx={ct.opex_per_year():.0f} EUR/tree/yr "
        f"over {gd.horizon_years} yr horizon (Barcelona-anchored; OpEx VERIFIED BCN IMPJ 2023, CapEx DECLARED Diputació BCN grant). "
        f"{growth_note}"
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
        # Growth-discount param echo (COST-05) — additive, does not remove existing keys
        "discount_rate": gd.discount_rate,
        "ramp_years": gd.ramp_years,
        "horizon_years": gd.horizon_years,
        "growth_note": growth_note,
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
