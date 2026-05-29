# Agent Brief — Speckle Visual + Provenance Layer for CoolSpend

**For:** an agent tasked with designing/building the same engine-output → procedural-3D → Speckle
provenance layer we built for the parent project (NatureGooddest/COOLSTOCK), instantiated for **CoolSpend**.
**Created:** 2026-05-22 · **Source pattern:** COOLSTOCK Phase V (proven V0 spike + deep-research).
**Read first:** `.planning/PROJECT.md` (this repo). Reference implementation (if you can access the parent
repo `../NatureGooddest/`): `scripts/viz/v0_spike.py`, `phase-2/speckle_leverage_report_2026_05_21.md`,
`.planning/phase-visual-layer/PLAN.md`.

---

## 0. ⚠️ Scope reality check — READ BEFORE BUILDING

CoolSpend is a **3-day hackathon** build (May 27–31), judged **decision > visualization**, demo surface =
**Gradio on Hugging Face Spaces**. `PROJECT.md` Out-of-Scope explicitly lists *"Three.js viewer — parent-project
baggage."* The **keystone is the surrogate-vs-Infrared validation study (VALID-01/02/03)** — everything else is
downstream.

Therefore this layer splits in two, and you must treat them differently:

- **PROVENANCE/AUDIT half — genuinely fits CoolSpend.** A versioned Speckle commit of each budget allocation, with
  a per-tree dossier (€/°C, ΔUTCI, species, cost, location), directly serves three EXISTING CoolSpend requirements:
  *audit manifest*, *GIS layer interop*, and *grant-compliance packaging*. The version-diff ("budget v1 spent here,
  v2 spent there") is literally CoolSpend's "a decision, not a heatmap" thesis made tangible. **Worth doing IF the
  keystone + allocation + Gradio demo are already locked and time remains.**
- **3D-VIEWER half — stretch/optional, and partially contradicts a logged decision.** Embedding a Speckle 3D viewer
  is "a 3D viewer," which `PROJECT.md` ruled out. Do NOT build it on the hackathon critical path. If pursued, get
  Rafik's explicit OK first and treat it as last-day polish only.

**Default recommendation:** ship the provenance/audit + GLB export as a clean optional module behind a flag; do the
embedded interactive viewer only as a post-deadline / "v2.1" stretch. Never let this delay VALID-01/02/03 or the demo video.

---

## 1. The transferable system (what you are designing)

A five-stage layer that turns any spatial-optimizer output into a versioned, queryable, viewable 3D model where
every object carries an auditable dossier:

```
optimizer output (placed things + per-thing metrics)
   │
[V1] procedural geometry  — pure-Python (trimesh) builds a mesh per placed thing from a parametric form recipe
   │
[V2] dossier binding      — attach per-object provenance/metric data (the audit dossier)
   │
[V3] Speckle commit       — specklepy v3 → one DataObject per thing → versioned Model (audit trail / "GitHub for the design")
   ├─[V4] GLB export       — trimesh → .glb for offline/embeddable fallback
   └─[V5] viewer (STRETCH) — embed model; click object → dossier card
```

This is project-agnostic. It works for ANY optimizer that places discrete elements in space with per-element metrics.

## 2. COOLSTOCK → CoolSpend variable binding

| Abstraction | COOLSTOCK (parent) | **CoolSpend (this project)** |
|---|---|---|
| Engine output | `placement_*.geojson` (cooling modules) | `optimizer.py` ranked allocation (placed trees [+ cool-roofs in v2]) |
| Placed "thing" | a pattern module (canopy, wall…) | **a planted tree** (and v2: a cool-roof patch) |
| Form recipe | frame-lattice + skin-membrane | **trunk cylinder + canopy ellipsoid**, sized by species + growth horizon; cool-roof = extruded footprint polygon |
| Dimensions source | pattern YAML decision_variables | species table (mature height, canopy radius), growth-horizon year |
| Per-object dossier | material·source·distance·cost·kgCO₂e·DOI | **species · cost_eur · ΔUTCI_relief · €/°C (headline KPI) · location · growth_horizon_yr · equity_weight · honesty_status** |
| Grouping | one Collection per pattern | **one Collection per intervention type** (trees / cool-roofs); site polygon as a context object |
| Material proxy | RenderMaterial per material | RenderMaterial per **species** (canopy green variants) |
| Versioning meaning | design iteration | **budget allocation iteration** (v1 vs v2 spend) — fits "decision not heatmap" |
| Demo surface | `/proto` static app | **Gradio app** (HF Spaces) — embedding is awkward; see §6 |

## 3. Proven technical facts — REUSE THESE, do not re-discover

specklepy **3.x = next-gen** (Projects/Models/Versions, NOT Streams/Branches/Commits). `app.speckle.systems` uses
**Workspaces**. Verified-working commit flow from the parent V0 spike:

```python
client = SpeckleClient(host="app.speckle.systems")            # host without scheme
client.authenticate_with_token(TOKEN)                          # token from .env: SPECKLE_TOKEN
# project MUST be created inside a workspace on app.speckle.systems:
from specklepy.core.api.inputs.project_inputs import WorkspaceProjectCreateInput
from specklepy.core.api.enums import ProjectVisibility
ws = client.active_user.get_workspaces().items[0]              # pick the right workspace
project = client.project.create_in_workspace(WorkspaceProjectCreateInput(
    name="CoolSpend", workspaceId=ws.id, visibility=ProjectVisibility.WORKSPACE))  # visibility REQUIRED
# build objects, then:
transport = ServerTransport(stream_id=project.id, client=client)   # kwarg still named stream_id (=project id)
obj_id = operations.send(root, [transport])
model = client.model.create(CreateModelInput(name="alloc-run", project_id=project.id))
client.version.create(CreateVersionInput(object_id=obj_id, model_id=model.id,
                                         project_id=project.id, message="budget run <id>"))
```

**Object model (locked from deep-research):**
- Each placed thing = `DataObject(name, applicationId="<type>-<idx>", properties={dossier scalars}, displayValue=[mesh])`.
  A **raw Mesh sent alone is INVISIBLE** — always wrap in DataObject with `displayValue`.
- Dossier = **attached** plain scalars (queryable + viewer-visible). Geometry = **detached** + chunked:
  `obj.add_detachable_attrs({"displayValue"})`, `obj.add_chunkable_attrs(vertices=10000, faces=10000)`.
- **`applicationId` is mandatory** — stable per-tree id → re-runs UPDATE not duplicate, AND it's the key the
  version-diff matches on. (The "budget v1 vs v2" diff depends on this.)
- **Property-name gotcha:** keys cannot contain `.` or `/` or start with `@@`. Use `cost_eur`, `eur_per_degc`, not `€/°C`.
- Group with `Collection` objects (have `elements`, no `displayValue`); leaves are DataObjects (have `displayValue`).
- Share species materials via root-level `RenderMaterial` proxies referencing object ids.
- mesh = `Mesh(vertices=[flat x,y,z…], faces=[3,i,j,k, …], units="m")`.

**Audit/versioning (Python, the document of record):** query `project → model → versions {id, message, authorUser,
createdAt, referencedObject, parents}` via GraphQL; receive two versions' trees, match by `applicationId`, diff the
dossier fields → the allocation-change record. Viewer DiffExtension = the pitch screenshot only. ⚠️ verify the exact
v3 `version` selection set at `/explorer` before hardcoding; null-guard `referencedObject`.

## 4. Two collisions carried from the parent research (do not re-learn the hard way)

1. **Speckle Automate is cloud-only + Enterprise-only + NOT self-hostable.** If CoolSpend ever wants
   auto-run-checks-on-commit, re-implement as your own post-commit Python check, not Automate.
2. **Self-host lacks Workspaces (likely).** The commit flow above uses `create_in_workspace`; on a self-hosted
   Apache-2 server that call may not exist. CoolSpend ships on **hosted HF + hosted Speckle**, so this is a
   non-issue for the hackathon — but don't promise a self-hosted variant without re-testing.

## 5. Geometry recipe for CoolSpend (V1 detail)

```python
def build_tree(x, y, species, growth_horizon_yr) -> trimesh.Scene:
    h, r = species_dims(species, growth_horizon_yr)   # mature/horizon-scaled height + canopy radius
    trunk  = trimesh.creation.cylinder(radius=0.15, height=h*0.4)   # translate to (x, h*0.2, y)
    canopy = trimesh.creation.icosphere(radius=r)                   # translate to (x, h*0.7, y), scale ellipsoid
    # color canopy via RenderMaterial proxy per species; trunk brown
    return trunk + canopy
# cool-roof (v2): extrude the roof footprint polygon a few cm, light-albedo material.
```
Coordinates: keep a single CRS end-to-end (CoolSpend requirement). If allocation is lat/lon, project to the site's
metric CRS before meshing; record the CRS on the root object's properties.

## 6. Viewer for a Gradio app (V5 — STRETCH)

- Gradio can host raw HTML via `gr.HTML`. Simplest: an **iframe embed** of the public Speckle model (read-only 3D
  of the allocation). No click→card (iframe can't push selection out). Cheap, honest, decent.
- Full click→dossier needs `@speckle/viewer` in custom JS — awkward inside Gradio and against the logged
  Three.js-out decision. **Do not attempt for the hackathon** unless Rafik green-lights post-deadline.
- For judging, the stronger artifact is the **before/after map + ranked allocation table + the version-diff audit
  manifest** — all of which the provenance half produces without any 3D viewer. Lead with the decision.

## 7. Honesty rules (CoolSpend's own contract — obey, do not import COOLSTOCK's)

- Every mock/surrogate → CoolSpend **MOCKS ledger**; data tagged VERIFIED / PENDING / DECLARED.
- **No fabricated/inferred citations** — deep-research agents have hallucinated DOIs in this repo before. Any DOI in
  a dossier must be source-verified.
- Surrogate honesty: the dossier sells "UTCI relief" but the optimizer uses a ΔTmrt **surrogate** with an unsourced
  12°C cap — this **unit substitution + cap must be DISCLOSED** in the dossier (e.g. `metric_basis: "ΔTmrt surrogate,
  pending UTCI calibration"`), never silently labeled "UTCI."
- AI-gen images (if any) → flagged in the MOCKS ledger, art-direction-only.

**⚠️ Constraint difference from the parent:** COOLSTOCK has a HARD "never auto-trigger Infrared" rule. CoolSpend is
the OPPOSITE — it is *built* to call Infrared, but only to **validate Top-3** behind a **`SimBudget` guard**, NEVER
per-optimizer-evaluation. Respect CoolSpend's SimBudget guard; do not import COOLSTOCK's manual-only rule.

## 8. Suggested phase order for this layer (only after keystone + demo are safe)
1. V1 geometry (`viz/build_scene.py`) — trees from the allocation; verify mesh count == placed-tree count.
2. V2 dossier binding — attach €/°C, ΔUTCI(+basis), species, cost, location, equity, honesty_status.
3. V3 commit (`viz/commit_speckle.py`) — versioned Model per allocation run; applicationId per tree.
4. V3-audit — Python version-diff → allocation-change manifest (serves the grant/audit requirement).
5. V4 GLB export (offline/interop).
6. V5 viewer — iframe embed only, stretch.

Deliver each behind a flag so none of it can break the core decision pipeline or the demo.
