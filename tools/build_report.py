"""Generate the CoolSpend 'Real-Data / Zero-Mock Re-architecture' report PDF.

Code-based, deterministic. Run: python tools/build_report.py
Writes: outputs/CoolSpend_RealData_ActionPlan.pdf
"""
from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, Table, TableStyle,
    ListFlowable, ListItem, HRFlowable, PageBreak,
)

OUT = Path("outputs/CoolSpend_RealData_ActionPlan.pdf")
OUT.parent.mkdir(parents=True, exist_ok=True)

# ── Palette ───────────────────────────────────────────────────────────────────
INK = colors.HexColor("#14241b")
LEAF = colors.HexColor("#2f7d4f")
LEAFD = colors.HexColor("#1d5233")
HEAT = colors.HexColor("#c2410c")
MUTE = colors.HexColor("#5b6b61")
LINE = colors.HexColor("#cdd8d0")
PANEL = colors.HexColor("#eef4ef")
PANEL2 = colors.HexColor("#fbf4ee")

ss = getSampleStyleSheet()

def style(name, **kw):
    return ParagraphStyle(name, parent=ss["Normal"], **kw)

H1 = style("H1", fontName="Helvetica-Bold", fontSize=20, leading=24, textColor=LEAFD, spaceAfter=4)
SUB = style("SUB", fontName="Helvetica", fontSize=10.5, leading=14, textColor=MUTE, spaceAfter=10)
H2 = style("H2", fontName="Helvetica-Bold", fontSize=13.5, leading=17, textColor=INK, spaceBefore=14, spaceAfter=5)
H3 = style("H3", fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=LEAFD, spaceBefore=8, spaceAfter=3)
BODY = style("BODY", fontName="Helvetica", fontSize=9.6, leading=13.6, textColor=INK, alignment=TA_LEFT, spaceAfter=5)
SMALL = style("SMALL", fontName="Helvetica", fontSize=8.4, leading=11.2, textColor=MUTE)
KPI = style("KPI", fontName="Helvetica-Bold", fontSize=9.6, leading=13, textColor=LEAFD)
CELL = style("CELL", fontName="Helvetica", fontSize=8.5, leading=11, textColor=INK)
CELLB = style("CELLB", fontName="Helvetica-Bold", fontSize=8.5, leading=11, textColor=INK)
CELLH = style("CELLH", fontName="Helvetica-Bold", fontSize=8.5, leading=11, textColor=colors.white)

story = []

def hr():
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=0.6, color=LINE))
    story.append(Spacer(1, 4))

def para(t, s=BODY):
    story.append(Paragraph(t, s))

def bullets(items, s=BODY):
    story.append(ListFlowable(
        [ListItem(Paragraph(t, s), leftIndent=6, value="•") for t in items],
        bulletType="bullet", start="•", leftIndent=12, bulletColor=LEAF,
    ))

def panel(flowables, bg=PANEL, pad=7):
    t = Table([[flowables]], colWidths=[170 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("BOX", (0, 0), (-1, -1), 0.5, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), pad),
        ("RIGHTPADDING", (0, 0), (-1, -1), pad),
        ("TOPPADDING", (0, 0), (-1, -1), pad),
        ("BOTTOMPADDING", (0, 0), (-1, -1), pad),
    ]))
    story.append(t)
    story.append(Spacer(1, 6))

def table(rows, widths, header=True, zebra=True):
    data = []
    for ri, r in enumerate(rows):
        is_head = header and ri == 0
        data.append([c if isinstance(c, Paragraph) else Paragraph(str(c), CELLH if is_head else CELL)
                     for c in r])
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    sty = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.4, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if header:
        sty.append(("BACKGROUND", (0, 0), (-1, 0), LEAFD))
    if zebra:
        for i in range(1, len(data)):
            if i % 2 == 0:
                sty.append(("BACKGROUND", (0, i), (-1, i), PANEL))
    t.setStyle(TableStyle(sty))
    story.append(t)
    story.append(Spacer(1, 6))

# ════════════════════════════════════════════════════════════════════════════
# COVER / HEADER
# ════════════════════════════════════════════════════════════════════════════
para("CoolSpend — Real-Data, Zero-Mock Re-architecture", H1)
para("Action plan to make the &ldquo;optimal cooling layout&rdquo; claim defensible on measured Infrared UTCI. "
     "Prepared 2026-05-29 (Thu). Submission: Sun night. Working window: ~3 days.", SUB)
hr()

# ════════════════════════════════════════════════════════════════════════════
# 1. EXECUTIVE SUMMARY
# ════════════════════════════════════════════════════════════════════════════
para("1 &nbsp; Executive summary", H2)
para("The pipeline already <b>measures real tree cooling</b> via Infrared (same site, run once without trees, once with "
     "your placed trees as vegetation; the delta is genuine physics). Cached live runs show <b>0.7&ndash;1.5&nbsp;&deg;C "
     "mean cooling</b> on real Barcelona polygons. That part is sound. The weakness is not <i>&ldquo;is it real&rdquo;</i> "
     "&mdash; it is <i>&ldquo;did we optimise for it.&rdquo;</i>", BODY)
panel([
    Paragraph("THE CORE PROBLEM (one sentence)", KPI),
    Paragraph("The optimiser maximises an <b>unsourced analytical surrogate</b> shaped by a hand-tuned &ldquo;core-weight&rdquo; "
              "knob, validates only 3 of thousands of layouts on real Infrared, and ranks them on a noisy site-mean &euro;/&deg;C "
              "KPI &mdash; so the &ldquo;optimal cooling&rdquo; claim rests on a proxy, not on measured cooling.", BODY),
])
para("This report specifies the surgical change: <b>drop the analytical surrogate and the core-weight knob, drive the search "
     "with real Infrared UTCI batches, make placement building-aware, and rank on one measured metric end-to-end.</b> "
     "Result: every reported number is measured, the &ldquo;optimal&rdquo; claim becomes &ldquo;best of N measured layouts,&rdquo; "
     "and the mock UTCI path is removed from the demo. Natural-capital (multi-yield) work is parked until this lands.", BODY)

panel([
    Paragraph("ONE BLOCKER FOR LIVE WORK", KPI),
    Paragraph("<b>INFRARED_API_KEY is not set in the working environment.</b> Real-UTCI optimisation cannot run until you "
              "supply it (set the env var, or run the driver yourself). Everything that does NOT need the key (building-aware "
              "placement, single-metric refactor, surrogate removal, KPI consistency, under-shade readout) can proceed now.", BODY),
], bg=PANEL2)

# ════════════════════════════════════════════════════════════════════════════
# 2. CURRENT STATE — WHAT IS REAL
# ════════════════════════════════════════════════════════════════════════════
para("2 &nbsp; Current state &mdash; measured evidence", H2)
para("Pulled from your 8 cached <i>live</i> Infrared runs (backend=&ldquo;live&rdquo;), two real Barcelona sites:", BODY)
table(
    [
        ["Site", "Baseline UTCI mean", "Best intervention mean", "Real cooling &Delta;", "Heat-stress area removed"],
        ["A (~1999 cells)", "28.98 &deg;C", "27.52 &deg;C", "1.46 &deg;C", "~188 m&sup2;"],
        ["B (~8167 cells)", "28.56 &deg;C", "27.57 &deg;C", "0.99 &deg;C", "~672 m&sup2;"],
    ],
    widths=[30 * mm, 35 * mm, 38 * mm, 30 * mm, 37 * mm],
)
bullets([
    "<b>Cooling is real and measured.</b> Mechanism is correct: baseline (0 trees) vs intervention (placed trees as vegetation), identical buildings/ground/weather.",
    "<b>Building shadows are ALREADY modelled</b> in the live sim &mdash; <font face='Courier'>buildings</font> are passed to <font face='Courier'>run_area_and_wait</font>. The gap is only that <i>placement screening</i> ignores them (treats the site as open ground).",
    "<b>Baseline is mild</b> (mean ~29 &deg;C, max ~31 &deg;C): coastal Barcelona + sea breeze + a July window-mean. Real, but the &ldquo;extreme heat&rdquo; pitch is not supported by the data &mdash; lead with m&sup2; cooled + peak-cell drop instead.",
    "<b>Feasibility unlock:</b> <font face='Courier'>run_area_and_wait</font> accepts a LIST of payloads and runs ~20 tile-jobs concurrently per client (account ceiling ~100). Evaluating dozens of candidate layouts on real UTCI in batches is therefore practical.",
])

# ════════════════════════════════════════════════════════════════════════════
# 3. THE SIX PROBLEMS -> FIXES
# ════════════════════════════════════════════════════════════════════════════
para("3 &nbsp; The six problems &rarr; required fix", H2)
table(
    [
        ["#", "Problem (today)", "Fix (this plan)"],
        ["1", "Optimiser maximises an analytical surrogate; only 3 layouts ever see real Infrared.",
         "Drive the search with <b>real UTCI batches</b>; rank a population of <i>measured</i> layouts. &ldquo;Optimal&rdquo; = best of N measured."],
        ["2", "Core-weight knob (CORE_BLEND=0.6&hellip;) hand-shapes &ldquo;best thermal.&rdquo;",
         "<b>Remove the knob entirely.</b> Thermal value = measured UTCI cooling; no centre bias, no footfall assumption."],
        ["3", "Surrogate uses an unsourced 12 &deg;C cap + 0.80 shade + 3 m radius.",
         "<b>Delete the analytical surrogate</b> from the decision path. Optional: a cheap proposer fitted to real runs, ranking-only, never reported as &deg;C."],
        ["4", "Dimension mismatch: surrogate &Delta;Tmrt vs validation mean UTCI.",
         "<b>One quantity throughout</b>: measured UTCI cooling (mean &Delta; + m&sup2; cooled). Search, rank, headline all use it."],
        ["5", "Ranking KPI = &euro;/&deg;C on a noisy mean; headline uses a different metric (m&sup2;).",
         "<b>Single KPI</b>: &euro; per m&sup2; cooled &ge;0.5 &deg;C (robust, doesn&rsquo;t saturate). Optimise, rank, and headline on it."],
        ["6", "Placement can land trees on buildings/streets; ignores building shade.",
         "<b>Building-aware candidate slots</b>: filter by real Infrared/OSM footprints + street buffers. Building shade already in the sim."],
    ],
    widths=[7 * mm, 78 * mm, 85 * mm],
)
para("Extra asks captured: <b>show under-shade temperature</b> (mask grid cells under canopy &rarr; report under-canopy UTCI "
     "vs open); <b>weather-grounded value</b> (UTCI already runs on the real TMYx Barcelona EPW &mdash; surface that provenance). "
     "<b>Zero mocks</b> is the exit gate (&sect;5).", BODY)

# ════════════════════════════════════════════════════════════════════════════
# 4. ARCHITECTURE DECISION
# ════════════════════════════════════════════════════════════════════════════
story.append(PageBreak())
para("4 &nbsp; Architecture decision", H2)
para("<b>From:</b> NSGA-II on an analytical proxy &rarr; validate 3 picks. &nbsp; <b>To:</b> a search whose fitness IS measured "
     "Infrared UTCI, over building-aware slots, ranked on one metric.", BODY)

para("4.1 &nbsp; Recommended: measured-fitness search (greedy + batch)", H3)
bullets([
    "<b>Decision space</b> = building-aware candidate planting slots: a metric grid over the site, minus building footprints, minus street buffers, optionally snapped to real empty tree-pit locations.",
    "<b>Greedy marginal placement on real UTCI</b>: at each step batch-evaluate the C best open slots (one payload each, run concurrently), keep the slot with the largest measured cooling gain, repeat to budget. Directly yields <b>per-tree marginal cooling</b> &mdash; the &ldquo;how much does ONE tree cool&rdquo; number you asked about, measured.",
    "<b>Or population batch</b>: generate K candidate layouts (building-aware), evaluate ALL on real UTCI in one multi-payload call, pick the best-measured; small CMA/NSGA loop if budget allows.",
    "<b>Sim budget knob</b>: total real evaluations bounded (e.g. 40&ndash;80) and logged. &ldquo;Optimal&rdquo; is honestly stated as &ldquo;best of N measured layouts,&rdquo; not global optimum.",
])
panel([
    Paragraph("WHY NOT &ldquo;just optimise directly, thousands of evals&rdquo;", KPI),
    Paragraph("A full NSGA-II run is ~3,600 evaluations. At real-sim latency that is impossible in 3 days and would burn quota. "
              "The honest, strong alternative is a <b>bounded measured search</b> (greedy/batch) that evaluates tens of real "
              "layouts &mdash; every reported layout is measured, and the claim is precise about what was searched.", BODY),
], bg=PANEL2)

para("4.2 &nbsp; What gets deleted / neutralised", H3)
bullets([
    "<font face='Courier'>core_weighted_coverage_fraction</font> + CORE_BLEND / CORE_RADIUS_M / N_CORE_REF &mdash; <b>removed from the decision path.</b>",
    "<font face='Courier'>delta_tmrt_surrogate</font> / MAX_TMRT_REDUCTION_C (12 &deg;C) / TREE_SHADE_FRACTION / canopy-radius proxy &mdash; <b>out of the objective.</b> (May survive as a labelled, ranking-only proposer; never reported as &deg;C.)",
    "Mock UTCI scalars (41.0 / 30.5) + mock TCS &mdash; <b>removed from the demo path</b>; mock cannot run by accident (&sect;5).",
    "<font face='Courier'>open_square_site</font> &ldquo;everything plantable&rdquo; &mdash; replaced by building-aware slots.",
])

# ════════════════════════════════════════════════════════════════════════════
# 5. ZERO-MOCK EXIT GATE
# ════════════════════════════════════════════════════════════════════════════
para("5 &nbsp; Zero-mock exit gate", H2)
para("&ldquo;Done&rdquo; = the demo path contains none of the items below in an active state.", BODY)
table(
    [
        ["Item", "Type", "Disposition"],
        ["UTCI scalars 41.0 / 30.5; mock TCS 80h/60h", "TRUE MOCK", "Remove from demo; backend must be cached/live. Hard guard so mock cannot run."],
        ["angels_site.geojson fixture", "TRUE MOCK", "Tests only; demo always uses real fetched polygon."],
        ["MAX_TMRT_REDUCTION_C = 12 &deg;C (unsourced)", "ASSUMPTION", "Deleted from objective (surrogate removed)."],
        ["TREE_SHADE_FRACTION 0.80; radius 3 m", "ASSUMPTION", "Out of objective; crown size comes from real species table for the sim."],
        ["core-weights 0.6 / 6 / 6", "ASSUMPTION", "Deleted."],
        ["MIN_SPACING 4 m; species palette", "ASSUMPTION", "Keep as a stated planting constraint (real arboricultural guideline); cite or expose."],
        ["TOPSIS weights 0.6/0.4", "ASSUMPTION", "Becomes moot under single-metric ranking, or a labelled slider."],
        ["Cost: tree_stock 600 / pit 500 / soil 600", "DECLARED", "Source to BCN tender, or label DECLARED in UI. (guarding/labour/OpEx already VERIFIED.)"],
        ["growth 25y/20%, discount 3.5%, horizon 40y", "DECLARED", "Standard public-CBA conventions; label + expose as inputs."],
    ],
    widths=[58 * mm, 24 * mm, 88 * mm],
)

# ════════════════════════════════════════════════════════════════════════════
# 6. ACTION PLAN (PHASED)
# ════════════════════════════════════════════════════════════════════════════
story.append(PageBreak())
para("6 &nbsp; Action plan &mdash; phased, each phase ships a working demo", H2)
para("Principle: never break the green test suite (267 pass). Each phase is independently shippable, so if time runs out the "
     "last completed phase is still a clean demo. <b>[KEY]</b> = needs INFRARED_API_KEY.", SMALL)

def phase(title, when, items, key=False):
    tag = "  [KEY]" if key else ""
    para(f"{title}{tag} &nbsp;&mdash;&nbsp; <font color='#5b6b61'>{when}</font>", H3)
    bullets(items)

phase("Phase 0 &mdash; Spike &amp; measure (de-risk)", "~1&ndash;2 h", [
    "Set INFRARED_API_KEY; run ONE baseline + ONE single-tree sim to measure real latency per layout and confirm the under-shade grid readout. This sizes the whole sim budget.",
    "Confirm multi-payload batch concurrency on the account (submit 3&ndash;5 layouts in one call).",
    "Deliverable: measured seconds/layout &rarr; pick greedy depth + batch width.",
], key=True)
phase("Phase 1 &mdash; Building-aware candidate slots", "~3 h", [
    "Replace open_square_site with real building/street filtering: fetch footprints (already available), build is_valid_location over a metric grid of slots.",
    "Unit tests: no slot inside a building or within street buffer. Keeps suite green.",
    "Fixes problem #6. No key needed (uses cached/fetched footprints).",
])
phase("Phase 2 &mdash; Single measured metric + KPI", "~3 h", [
    "Make cooled_footprint_m2 (&ge;0.5 &deg;C cells) the one value used for search, ranking, and headline. KPI = &euro;/m&sup2; cooled.",
    "Add under-canopy UTCI readout (mask grid cells under placed crowns; report under-shade vs open).",
    "Fixes problems #4 + #5. Refactor + tests; no key needed.",
])
phase("Phase 3 &mdash; Measured-fitness search engine", "~5&ndash;6 h", [
    "Implement greedy marginal placement: batch-evaluate candidate slots on real UTCI, keep best gain, repeat to budget. Bounded sim count, logged.",
    "Delete surrogate + core-weight from the decision path (problems #1, #2, #3).",
    "Emits per-tree marginal cooling (bonus narrative).",
], key=True)
phase("Phase 4 &mdash; Zero-mock guard + wiring", "~2 h", [
    "Hard guard: demo refuses to run on backend=mock; default to cached/live. Remove mock UTCI from the app path.",
    "Pipeline + app + 3D read the new single metric; before/after uses measured grids only.",
    "Run the &sect;5 exit-gate checklist.",
])
phase("Phase 5 &mdash; Validate, screenshot, re-pitch", "~2&ndash;3 h", [
    "Full live run on 1&ndash;2 hero sites; capture before/after + cooling-diff + per-tree marginal chart.",
    "Rewrite headline: &ldquo;best of N measured Infrared layouts; X m&sup2; cooled &ge;0.5 &deg;C at &euro;Y/m&sup2;; under-shade Z &deg;C cooler.&rdquo;",
    "Then &mdash; and only then &mdash; resume natural-capital multi-yield layer.",
], key=True)

# ════════════════════════════════════════════════════════════════════════════
# 7. AGENTS & SKILLS
# ════════════════════════════════════════════════════════════════════════════
para("7 &nbsp; Agents &amp; skills to deploy", H2)
table(
    [
        ["Phase / job", "Use", "Why"],
        ["Re-frame the analytical core", "skill: crispdm-4-modeling", "Forces measured-fitness design + mandatory sensitivity/robustness; right discipline for &ldquo;optimal&rdquo; claims."],
        ["Plan the sprint", "skill: writing-plans / executing-plans", "Turn this into checkpointed phase plans you approve before code."],
        ["Drive Infrared correctly", "skill: infrared:use-infrared", "Area-API batching, building shade, time-period, grid readout."],
        ["Build the search engine", "agent: AI Engineer", "Implements greedy/batch measured-fitness loop + grid post-processing."],
        ["New pipeline shape", "agent: Backend/Software Architect", "Clean boundary between proposer, measured search, and UI."],
        ["Slots + grid data", "agent: Data Engineer", "Building-aware slot generation; under-shade masking; cached replay."],
        ["Keep it honest/green", "skills: test-driven-development, verification-before-completion", "No claim without a passing test + real-run evidence."],
        ["Source cost/data", "skill: earn-the-data", "Replace DECLARED cost lines with BCN tender values where possible."],
        ["Prove it", "agents: Reality Checker / Evidence Collector", "Screenshots of real runs before any &ldquo;done.&rdquo;"],
    ],
    widths=[42 * mm, 52 * mm, 76 * mm],
)

# ════════════════════════════════════════════════════════════════════════════
# 8. RISKS
# ════════════════════════════════════════════════════════════════════════════
para("8 &nbsp; Risks &amp; mitigations", H2)
table(
    [
        ["Risk", "Mitigation"],
        ["Real-sim latency too high for many evals", "Phase 0 measures it first; cap sim budget; greedy depth scales to measured speed; batch 20-concurrent."],
        ["API quota burn", "Bounded, logged sim count; cache every run for offline replay (cached backend reproduces the demo)."],
        ["Re-architecture breaks the green suite 2 days out", "Phased, each phase shippable; surrogate path retired only after the measured path passes tests."],
        ["&ldquo;Optimal&rdquo; overclaim", "State precisely: best of N measured layouts; show the N and the search method."],
        ["No API key in time", "All no-key phases (1, 2, 4 partial) proceed; live phases gated on your key."],
    ],
    widths=[70 * mm, 100 * mm],
)

# ════════════════════════════════════════════════════════════════════════════
# 9. WHAT I NEED FROM YOU
# ════════════════════════════════════════════════════════════════════════════
para("9 &nbsp; What I need from you", H2)
bullets([
    "<b>INFRARED_API_KEY</b> in the environment (or you run the Phase-0/3/5 driver). Nothing live moves without it.",
    "<b>Go / tweak</b> on the architecture in &sect;4 (greedy measured-fitness + building-aware slots, single &euro;/m&sup2;-cooled metric).",
    "<b>Sim budget ceiling</b> you&rsquo;re comfortable spending (e.g. 60 real evaluations).",
])
para("On approval I start Phases 1&ndash;2 immediately (no key needed), and the moment the key is set I run Phase 0 and proceed. "
     "Natural-capital multi-yield work resumes after Phase 5, as you asked.", BODY)

hr()
para("CoolSpend &middot; infrared.city Buildathon &middot; generated by Claude Code &middot; all figures from your live Infrared cache + repo source.", SMALL)

# ── Build with footer ───────────────────────────────────────────────────────
def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(LINE); canvas.setLineWidth(0.5)
    canvas.line(20 * mm, 15 * mm, 190 * mm, 15 * mm)
    canvas.setFont("Helvetica", 7.5); canvas.setFillColor(MUTE)
    canvas.drawString(20 * mm, 10 * mm, "CoolSpend — Real-Data / Zero-Mock Action Plan")
    canvas.drawRightString(190 * mm, 10 * mm, f"p. {doc.page}")
    canvas.restoreState()

doc = BaseDocTemplate(str(OUT), pagesize=A4,
                      leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm, bottomMargin=20 * mm)
frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="f")
doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=footer)])
doc.build(story)
print(f"WROTE {OUT.resolve()}  ({OUT.stat().st_size} bytes)")
