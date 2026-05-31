# CoolSpend — Explainer Film (Remotion + Higgsfield)

A ~11-minute cinematic explainer that walks through the entire CoolSpend system —
the problem of urban heat, the UTCI metric, the four real data sources, candidate-slot
generation, the greedy shade-gain placement engine, the ecological plantability gate,
growth + cost, optimise-then-validate on live Infrared UTCI, the €1M city-wide
portfolio, the honesty architecture, and the limitations.

It plays as a full-screen autoplay intro gate when the web app opens
(`web/src/components/IntroVideoGate.tsx`), then drops the viewer into the live UI.

## How it was made

- **Script** (`SCRIPT.md`, `src/data/scenes.json`): written by a multi-agent workflow whose
  *only* factual source was `../PAPER.md`, then adversarially fact-checked against it.
  Every on-screen number traces to the paper / the live app bundles.
- **Visuals**: Remotion (React) motion graphics for the 7 technical scenes; real
  measured assets for the proof scenes — the live Infrared UTCI rasters
  (`public/app/utci_*.png`), real `trees.geojson`, and live captures of the app
  (`public/app/live-*.png`).
- **Cinematic b-roll**: Higgsfield Seedance 2.0 (`public/clips/*.mp4`) for the opening
  aerial and the closing dusk shot.
- **Voiceover**: edge-tts neural voice `en-GB-RyanNeural`, one file per scene
  (`public/audio/vo_*.mp3`), durations drive each scene's length (`src/lib/timeline.ts`).
- **Music**: "Lightless Dawn" by Kevin MacLeod (incompetech.com), CC-BY 4.0 (see below).

## Rebuild

```bash
npm install
# regenerate VO (needs edge-tts on PATH):  python scripts/gen_vo.py
# regenerate Higgsfield clips (needs higgsfield CLI auth):  bash scripts/gen_clips.sh
npx remotion studio                      # preview
npx remotion render CoolSpend out/coolspend-explainer.mp4 --concurrency=8
```

## Music attribution (required, CC-BY 4.0)

```
Music: "Lightless Dawn" by Kevin MacLeod (incompetech.com)
Licensed under Creative Commons: By Attribution 4.0 License
http://creativecommons.org/licenses/by/4.0/
```
