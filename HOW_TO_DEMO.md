# CoolSpend — How to Run & Verify the Demo

Two surfaces:
- **Gradio app** — the reliable demo. Runs anywhere, no external tokens. Optimizer + real
  Infrared UTCI + before/after map + 3D `.glb` + ranked table.
- **deck.gl web app** (`web/`) — the wow-layer. Photorealistic 3D Barcelona with your
  scenario cut in. Needs two free tokens (Mapbox + Cesium Ion).

Both read the SAME real data. Nothing is invented; mock is clearly labelled "NOT MEASURED DATA".

---

## 1. Gradio app

```powershell
# from repo root, with the venv active
$env:INFRARED_BACKEND="live"      # real Infrared UTCI (needs INFRARED_API_KEY in .env)
python -m coolspend.app           # opens http://127.0.0.1:7860
```

Backends (radio in the UI): **live** = real API · **cached** = replay last live result offline ·
**mock** = synthetic, labelled NOT MEASURED DATA (integration only).

### What "correct" looks like (live run)
- **Headline** like: *"Spend EUR 294,400 → 64 trees cool 3,682 m² of ground by ≥0.5 °C
  (EUR 80/m²), validated by real Infrared UTCI. At sun-exposed spots the felt temperature
  drops 30.9 °C → 30.2 °C."*
- **Before/After map** renders (a PNG, not blank).
- **3D Scene (.glb)** + **Cooling Diff (.glb)** download chips populate.
- **Table**: 3 ranked rows; "Felt-peak °C (base→int)" column shows e.g. `30.9→30.2`.
- **Banner** ends with: *"Presentation bundle exported → outputs/web_bundle/ …"*.
- **Call log** (accordion): 3 lines `UTCI sim call #1..#3` (not "live" wording under mock).

### Red flags (something's wrong)
- Headline shows `cools the plaza X degC` with no m² → grids missing (mock, or live failed).
- Banner says "NOT MEASURED DATA" on a run you intended to be live → backend wasn't live /
  no API key.
- Before/after blank or table empty → check the call-log accordion + server logs.

---

## 2. deck.gl web app (photorealistic 3D)

```powershell
cd web
npm install
# add tokens (see below) to web/.env.local
npm run dev        # http://localhost:5173
```

### Tokens (both free)
- **Mapbox**: mapbox.com → sign up → Dashboard → Tokens → copy the **Default public token**
  (`pk.…`).
- **Cesium Ion**: cesium.com/ion/signup → Access Tokens → copy the default token (`eyJ…`).
  Free tier = 1,000 sessions/month.

Create `web/.env.local`:
```
VITE_MAPBOX_TOKEN=pk.your_token_here
VITE_CESIUM_ION_TOKEN=eyJ.your_token_here
```
Restart `npm run dev` after adding tokens.

### Degradation (never white-screens)
- No tokens → flat dark map + UTCI heatmap + trees + boundary.
- Mapbox only → real basemap + overlays.
- Both → photoreal Google 3D Barcelona with your study area cut in. The hero shot.

### What "correct" looks like
- HUD card: headline + rank-1 KPIs (trees, €, cooled m², €/m², felt-peak base→int, Δ°C).
- UTCI heatmap draped on the ground inside the boundary; baseline↔intervention toggle flips it.
- Tree pins: species-coloured (proposed) + olive (existing).
- Legend for the UTCI colour scale; disclaimer small at the bottom.

---

## 3. Getting REAL data into the web app

The web app reads `web/public/web_bundle/`. Regenerate from a live sim and copy:

```powershell
python -m coolspend.export_web      # live run -> outputs/web_bundle/ (7 files)
Copy-Item outputs/web_bundle/decision.json,outputs/web_bundle/boundary.geojson,`
  outputs/web_bundle/trees.geojson,outputs/web_bundle/bounds.json,`
  outputs/web_bundle/utci_baseline.png,outputs/web_bundle/utci_intervention.png `
  web/public/web_bundle/ -Force
```

To scan a different location, edit the `center_lonlat` in `coolspend/export_web.py`'s
`__main__`, or run the Gradio app at that lat/lon (it auto-writes `outputs/web_bundle/` on
every live run).

The bundle (for claude-design / slides):
- `decision.json` — headline + Top-3 KPIs (incl. felt-peak base/intervention)
- `boundary.geojson` — site ring · `trees.geojson` — proposed + existing trees
- `utci_baseline.png` / `utci_intervention.png` — colorized UTCI rasters (scale 20–40 °C)
- `bounds.json` — `[west,south,east,north]` for the rasters
- `scene.glb` — full 3D scene (buildings + existing + proposed trees)

---

## 4. Honesty notes for the presentation

- **Felt temperature is real UTCI** (air + radiant + wind + humidity), from Infrared, July
  09–17 window. Barcelona reads moderate (~28–31 °C, "moderate heat stress") because it's
  coastal + breezy — see `AUDIT_REPORT.md` "UTCI accuracy investigation". This is correct,
  not a bug; inland Spain would read hotter.
- Lead with **cooled m² per euro** + the **felt-peak drop** — both robust and measured.
- The surrogate ΔTmrt (optimizer objective) carries ±4 °C; the live UTCI is the ground truth.

---

## 5. Tests

```powershell
python -m pytest coolspend/tests -q     # expect: 267 passed, 1 skipped
cd web; npm test                         # expect: 17 passed
```
The 1 skip is a Windows port-bind health-check, not an app failure.
