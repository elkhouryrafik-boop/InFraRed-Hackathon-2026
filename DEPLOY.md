# Deploy CoolSpend to a live URL

The [IAAC Day-2](https://slides.infrared.city/iaac-day2/) "ship it" path:
**frontend → Vercel · backend → Render · database → Render Postgres (free).** `main`
is production; open a PR for a preview URL.

```
Browser ──> Vercel (web/, static)  ──/api/*──>  Render (coolspend FastAPI)  ──>  infrared.city
                                                      │
                                                      └── Render Postgres  (runs metadata + heatmap blobs)
```

The `render.yaml` blueprint provisions the FastAPI service **and** a free Postgres
together and injects `DATABASE_URL` automatically. Saved runs — metadata *and* the
heatmap PNG bytes — live in Postgres, so they survive redeploys; the free web tier
has no persistent disk, which is exactly why the data goes in the DB, not a file.
Locally, `DATABASE_URL` is unset and the same code uses a SQLite file (no setup).

Two moving parts you provide: an **Infrared API key** and (free) **Render** +
**Vercel** accounts. Mapbox/Cesium tokens are optional (the map degrades without
them).

---

## 1 · Backend → Render

Config lives in [`render.yaml`](./render.yaml).

1. Push this repo to GitHub.
2. Render → **New → Blueprint** → pick the repo. It reads `render.yaml` and
   creates **both** the `coolspend-api` web service and a free `coolspend-db`
   Postgres, wiring `DATABASE_URL` between them automatically:
   - build `pip install -r requirements-api.txt`
   - start `uvicorn coolspend.api_server:app --host 0.0.0.0 --port $PORT`
   - `DATABASE_URL` injected from `coolspend-db` (saved runs persist here).
3. Set the secret env vars in the dashboard (left as `sync:false`):
   - `INFRARED_API_KEY` — your infrared.city key (**secret**; never commit it).
   - `CORS_ORIGINS` — your Vercel URL, e.g. `https://coolspend.vercel.app`
     (comma-separate multiple). Without it the browser blocks the cross-origin
     `/api` fetch.
   - `INFRARED_BACKEND` — `live` (real UTCI, ~60–90 s/eval) or `cached` (replays
     the bundled showcase, mock for new draws). Default in the blueprint: `live`.
4. Deploy. Verify: `https://<service>.onrender.com/api/health` → `{"status":"ok","backend":"live"}`.

> Free web instances sleep after inactivity (first request is slow). Saved runs are
> safe across sleeps/redeploys because they live in Postgres, not on the disk. Note
> Render's free Postgres is removed ~30 days after creation — see [§4](#4--durability-notes).

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

## 4 · Durability notes

`coolspend/store.py` speaks **both** SQLite and Postgres off one `DATABASE_URL`
seam — no code change to move between them:

| Concern | Local default | Production (Render blueprint) |
|---|---|---|
| Metadata DB | SQLite file (`DATABASE_URL` unset) | Render Postgres (`DATABASE_URL` injected) |
| Heatmap blobs | `blobs` table in the SQLite file | `blobs` table (BYTEA) in Postgres |

The contract: **metadata in rows, heatmap bytes in the `blobs` table, the metadata
row holds only the link.** Bytes live in the DB (not a file) precisely so saved
runs survive a diskless free host. Two future swaps, both config-only: upgrade the
Render Postgres `plan` past free (the free DB is deleted ~30 days after creation),
or, if blob volume outgrows the DB, point `BLOB_BASE_URL` at an S3/R2 object store
(the blob get/put functions in `store.py` are the single seam to change).

## Secrets — the one rule

`INFRARED_API_KEY` lives **only** in the Render backend env. The browser never
sees it: frontend → your backend → Infrared SDK. The frontend's `VITE_API_BASE`
is a public URL, never a key. (This repo never put the key in frontend code — see
[`ARCHITECTURE.md` § Exercise B](./ARCHITECTURE.md#exercise-b--the-key-stays-on-the-backend).)
