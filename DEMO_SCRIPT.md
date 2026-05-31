# CoolSpend — Demo Script (~3 min)

The app is the deck.gl + Mapbox web app (`web/`), not the old Gradio UI. All headline
numbers below are the **real live Infrared UTCI** result at Plaça dels Àngels (cached for
offline replay), so the demo is reproducible without burning API calls.

---

## The Hook (0:00–0:20)

**On screen:** the app open on satellite Barcelona, the plaza result already loaded.

**Narrator:**
> "Maria is Barcelona's Chief Heat Officer. Fixed budget, heatwave coming. Her question
> isn't 'where is it hot' — it's 'where does each euro buy the most cooling, and the
> healthiest ecosystem?' This is CoolSpend."

---

## Shot List

| # | Time | On screen | Narrator | Do |
|---|------|-----------|----------|----|
| 1 | 0:20 | HUD + plaza, satellite | "Plaça dels Àngels. For €129,000, CoolSpend places 28 trees that cool **4,268 m² of ground by at least half a degree — about €30 per square metre cooled**. Validated on the real Infrared UTCI engine." | Point at the headline + KPI tiles. |
| 2 | 0:35 | Baseline / With trees toggle | "This is the measured felt-temperature map. Baseline…" *(click Baseline)* "…and with the trees in. Peak comfort at the sun-exposed spots drops from 31 to 29.8 degrees." | Toggle Baseline ↔ With trees; let the heatmap change. |
| 3 | 0:55 | Cooling-depth tile | "It's not a thin half-degree everywhere: 3,260 m² cooled by ≥1°, 1,716 m² by ≥2°, and 664 m² lifted out of heat stress entirely." | Point at the cooling-depth row. |
| 4 | 1:10 | Click a tree → inspect panel | "Every tree is a real species. Click one — a Judas tree, native to the Mediterranean. You see its shade footprint, and its full **ecosystem profile**: drought tolerance, pollinator value, allergenicity, pest risk. It scores top of the palette because it's native and low-burden." | Click a canopy disk; walk the panel meters. |
| 5 | 1:35 | Species chips / note | "And what's NOT here matters: CoolSpend won't recommend the species Barcelona is phasing out — black locust, privet, Siberian elm are excluded as invasive, straight from the city's Pla Director de l'Arbrat." | Point at species chips (no invasives). |
| 6 | 1:55 | Switch to Citywide mode | "Zoom out. Same euro, whole city. CoolSpend ranks all 494 Barcelona cells by heat and sealed surface and allocates a million euros to the hottest first — Sant Andreu, Sants-Montjuïc, 44 to 48 degrees." | Click **Citywide**; show the priority heatmap + ranked chips. |
| 7 | 2:15 | Draw a polygon → Evaluate | "Or design anywhere: draw an area, set a budget, evaluate." | Draw a small polygon, set budget, click Evaluate; show the result render. |

---

## The Close (2:30–3:00)

**On screen:** back on the plaza, heatmap + canopy disks.

**Narrator:**
> "Real Infrared UTCI, building-aware, on Barcelona's real tree inventory and the city's
> own planting strategy. 28 trees, 4,268 square metres cooled, thirty euros a metre — and
> an ecosystem, not just shade. That's a number Maria can defend to a budget committee.
> Any area, any budget, anywhere in Barcelona. That's CoolSpend."

*End on the live result, not a terminal.*

---

## Recording the app

Two local servers (the live result is cached, so no API key is needed to demo):

```powershell
# 1. backend API (drawing + citywide). Mock lets you evaluate ANY drawn area instantly.
$env:INFRARED_BACKEND="mock"; python -m uvicorn coolspend.api_server:app --port 8000
# 2. web app
cd web; npm run dev      # opens http://localhost:5173
```

The default plaza view loads the **cached live** bundle (`backend=cached`, real Infrared
UTCI) — that's the showcase. Drawing a new area evaluates on the mock backend (a labelled
synthetic preview); the live backend handles new areas when an API key is present.

Tokens needed in `web/.env.local`: `VITE_MAPBOX_TOKEN` (basemap). `VITE_CESIUM_ION_TOKEN`
is optional (photoreal 3D, currently off by default).

**To re-generate the live showcase** (one real run, ~few sims):
```powershell
$env:INFRARED_BACKEND="live"; python -m coolspend.export_web
```

---

## Final manual step (USER)

The agent cannot record video. Record a ~3-min screen capture following the shot list
(OBS / Loom / macOS Cmd+Shift+5), upload it, and paste the URL into SUBMISSION.md under
`Demo video:`. Repo + deployed app + video = the complete deliverable.
