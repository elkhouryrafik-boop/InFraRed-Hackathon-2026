---
title: CoolSpend Tree Budget Optimizer
emoji: 🌳
colorFrom: green
colorTo: blue
sdk: gradio
sdk_version: 4.44.1
app_file: coolspend/app.py
pinned: false
---

## CoolSpend — Tree Budget Optimizer

CoolSpend is a heat-mitigation budget decision-support tool built for the infrared.city SDK Buildathon (Tree Budget track). A city Chief Heat Officer provides a site polygon and a fixed planting budget. CoolSpend runs a baseline UTCI thermal-comfort simulation, identifies the hottest, most sun-exposed street locations, and uses a multi-objective NSGA-II optimizer to propose where to plant trees so that each euro buys the most degrees of street-level comfort relief. The result is a ranked budget allocation and a before/after UTCI map — a defensible decision, not just a heatmap.

The app defaults to Plaça dels Àngels, Barcelona (real Infrared SDK data already validated in the reference project). Switch the polygon text box to any GeoJSON site to run a new optimization.

## Run locally (offline, no API key)

Install dependencies:

```
pip install -r requirements.txt
```

Launch the Gradio UI in mock mode (no key required):

```
python -m coolspend.app
```

Headless smoke test (no browser, no server):

```
python -c "import coolspend.app as a; a.build_demo()"
```

Full test suite (offline):

```
python -m pytest coolspend/tests/ -q
```

## Deploy to Hugging Face Spaces

This is the user's final step (Infrared API key issued at hackathon kickoff May 27).

1. Go to huggingface.co → New → Space → SDK: Gradio → give it a name.
2. Push this repo to the Space (or connect the GitHub repo via Settings → Repository).
   The `README.md` YAML header above makes Hugging Face recognise it as a Gradio Space and
   sets `app_file: coolspend/app.py` as the entry point.
3. Hugging Face automatically installs `requirements.txt` on each build — no extra config needed.
4. The Space starts in mock mode by default (no key required for the public demo).

## Live Infrared backend (real UTCI)

To switch from mock data to real Infrared SDK calls, add two Space Secrets in
Space → Settings → Variables and secrets:

- `INFRARED_BACKEND=live`
- `INFRARED_API_KEY=<your key from the infrared.city hackathon dashboard>`

With these set the app calls the Infrared UTCI API for the Top-3 validated configurations
and shows the real measured UTCI deltas in the call-log panel. **Never commit the key to the
repository.**

mock = NOT MEASURED DATA (surrogate values, synthetic, for integration only)
live = real Infrared UTCI API calls with real measured data

## Honesty / MOCKS note

The thermal surrogate (`delta_tmrt_surrogate`) carries approximately +/-4 degC uncertainty
and the 12 degC cap (`MAX_TMRT_REDUCTION`) is unsourced (no validated citation).
Full details, data-source tags, and the complete MOCKS ledger are documented in
[MOCKS.md](coolspend/MOCKS.md) (Phase 4 / SHIP-02). Do not interpret mock results as
measured data.
