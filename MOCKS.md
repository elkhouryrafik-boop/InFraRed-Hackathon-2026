# MOCKS.md — CoolSpend Honesty Ledger

Every mock/surrogate/assumed constant in coolspend gets a row here. No fabricated citations (use REQUIRES_VERIFICATION).

Any value tagged MOCK, SURROGATE, or DECLARED in code must have a matching row in this table.
The pre-merge check is: every `# MOCK:` or `# SURROGATE:` comment must map to a row here.

| Item | Location | Status | Reason | Replacement Path |
|------|----------|--------|--------|-----------------|
| mock UTCI delta | coolspend/sdk_client.py | MOCK | synthetic scalar UTCI delta returned offline before May 27 API key; NOT MEASURED DATA | INFRARED_BACKEND=live after May 27 |
| angels_site.geojson fixture | coolspend/data/angels_site.geojson | MOCK | hand-authored offline site geometry (site boundary + 2 buildings + 1 street) for deterministic spatial tests; not surveyed OSM data | real OSM export for Placa dels Angels |
| CapEx/OpEx tree cost constants | coolspend/cost_model.py | DECLARED | CAPEX_PER_TREE_EUR=350, OPEX_PER_TREE_YEAR_EUR=35, OPEX_HORIZON_YEARS=10 are unsourced midrange assumptions for urban street-tree planting; NOT independently verified | verified municipal tree-cost figures (e.g. Barcelona/Madrid procurement data) |
| ecological rules (MIN_SPACING_M, SPECIES_PALETTE) | coolspend/rules_engine.py | DECLARED | MIN_SPACING_M=4.0 m is a typical urban street-tree planting guideline assumption, NOT sourced from Barcelona municipal code; SPECIES_PALETTE=("platanus","celtis","tilia","quercus") is a demo resilient-mix selection, NOT verified against Barcelona Arbrat Viari recommended-species list — REQUIRES_VERIFICATION | Barcelona municipal tree-planting code (spacing) + Arbrat Viari zona recommended-species list (palette) |
| delta_tmrt_surrogate (analytical thermal proxy) | coolspend/spatial_engine.py | MOCK/SURROGATE | MAX_TMRT_REDUCTION_C=12°C is an UNSOURCED hard-coded cap with no error bar and no Ladybug/Infrared validation (CONCERNS 1.1). Uncertainty ±4°C per parent audit_record.json. Citation mismatch: Garcia-Nevado 2020 measures pavement surface temperature via IR thermography, NOT mean radiant temperature (Tmrt) at 1.1m pedestrian height. Vanos 2020 quotes Tmrt shade component only. Linear interpolation between two literature ceilings is not a calibrated Tmrt model. Porosity-squared bug fixed (CONCERNS 4.2): porosity applied ONCE by caller, not re-applied in body. Use for NSGA-II surrogate hot-path ONLY; validate Top-3 with real Infrared SDK UTCI (Plan 02-04). | Replace with Ladybug lookup table (D1-04) or real Infrared UTCI after May 27 API key |
| TREE_SHADE_FRACTION=0.80, TREE_CANOPY_RADIUS_M=3.0 | coolspend/spatial_engine.py | DECLARED | Mature street-tree typical canopy shade fraction and effective shaded radius — DECLARED assumptions, NOT from surveyed Barcelona Arbrat Viari tree inventory. REQUIRES_VERIFICATION. | Barcelona Arbrat Viari tree inventory + field measurement data |
