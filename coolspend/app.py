"""
coolspend/app.py — Gradio Blocks web app for CoolSpend.

Entry point for Hugging Face Spaces and local demo:
  python -m coolspend.app       # launches Gradio server in browser
  python coolspend/app.py       # same via direct run

Build the UI in build_demo() so tests can construct it without launching.

Threat mitigations:
  T-03-05: INFRARED_API_KEY never referenced here — only backend name shown
  T-03-06: polygon text delegated to parse_site_geojson (json.loads only, no eval)
  T-03-07: SimBudget cap enforced inside run_decision (3 live calls/run)
  T-03-08: per-row provenance + global banner make mock-vs-live explicit
  T-03-09: on_submit catches unexpected exceptions and shows a GENERIC error
           message to the UI; full traceback is logged server-side only
           (prevents path/internal leakage on a public Space — Security L1)
"""
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger("coolspend.app")

import gradio as gr

# ── Workaround: gradio 4.44.1 + gradio_client schema-parse bug ────────────────
# get_api_info() crashes with "TypeError: argument of type 'bool' is not iterable"
# when a component schema has a boolean `additionalProperties`/`const`. The buggy
# helpers index the schema assuming it is always a dict. We make them bool-safe.
# This also fixes the false "localhost is not accessible" error, which is caused
# by the launch health-check hitting the crashing api_info endpoint.
try:  # pragma: no cover - environment-dependent
    import gradio_client.utils as _gcu

    _orig_js2pt = _gcu._json_schema_to_python_type

    def _safe_js2pt(schema, defs=None):
        if isinstance(schema, bool):
            return "Any"
        return _orig_js2pt(schema, defs)

    _gcu._json_schema_to_python_type = _safe_js2pt

    _orig_get_type = _gcu.get_type

    def _safe_get_type(schema):
        if not isinstance(schema, dict):
            return "Any"
        return _orig_get_type(schema)

    _gcu.get_type = _safe_get_type
except Exception:  # noqa: BLE001 - never block launch on the patch itself
    logger.warning("gradio_client bool-schema patch could not be applied", exc_info=True)

from coolspend.app_pipeline import DEFAULT_BUDGET_EUR, run_decision
from coolspend.app_viz import render_before_after
from coolspend.spatial_engine import DEFAULT_SITE

# ── Default polygon pre-fill ──────────────────────────────────────────────────
_DEFAULT_POLYGON_TEXT: str = Path(DEFAULT_SITE).read_text(encoding="utf-8")

# ── Table headers ─────────────────────────────────────────────────────────────
# D-15: surface the KPI interval [lo, hi] + band_source; never a bare point estimate.
# Dual unit: primary EUR/degC + secondary EUR/UTCI-hr (D-09).
_TABLE_HEADERS = [
    "Rank",
    "Label",
    "Trees",
    "Cost EUR",
    "EUR/degC [lo–hi]",
    "EUR/UTCI-hr",
    "Band source",
    "delta UTCI degC",
    "TOPSIS",
    "Provenance",
]


# ── Callback ──────────────────────────────────────────────────────────────────


def on_submit(
    geojson_text: str,
    budget_eur: float,
    w_thermal: float,
    w_ecological: float,
    backend: str,
) -> tuple:
    """Handle the Run button click.

    Args:
        geojson_text:  GeoJSON string from the polygon textarea (or empty).
        budget_eur:    Budget in EUR from the slider.
        w_thermal:     TOPSIS thermal weight slider value (0.0 – 1.0).
        w_ecological:  TOPSIS ecological weight slider value (0.0 – 1.0).
        backend:       "mock" | "cached" | "live" from the radio selector.

    Returns:
        4-tuple: (banner_md, img_path, table_rows, call_log_text)
          - banner_md:     str  — Markdown headline + disclaimer banner
          - img_path:      str | None — path to before/after PNG (or None on error)
          - table_rows:    list[list] — rows for gr.Dataframe
          - call_log_text: str  — captured Infrared/SimBudget call lines
    """
    # Run pipeline
    try:
        result = run_decision(
            budget_eur=budget_eur,
            weights=(w_thermal, w_ecological),
            geojson_text=geojson_text.strip() if geojson_text else None,
            backend=backend,
        )
    except Exception as exc:  # noqa: BLE001  — never crash the UI
        # T-03-09: log full traceback server-side; show only a generic message to the
        # UI to prevent path/internal leakage on a public Space (Security L1).
        logger.exception("on_submit: unexpected exception from run_decision: %s", exc)
        banner = "**ERROR** — An unexpected error occurred — see server logs."
        return (banner, None, [], "An unexpected error occurred — see server logs.")

    # ── Error path ────────────────────────────────────────────────────────────
    if result.get("error"):
        err = result["error"]
        banner = (
            f"**ERROR** — {err}\n\n"
            f"_Backend: {backend}_"
        )
        call_log_text = "\n".join(result.get("call_log", []))
        return (banner, None, [], call_log_text or err)

    # ── Success path ──────────────────────────────────────────────────────────
    headline = result["headline"]

    # Honesty disclaimer — "NOT MEASURED DATA" required for mock backend (T-03-08)
    if backend == "mock":
        disclaimer_line = (
            "**DISCLAIMER: NOT MEASURED DATA** — "
            "results are synthetic mock values for integration only. "
            "SURROGATE-DERIVED deltas with ±4 degC uncertainty."
        )
    else:
        disclaimer_line = f"_Disclaimer: {result.get('disclaimer', '')}_ "

    backend_line = f"_Backend: **{backend}**_"
    banner_md = f"### {headline}\n\n{disclaimer_line}\n\n{backend_line}"

    # Before/after image
    try:
        img_path = render_before_after(
            result["configurations"][0],
            result["before_after"],
            site_path=result.get("site_path"),
        )
    except Exception as exc:  # noqa: BLE001
        img_path = None
        banner_md += f"\n\n_Warning: Could not render before/after map: {exc}_"

    # Allocation table rows — D-15: always show interval [lo,hi] + band_source,
    # never a bare point estimate. Dual unit: EUR/degC (primary) + EUR/UTCI-hr (D-09).
    table_rows = []
    for cfg in result.get("configurations", []):
        kpi = cfg.get("cost_per_utci_degree", {})
        if not isinstance(kpi, dict):
            kpi = {}

        # Primary KPI: EUR/degC as interval [lo–hi] (D-10 / D-15)
        kpi_val = kpi.get("value")
        value_lo = kpi.get("value_lo")
        value_hi = kpi.get("value_hi")
        if kpi_val is not None:
            lo_str = f"{value_lo:.2f}" if value_lo is not None else "?"
            hi_str = f"{value_hi:.2f}" if value_hi is not None else "∞"
            eur_per_deg = f"{kpi_val:.2f} [{lo_str}–{hi_str}]"
        else:
            eur_per_deg = "N/A"

        # Secondary KPI: EUR per annual UTCI-hour reduced (D-09)
        cost_per_utci_hour = kpi.get("cost_per_utci_hour")
        eur_per_hour = f"{cost_per_utci_hour:.2f}" if cost_per_utci_hour is not None else "N/A"

        # Band source label (D-15 — reads from KPI dict, never hardcoded)
        band_source = kpi.get("band_source", "")

        # Provenance: per-row disclaimer (truncated to 60 chars to fit column)
        provenance_full = cfg.get("disclaimer", cfg.get("validated_disclaimer", ""))
        provenance = provenance_full[:60] + "…" if len(provenance_full) > 60 else provenance_full

        table_rows.append([
            cfg.get("rank", ""),
            cfg.get("label", ""),
            cfg.get("tree_count", 0),
            f"{cfg.get('cost_eur', 0.0):,.0f}",
            eur_per_deg,
            eur_per_hour,
            band_source,
            f"{cfg.get('delta_utci_c', 0.0):.3f}",
            f"{cfg.get('topsis_score', 0.0):.4f}",
            provenance,
        ])

    # Call log — visible Infrared/SimBudget call lines (ROADMAP #3)
    call_log_text = "\n".join(result.get("call_log", []))

    return (banner_md, img_path, table_rows, call_log_text)


# ── UI builder ────────────────────────────────────────────────────────────────


def build_demo() -> gr.Blocks:
    """Build and return the Gradio Blocks demo without launching.

    Tests call this directly so the UI can be constructed headlessly.

    Returns:
        gr.Blocks: the constructed demo (not started).
    """
    with gr.Blocks(title="CoolSpend — Tree Budget Optimizer") as demo:
        gr.Markdown(
            "# CoolSpend — Tree Budget Optimizer\n"
            "Given a site polygon and a planting budget, find the tree placements "
            "that deliver the most UTCI cooling relief per euro.\n\n"
            "_Powered by Infrared City SDK + NSGA-II multi-objective optimization._"
        )

        with gr.Row():
            # ── Left column: inputs ───────────────────────────────────────────
            with gr.Column(scale=1):
                gr.Markdown("### Inputs")

                geojson_box = gr.Textbox(
                    label="Site polygon (GeoJSON FeatureCollection or bare Polygon)",
                    value=_DEFAULT_POLYGON_TEXT,
                    lines=8,
                    placeholder="Paste GeoJSON here (default = Plaça dels Àngels, Barcelona)",
                )

                budget_slider = gr.Slider(
                    minimum=50_000,
                    maximum=2_000_000,
                    value=DEFAULT_BUDGET_EUR,
                    step=50_000,
                    label="Budget (EUR)",
                )

                gr.Markdown(
                    "**TOPSIS weights** — user judgment, NOT calibrated constants "
                    "(CONCERNS 1.6 / APP-01). Adjust to reflect priorities."
                )
                w_thermal_slider = gr.Slider(
                    minimum=0.0,
                    maximum=1.0,
                    value=0.6,
                    step=0.1,
                    label="Weight: Thermal relief (UTCI delta)",
                )
                w_ecological_slider = gr.Slider(
                    minimum=0.0,
                    maximum=1.0,
                    value=0.4,
                    step=0.1,
                    label="Weight: Ecological score",
                )

                backend_radio = gr.Radio(
                    choices=["mock", "cached", "live"],
                    value="mock",
                    label="Infrared backend (mock = offline, no key)",
                )

                run_btn = gr.Button("Run decision", variant="primary")

            # ── Right column: outputs ─────────────────────────────────────────
            with gr.Column(scale=2):
                gr.Markdown("### Results")

                banner_out = gr.Markdown(
                    value="_Click 'Run decision' to see the headline result._",
                    label="Decision headline + disclaimer",
                )

                map_out = gr.Image(
                    label="Before / After UTCI map",
                    type="filepath",
                )

                table_out = gr.Dataframe(
                    headers=_TABLE_HEADERS,
                    label="Ranked allocation table (Top-3 configurations)",
                    interactive=False,
                )

                with gr.Accordion("Infrared SDK call log", open=False):
                    calllog_out = gr.Textbox(
                        label="Visible Infrared / SimBudget calls (ROADMAP #3)",
                        lines=6,
                        interactive=False,
                        placeholder="Call log will appear here after running.",
                    )

        # ── Wire callback ─────────────────────────────────────────────────────
        run_btn.click(
            fn=on_submit,
            inputs=[
                geojson_box,
                budget_slider,
                w_thermal_slider,
                w_ecological_slider,
                backend_radio,
            ],
            outputs=[banner_out, map_out, table_out, calllog_out],
        )

    return demo


# ── Module-level demo (HF Spaces + `python -m coolspend.app` entrypoint) ─────
demo = build_demo()

if __name__ == "__main__":
    import os

    # Configurable launch. If loopback is blocked in your environment, set
    # GRADIO_SHARE=1 to get a temporary public link instead.
    demo.launch(
        server_name=os.environ.get("GRADIO_SERVER_NAME", "127.0.0.1"),
        server_port=int(os.environ.get("GRADIO_SERVER_PORT", "7860")),
        share=os.environ.get("GRADIO_SHARE", "").lower() in ("1", "true", "yes"),
    )
