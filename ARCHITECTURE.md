# CoolSpend — Architecture

> "Read the machine." Four diagrams answer four questions about how CoolSpend
> actually runs — the [IAAC Day-2](https://slides.infrared.city/iaac-day2/)
> toolkit applied to this repo. Each Mermaid block renders on GitHub.

CoolSpend is a two-part app:

- **`web/`** — a React + Vite + deck.gl/Mapbox/Cesium frontend (draw a block in
  Barcelona, see the cooling).
- **`coolspend/`** — a FastAPI backend that runs the real placement + Infrared
  UTCI pipeline and now **remembers** evaluated runs (SQLite + a blob store).

---

## 1 · Component — what are the parts?

```mermaid
flowchart LR
  subgraph Browser["web/ (React + Vite, Vercel)"]
    UI["Scene / ActionRail / ResultCard / SavedRuns"]
    APIc["lib/api.ts<br/>(fetch /api/*, VITE_API_BASE seam)"]
    UI --> APIc
  end

  subgraph Backend["coolspend/ (FastAPI + uvicorn, Render)"]
    API["api_server.py<br/>/api/buildings · /api/evaluate · /api/runs"]
    PIPE["app_pipeline.smart_evaluate<br/>+ export_web.export_web_bundle"]
    SDK["sdk_client.py<br/>(Infrared SDK boundary)"]
    STORE["store.py<br/>(SQLite + blob persistence)"]
    API --> PIPE
    PIPE --> SDK
    API --> STORE
  end

  subgraph Data["Persistence & data"]
    DB[("SQLite<br/>runs table")]
    BLOB["Blob store<br/>(heatmap PNGs + run.json)"]
    GRID["scored_grid.geojson<br/>citywide cells"]
  end

  EXT["infrared.city API<br/>(UTCI / buildings / ground)"]
  OSM["OSM + Open Data BCN<br/>(buildings, trees, species)"]

  APIc -- "HTTP JSON" --> API
  STORE --> DB
  STORE --> BLOB
  SDK -- "INFRARED_API_KEY<br/>(backend env only)" --> EXT
  PIPE --> OSM
  API --> GRID
```

The Infrared key lives **only** in the backend process (env var). The browser
never sees it — see [§ Exercise B](#exercise-b--the-key-stays-on-the-backend).

---

## 2 · Sequence — what happens, in what order?

The draw → evaluate → **save → reload** loop. Save/reload is the new "memory".

```mermaid
sequenceDiagram
  actor U as User
  participant W as web (Scene)
  participant A as FastAPI (api_server)
  participant P as pipeline + Infrared
  participant S as store.py
  participant DB as SQLite + blobs

  U->>W: draw polygon
  W->>A: POST /api/buildings {polygon}
  A-->>W: building/impervious preview
  U->>W: Evaluate
  W->>A: POST /api/evaluate {polygon, budget}
  A->>P: smart_evaluate → UTCI baseline/intervention → export_web_bundle
  P-->>A: bundle (decision, trees, heatmap PNGs → eval_bundle/)
  A-->>W: payload (JSON + image URLs)
  W-->>U: render 3D scene + Result Card

  U->>W: Save this run (name)
  W->>A: POST /api/runs {name, polygon, payload}
  A->>S: save_run(...)
  S->>DB: INSERT row + copy PNGs to blobs/runs/<id>/
  A-->>W: {id}

  Note over U,DB: ...page refresh — memory persists...
  U->>W: open Saved runs
  W->>A: GET /api/runs
  A->>S: list_runs()
  S-->>A: rows (headline KPIs)
  A-->>W: gallery list
  U->>W: click a run
  W->>A: GET /api/runs/{id}
  A->>S: get_run(id) → read blobs/runs/<id>/run.json
  A-->>W: evaluate-shaped payload (image URLs → /blobs)
  W-->>U: re-render the saved scene
```

---

## 3 · Entity-Relationship — what data, and how is it related?

One table. The slides' Exercise-A split: **queryable metadata in columns**, the
**heavy heatmap files in the blob store**, and the row holds **only a link** to
them (`blob_url`) — never the bytes.

```mermaid
erDiagram
  RUNS ||..|| BLOB_DIR : "blob_url points at (link, not bytes)"

  RUNS {
    integer id PK "AUTOINCREMENT"
    text    created_at "ISO-8601 UTC"
    text    name
    text    backend "mock | cached | live"
    text    polygon_json "drawn ring [[lon,lat]...]"
    real    budget_eur
    real    w_thermal
    real    w_ecological
    real    delta_utci_c "headline KPI"
    real    cooled_m2    "headline KPI"
    integer n_trees      "headline KPI"
    real    cost_eur     "headline KPI"
    real    eur_per_m2   "headline KPI"
    text    blob_url "FK-style link → blobs/runs/<id>/"
  }

  BLOB_DIR {
    file run_json "full evaluate payload"
    file utci_baseline_png "big file"
    file utci_intervention_png "big file"
  }
```

Exactly how Infrared itself works: a database for metadata, object/blob storage
for the heavy rasters. Swap seams (no caller changes): `DATABASE_URL` →
Postgres/Neon, `BLOB_DIR`/`BLOB_BASE_URL` → S3/R2.

---

## 4 · Deployment — where does each part run?

```mermaid
flowchart TB
  user["Browser"]

  subgraph Vercel["Vercel (static)"]
    static["web/ build (Vite)<br/>VITE_API_BASE → Render"]
  end

  subgraph Render["Render (web service)"]
    uvicorn["uvicorn coolspend.api_server:app"]
    disk[("Persistent disk<br/>coolspend/var/<br/>coolspend.db + blobs/")]
    uvicorn --- disk
  end

  infrared["infrared.city API"]
  neon[("Neon Postgres<br/>(optional prod swap)")]

  user --> static
  static -- "/api/* (HTTPS)" --> uvicorn
  uvicorn -- "INFRARED_API_KEY (secret env)" --> infrared
  uvicorn -. "DATABASE_URL (when scaling past SQLite)" .-> neon
```

SQLite on the Render disk is the MVP. **Caveat:** a free-tier redeploy can reset
that disk — for durable storage point `DATABASE_URL` at Neon and the blob store
at S3/R2. See [`DEPLOY.md`](./DEPLOY.md).

---

## Exercise B — the key stays on the backend

The slides' leak exercise (`const KEY = "sk-infrared-…"` in frontend code) — **this
repo never had it.** `INFRARED_API_KEY` is read by the SDK from the backend
environment only; it is never accepted over HTTP, never logged, never returned
(`coolspend/api_server.py` header; `coolspend/sdk_client.py:_live_utci` key
check). The browser calls **our** backend; the backend calls Infrared. The
`VITE_API_BASE` env var in the frontend is only a public backend URL — not a
secret.

## Registry pattern — noted, not built

The slides suggest a registry so "add a simulation = one file + one line."
CoolSpend runs a single sim family (Infrared UTCI / TCS), so a multi-sim registry
would be speculative abstraction today. The seam to add: a `metric -> runner` map
in `sdk_client.py` if/when a second metric (e.g. wind/PWC) is wired.
