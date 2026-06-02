# Deploy CoolSpend to a live URL

The [IAAC Day-2](https://slides.infrared.city/iaac-day2/) "ship it" path:
**frontend → Vercel · backend → Render · (optional) database → Neon.** `main` is
production; open a PR for a preview URL.

```
Browser ──> Vercel (web/, static)  ──/api/*──>  Render (coolspend FastAPI)  ──>  infrared.city
                                                      │
                                                      └── coolspend/var/  (SQLite runs + blobs)
```

Two moving parts you provide: an **Infrared API key** and (free) **Render** +
**Vercel** accounts. Mapbox/Cesium tokens are optional (the map degrades without
them).

---

## 1 · Backend → Render

Config lives in [`render.yaml`](./render.yaml).

1. Push this repo to GitHub.
2. Render → **New → Blueprint** → pick the repo. It reads `render.yaml` and
   creates the `coolspend-api` web service:
   - build `pip install -r requirements-api.txt`
   - start `uvicorn coolspend.api_server:app --host 0.0.0.0 --port $PORT`
   - mounts a 1 GB disk at `coolspend/var` for the SQLite DB + saved-run blobs.
3. Set the secret env vars in the dashboard (left as `sync:false`):
   - `INFRARED_API_KEY` — your infrared.city key (**secret**; never commit it).
   - `CORS_ORIGINS` — your Vercel URL, e.g. `https://coolspend.vercel.app`
     (comma-separate multiple). Without it the browser blocks the cross-origin
     `/api` fetch.
   - `INFRARED_BACKEND` — `live` (real UTCI, ~60–90 s/eval) or `cached` (replays
     the bundled showcase, mock for new draws). Default in the blueprint: `live`.
4. Deploy. Verify: `https://<service>.onrender.com/api/health` → `{"status":"ok","backend":"live"}`.

> Free instances sleep after inactivity (first request is slow) and the disk can
> reset on redeploy. For durable storage see [§4](#4--durability-swap-when-you-outgrow-sqlite).

## 2 · Frontend → Vercel

Config lives in [`web/vercel.json`](./web/vercel.json).

1. Vercel → **New Project** → same repo. Set **Root Directory = `web`** (the app
   is in the subfolder; Vercel then auto-detects Vite).
2. Environment variables:
   - `VITE_API_BASE` — your Render backend URL, e.g. `https://coolspend-api.onrender.com`
     (no trailing slash). This is the seam in `web/src/lib/api.ts` — a public URL,
     **not** a secret.
   - `VITE_MAPBOX_TOKEN`, `VITE_CESIUM_ION_TOKEN` — optional (see
     `web/.env.local.example`). Without Mapbox the app uses the flat fallback map.
3. Deploy → open the Vercel URL.

## 3 · Acceptance test (the slides' bar: "save → refresh → it's still there")

On the live Vercel URL:

1. Enter the app → **Mode: Design** → draw a block in Barcelona → **Evaluate**.
2. On the Result card → **⤓ Save this run** → name it.
3. **Refresh the page.** Go to Design → the **Saved runs** panel (bottom-left)
   still lists it.
4. Click it → the saved scene re-renders (heatmap PNGs served from `/blobs`).

If step 3 survives a refresh, the app remembers — persistence works end to end.

## 4 · Durability swap (when you outgrow SQLite)

SQLite-on-disk is the MVP. `coolspend/store.py` exposes env seams so production
durability is a config change, not a rewrite:

| Concern | MVP (default) | Production swap |
|---|---|---|
| Metadata DB | SQLite file (`DATABASE_URL` unset) | `DATABASE_URL=postgres://…` (Neon) — add a driver in `store.py` |
| Blob store | local dir (`BLOB_DIR`) | `BLOB_DIR`/`BLOB_BASE_URL` → S3/R2-backed mount |

The contract never changes: **metadata in rows, big files in the blob store, the
row holds only the link.** (`store.py` raises `NotImplementedError` for a
non-SQLite `DATABASE_URL` rather than silently writing local — wire the driver
when you take that step.)

## Secrets — the one rule

`INFRARED_API_KEY` lives **only** in the Render backend env. The browser never
sees it: frontend → your backend → Infrared SDK. The frontend's `VITE_API_BASE`
is a public URL, never a key. (This repo never put the key in frontend code — see
[`ARCHITECTURE.md` § Exercise B](./ARCHITECTURE.md#exercise-b--the-key-stays-on-the-backend).)
