# CoolSpend

## One-line pitch

A budget-to-decision tool that tells a city Chief Heat Officer where to plant trees for the most degrees of UTCI thermal relief per euro — optimised with NSGA-II on an analytical surrogate, with the Top-3 picks re-simulated with Infrared UTCI when run live (live wiring implemented; confirmation pending May 27 API key).

---

## What it is

CoolSpend takes a city site polygon and a fixed planting budget, and returns a ranked tree-planting allocation with a before/after UTCI comfort map — a defensible decision, not just a heatmap. The user provides a GeoJSON polygon and adjusts a budget slider; CoolSpend runs a multi-objective NSGA-II optimizer, selects the three best Pareto candidates by distinct strategy (max thermal relief, max ecological coherence, and balanced), re-simulates each with Infrared UTCI when run live, and ranks them by the headline KPI: euros per degree Celsius of street-level comfort improvement. It is built on the infrared.city SDK (Tree Budget track) with a clean mock | cached | live boundary so it runs fully offline for demos and switches to real measured data with a single environment variable. The default site is Plaça dels Àngels, Barcelona.

---

## Technical depth

The optimizer (`optimizer.py`) uses NSGA-II from pymoo 0.6.1, a 24-float chromosome (x, y coordinates for 12 tree slots), two objectives — thermal relief and ecological coherence — and one budget inequality constraint. An analytical thermal surrogate (`delta_tmrt_surrogate` in `spatial_engine.py`) runs inside the NSGA-II hot path: zero SDK calls during the ~3,600 per-generation evaluations. The Pareto front (60 candidates at full settings) is computed in under half a second offline.

Top-3 Pareto representatives (MAX_THERMAL_RELIEF, MAX_ECOLOGICAL, BALANCED) are re-simulated with three Infrared UTCI SDK calls (guarded by `SimBudget(max_live_calls=3)`) when `INFRARED_BACKEND=live`. The live wiring is implemented; the exact SDK enum member requires confirmation at May 27 API key issuance (see MOCKS.md). TOPSIS (Hwang & Yoon 1981) with weights 0.6 thermal / 0.4 ecological provides a tie-break; primary ranking is ascending EUR/°C.

The SDK boundary (`sdk_client.py`) is a clean env-driven dispatch (mock | cached | live) with `UTCIResult`, `SimBudget`, geometry hashing, and lazy import of `infrared_sdk` — the module is importable and fully testable with no API key. The offline test suite covers 134 tests across all modules (deterministic, seed-42, no network).

Decision output is a deterministic JSON artifact (`outputs/top3_configurations.json`) with full run metadata, TOPSIS scores, per-config disclaimers, and a before/after UTCI record for the rank-1 configuration.

---

## Creativity

CoolSpend reframes "where is it hot?" as "where does each euro buy the most cooling?" — turning a heatmap into a budget allocation decision. The surrogate-optimize-then-validate pattern is the key creative contribution: by using an analytical proxy in the NSGA-II loop and reserving real SDK calls for Top-3 validation only, the tool stays within the SimBudget constraint while grounding its final recommendations in Infrared UTCI data when run live. The single headline KPI — euros per degree Celsius of UTCI relief — is designed to be defensible to a budget committee, not just technically accurate. The Gradio UI exposes TOPSIS weight sliders so the decision-maker can explore the trade-off between thermal and ecological objectives interactively.

---

## Real-world impact

The primary user persona is Maria, a city Chief Heat Officer with a fixed annual tree-planting budget and a heatwave forecast. CoolSpend gives her a ranked allocation she can hand to a budget committee with a defensible cost figure attached. On the mock backend the optimizer finds a genuinely differentiated ranking: EUR 1,700/degC (rank-1 MAX_THERMAL_RELIEF) vs EUR 2,084/degC (BALANCED) vs EUR 3,194/degC (MAX_ECOLOGICAL) — illustrative mock values; when run live, the final picks are re-simulated with Infrared UTCI and the real EUR/°C numbers replace these. The framework generalises to any city polygon: swap the GeoJSON polygon text box and re-run. District-scale triage — prioritising which blocks get trees first during a multi-year canopy expansion programme — is a direct application. The tool respects the constraints of real municipal procurement: cost constants are declared assumptions that require verification against local data, and all outputs carry explicit confidence levels and data-source tags.

---

## Presentation

CoolSpend runs as a live Gradio Blocks web app on Hugging Face Spaces. The UI shows the site polygon text box, budget slider, TOPSIS weight sliders, and a backend selector. On submit, it renders a before/after UTCI map panel, a ranked three-row allocation table with a per-row provenance column, and an expandable SDK call-log panel showing the three SimBudget-guarded Infrared API calls. The app defaults to mock mode (no key required) with a prominent "NOT MEASURED DATA" banner; switching to live mode replaces all values with real measured Infrared UTCI outputs (requires API key and live backend confirmation). The ~3-minute narrated demo follows the DEMO_SCRIPT.md shot list: hook (the decision problem), app run with visible call log, before/after map, ranked table, and the EUR/°C headline close.

---

## Honesty note

The thermal surrogate (`delta_tmrt_surrogate`) has approximately ±4°C uncertainty and its 12°C cap (`MAX_TMRT_REDUCTION_C`) is unsourced — no validated citation was found for this constant. All mock numbers are NOT MEASURED DATA (synthetic values for integration testing only). The cost constants (CAPEX_PER_TREE_EUR=350, OPEX_PER_TREE_YEAR_EUR=35, OPEX_HORIZON_YEARS=10) are DECLARED assumptions that REQUIRE_VERIFICATION against municipal procurement data; the EUR/°C headline figure should be treated as illustrative until confirmed. When run with `INFRARED_BACKEND=live`, the Top-3 configurations are re-simulated with Infrared UTCI SDK calls, replacing surrogate values with measured data for the final ranking. The live SDK wiring is implemented; confirmation against the real API is pending May 27 API key issuance (see MOCKS.md live row).

Full details, data-source tags (VERIFIED / MOCK / DECLARED), and citation-mismatch disclosures are in [MOCKS.md](MOCKS.md).

---

## Links

- GitHub repo: `<FILL IN>`
- Hugging Face Space: `<FILL IN — created at kickoff>`
- Demo video: `<FILL IN after recording>`
