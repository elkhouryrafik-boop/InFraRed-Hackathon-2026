# CoolSpend — Demo Script (2.5–3 min)

**Total runtime budget:** ~3 minutes. The hook and close are fixed at the times shown. The shot list fills the middle 2 minutes — follow it in order but you can trim narration if you run long.

---

## The Hook (0:00–0:20)

**On screen:** terminal, then a browser with the live Gradio app loading.

**Narrator says:**

> "Maria is a city Chief Heat Officer. She has a fixed budget and a heatwave forecast for next month. Her question is simple: where do 12 trees buy the most cooling per euro? Not a heatmap — a decision.
> This is CoolSpend."

*Keep this tight. Do not explain the tech yet. Let the problem land.*

---

## Shot List

| # | Timecode | On Screen | Narrator Says | What to Click / Do |
|---|----------|-----------|---------------|--------------------|
| 1 | 0:20 | Gradio app, default inputs loaded | "The site is Plaça dels Àngels in Barcelona — already loaded as the default. Budget: one million euros. I'll leave the default TOPSIS weights." | Nothing — just show the inputs. Zoom in on the polygon text box and the budget slider. |
| 2 | 0:35 | App input panel, full view | "With the mock backend, every number you see is labelled NOT MEASURED DATA — it is a synthetic placeholder for integration testing. When I switch to the live Infrared backend after May 27, these fields are replaced with real measured values." | Optionally show the backend radio button (mock is selected). |
| 3 | 0:50 | Click "Run Optimization" | "Let's run it." | Click the **Run Optimization** button. |
| 4 | 0:55–1:15 | Spinner, then results appear | "The optimizer is running NSGA-II over 12-tree planting coordinates — about 3,600 surrogate evaluations. Zero real API calls in the hot path." | Wait for results. The call-log panel will appear. |
| 5 | 1:15 | SDK Call Log accordion — expand it | "Here — the SDK call log. You can see the SimBudget guard: exactly three calls to the Infrared UTCI SDK for Top-3 validation. On this mock take, those are mock backend calls — the same code path that fires real API calls when run live with a key." | Click to expand the **SDK Call Log** accordion. Point at each of the three call entries. |
| 6 | 1:30 | Before/after UTCI map panel | "Before and after. The left panel is the open-site baseline UTCI. The right shows the predicted thermal comfort after planting the rank-1 configuration. These are mock values — labelled NOT MEASURED DATA — but the surrogate trade-off is real and the same framework fires live SDK calls when run with a key." | Let the map sit. Point at the two side-by-side images. |
| 7 | 1:50 | Ranked allocation table (3 rows) | "Three configs, three genuinely distinct rows. On the mock backend: rank 1 — MAX THERMAL RELIEF at EUR 1,700 per degree Celsius, rank 2 — BALANCED at EUR 2,084/degC, rank 3 — MAX ECOLOGICAL at EUR 3,194/degC. All three use 12 trees. The optimizer found a real thermal-to-ecological trade-off — each row represents a genuinely different placement strategy. The headline KPI is euros per degree Celsius of UTCI relief, reported as an interval to reflect surrogate uncertainty." | Scroll to or expand the ranked table. Point at the three distinct EUR/degC values in the rank column. |
| 8 | 2:10 | Rank-1 row, cost-per-degree cell highlighted | "The headline KPI: euros per degree Celsius of UTCI relief. On the mock run the rank-1 figure is EUR 1,700/degC — labelled NOT MEASURED DATA and illustrative. On the live run, read the real number off this cell after May 27. That number is Maria's defensible answer." | Point at the cost-per-degree column in the rank-1 row. |

---

## The Close (2:20–3:00)

**On screen:** ranked table still visible, then switch to README or the GitHub page.

**Narrator says:**

> "The headline number on the mock run: EUR 1,700 per degree Celsius of street-level UTCI relief for rank-1 — a mock/illustrative estimate; the cost constants require verification against municipal procurement data, and the live number will differ after the final picks are re-simulated with Infrared UTCI. But the structure is sound: the optimizer finds a real thermal-to-ecological trade-off and the framework runs on any city polygon.
>
> Maria can hand this table to a budget committee. District-scale triage, any city, any planting budget. That is CoolSpend."

*End on the ranked table, not on a blank terminal.*

---

## Recording Commands

### SAFE TAKE — Mock backend, no API key required, always works

Run this first. Use it as your insurance take.

**Bash / Linux / macOS:**
```bash
python -m coolspend.app
```

**PowerShell (Windows):**
```powershell
python -m coolspend.app
```

Open http://127.0.0.1:7860 in your browser (Gradio prints the URL).

**While recording the mock take:** Before clicking Run, say clearly:
> "All numbers you see are NOT MEASURED DATA — synthetic mock values for integration only."

This satisfies the honesty contract on screen. The call-log will still show three SimBudget entries because the mock also goes through the same validation pathway.

**CLI backup (terminal-only shot if Gradio is not available):**
```bash
python -m coolspend.main
```

This prints a text decision summary to the terminal — useful as a fallback B-roll or to prove the headless pipeline works.

---

### LIVE TAKE — Real Infrared UTCI numbers (after May 27 API key issuance)

Use this for your final submission take. Read the actual UTCI and €/°C values off the screen as they appear — do NOT use the mock numbers quoted above.

**Bash / Linux / macOS:**
```bash
export INFRARED_BACKEND="live"
export INFRARED_API_KEY="<your-key>"
python -m coolspend.app
```

**PowerShell (Windows):**
```powershell
$env:INFRARED_BACKEND="live"
$env:INFRARED_API_KEY="<your-key>"
python -m coolspend.app
```

Replace `<your-key>` with your hackathon API key from the infrared.city dashboard. **Never paste a real key into this file or commit it to the repository.**

When the live results appear:
- The banner will no longer say "NOT MEASURED DATA"
- The validated UTCI values will be real measured outputs from the Infrared SDK
- Read the rank-1 EUR/°C figure off the cost-per-degree cell — this is the number to quote in your narration

**Note:** the live validated UTCI and EUR/°C figures will differ from the mock numbers shown in this script. That is expected and intentional — they are different backends.

---

## Final Manual Step (USER)

**The agent cannot record video.** This step is yours.

1. Run the SAFE take first (`python -m coolspend.app`, no key). Record a complete ~3-min run following the shot list above. This is your backup.
2. After May 27 when your API key is issued, run the LIVE take with real credentials. Record a second ~3-min run. Quote the real EUR/°C number from the screen in the close.
3. Upload the video (YouTube, Loom, or direct file). Paste the URL into SUBMISSION.md under `Demo video:`.
4. That is the last step. The GitHub repo + Hugging Face Space + this video = the complete deliverable.

**Recommended recording tools:** OBS Studio (free, cross-platform), Loom (browser capture, quick upload), or macOS screen recorder (Cmd+Shift+5).
