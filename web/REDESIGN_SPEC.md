# CoolSpend — Redesign Spec v4 "Cool Index"

> Lead design architect's merged, decisive, build-ready spec. This supersedes the four expert drafts.
> Where the experts disagreed, the resolution is stated inline and marked **DECISION**.
> Every recommendation maps to a real symbol in the live codebase: `App.tsx`, `Scene.tsx`,
> `Hud.tsx`, `DrawPanel.tsx`, `GrowthSlider.tsx`, `Legend.tsx`, `TreeInspect.tsx`, `useAreaDraw.ts`,
> `lib/layers.ts`, `lib/colorscale.ts`, `lib/bundle.ts`, `lib/types.ts`,
> `public/citywide_plan.json`, `public/eval_bundle/decision.json`.

---

## 1. NORTH-STAR CONCEPT (3 sentences)

**Guided-Sunroof:** a Google-Project-Sunroof "enter a place → personalised, measured result" tool, opened by a short Bloomberg-style guided heat reveal that ends by literally handing the live map to the user — narrative is the on-ramp, the app is the destination. The emulated precedents are **Project Sunroof** (place-in → result-out, the exact interaction analogue to draw-area → cooling), **Tree Equity Score** (one 0–100 score makes a complex composite legible in half a second), and **Bloomberg "Mapping the Coolest Spots"** (cinematic dim-the-context heat storytelling). **DECISION — story vs app conflict (UX draft wanted a phase machine; Narrative draft wanted full scrollytelling):** we sequence them, not blend them — a one-time, one-click-skippable, `localStorage`-gated intro that drives the *real* deck.gl layers (no separate story canvas), then dissolves into a quiet persistent tool where at most **one** dense surface is visible at any moment.

---

## 2. FINAL DESIGN TOKENS (paste-ready)

Create `web/src/styles/tokens.css` and `@import` it first in `main.tsx`. These supersede every inline hex in `Hud.css` / `DrawPanel.css` / `TreeInspect.css`.

**DECISION — accent + heat ramp conflicts.** Two drafts proposed different mints (`#46f0c8` vs `#3BE8C0`) and two different "CVD-safe" ramps (inferno-magma vs cyan→magenta). The Accessibility constraints are binding (release-blockers), so they win: **the heat ramp is the monotonic-lightness CVD-safe ramp** (hot = bright, cool = dark — survives deuteranopia/protanopia/tritanopia and greyscale), and **brand mint = `#3BE8C0`** (deeper, clears AA on glass). The "pretty cyan-cool-end" idea from the Visual draft is preserved only as the *legend's* perceptual feel, not as the data encoding.

```css
:root {
  /* ─── BRAND / ACCENT (mint = "the answer / the active thing"; use SPARINGLY) ─── */
  --brand:        #3BE8C0;   --brand-bright: #5FF6D6;
  --brand-deep:   #0E5C50;   --brand-ink:    #042B25;   /* text ON a mint button */

  /* ─── INK (text on dark) — all pre-cleared on --surface-1 (see §6) ─── */
  --ink-0: #FFFFFF;   /* hero numbers only (~15:1) */
  --ink-1: #EAF3F1;   /* primary text */
  --ink-2: #C2D2DA;   /* secondary / labels (~9:1) */
  --ink-3: #8FA6B0;   /* MINIMUM allowed text — captions/units (~4.6:1). Nothing dimmer for text. */
  --ink-4: #46615B;   /* hairlines / disabled only — NEVER text */

  /* ─── SURFACES — near-opaque so text never relies on the map for contrast (A1) ─── */
  --bg:            #060B0E;
  --surface-1:     rgba(11, 31, 42, 0.93);   /* primary panels — ≥92% opacity (A1 release-blocker) */
  --surface-2:     rgba(18, 28, 33, 0.90);   /* nested cards */
  --surface-3:     rgba(255,255,255,0.06);   /* flat inner wells, slider tracks */
  --surface-scrim: rgba(4, 8, 10, 0.62);     /* onboarding / dialog backdrop */
  --map-pill:      rgba(11, 31, 42, 0.85);   /* scrim for any label floating on the map (A1) */
  --hairline:        rgba(140, 200, 190, 0.18);
  --hairline-strong: rgba(140, 200, 190, 0.30);

  /* ─── DATA RAMP — UTCI 20→40 °C, CVD-SAFE, MONOTONIC LIGHTNESS (B1 release-blocker) ─── */
  /* hot = bright, cool = dark. Survives deuteran/protan/tritan + greyscale. Replaces RdYlBu_r. */
  --t-20: #0D2149;  --t-24: #3A4DA0;  --t-28: #6A5ACD;  --t-32: #B5497A;
  --t-36: #E8602C;  --t-38: #F9A825;  --t-40: #FCE84F;
  --ramp-utci: linear-gradient(90deg,
      #0D2149 0%, #3A4DA0 20%, #6A5ACD 40%, #B5497A 60%, #E8602C 80%, #F9A825 90%, #FCE84F 100%);
  /* diverging ramp ONLY for ΔUTCI cooling effect (B3): teal ↔ neutral ↔ magenta (never red–green) */
  --ramp-delta: linear-gradient(90deg, #1A9988 0%, #F0EAD6 50%, #A6207A 100%);

  /* ─── SEMANTIC / CREDIBILITY (measured mint vs estimate amber — NEVER both at once) ─── */
  --success: #3BE8C0;  --warn: #F0B968;  --danger: #FF7A66;  --info: #6FB6E8;
  --measured: #3BE8C0;  --measured-bg: rgba(59,232,192,0.14);  --measured-border: rgba(59,232,192,0.55);
  --estimate: #F0B968;  --estimate-bg: rgba(240,185,104,0.13); --estimate-border: rgba(240,185,104,0.50);
  --tree-proposed: #3BE8C0;  --tree-existing: #738C6B;   /* = EXISTING_TREE_COLOR [115,140,107] */

  /* ─── TYPE — Fraunces (editorial serif, hero numbers+headline) + Inter (UI) + IBM Plex Mono ─── */
  --font-display: 'Fraunces','Spectral',Georgia,serif;
  --font-ui:      'Inter',system-ui,-apple-system,sans-serif;
  --font-mono:    'IBM Plex Mono','JetBrains Mono',monospace;
  /* scale: ratio 1.25, base 16. FLOOR for meaningful text = 14px (E1 release-blocker). */
  --fs-xs:  0.875rem;  /* 14px  MIN — captions, units, legend ticks */
  --fs-sm:  1rem;      /* 16px  body, controls (also prevents iOS input zoom) */
  --fs-md:  1.125rem;  /* 18px  emphasised body */
  --fs-lg:  1.25rem;   /* 20px  secondary KPI value */
  --fs-xl:  1.75rem;   /* 28px  panel title */
  --fs-2xl: 2.5rem;    /* 40px  big KPI — hero FLOOR (E1) */
  --fs-3xl: 3.75rem;   /* 60px  HERO Cool Score / felt-temp */
  --fs-4xl: 5rem;      /* 80px  onboarding headline */
  --fw-reg:400; --fw-med:500; --fw-semi:600; --fw-bold:700;
  --lh-tight:1.05; --lh-snug:1.22; --lh-body:1.5;   /* body ≥1.4 (E1) */
  --tracking-label:0.10em; --tracking-tight:-0.02em;

  /* ─── SPACING (4px base) ─── */
  --s-1:4px; --s-2:8px; --s-3:12px; --s-4:16px; --s-5:20px; --s-6:24px;
  --s-8:32px; --s-10:40px; --s-12:48px; --s-16:64px;

  /* ─── RADII / ELEVATION / BLUR ─── */
  --r-sm:8px; --r-md:12px; --r-lg:18px; --r-xl:24px; --r-pill:999px;
  --sh-1:0 2px 8px rgba(0,0,0,.35); --sh-2:0 12px 32px rgba(0,0,0,.45); --sh-3:0 24px 64px rgba(0,0,0,.55);
  --sh-glow:0 0 24px rgba(59,232,192,.35); --sh-inset-top:inset 0 1px 0 rgba(255,255,255,.06);
  --blur-panel:20px; --blur-chip:12px; --saturate:135%;

  /* ─── MOTION (all gated by prefers-reduced-motion, §6 D1) ─── */
  --ease-out:cubic-bezier(.22,1,.36,1); --ease-inout:cubic-bezier(.65,0,.35,1);
  --ease-spring:cubic-bezier(.34,1.56,.64,1);
  --t-fast:140ms; --t-base:240ms; --t-slow:420ms; --t-flyto:1200ms;  /* flyto ≤1.2s (D5) */

  /* ─── FOCUS RING (C3 release-blocker, ≥3:1, ≥2px) ─── */
  --focus-ring: #9FE8FF;
}
```

---

## 3. INFORMATION ARCHITECTURE + NARRATIVE STORYBOARD

### 3.1 Single source of truth — replace loose `appMode`

Add a phase machine to `App.tsx`. It absorbs the existing `appMode` and kills the scattered
`appMode === 'draw'` / `=== 'citywide'` conditionals in `Scene.tsx` (lines ~359/369/383/389/405/444/448).

```ts
type Phase = 'intro' | 'design' | 'result' | 'citywide'
type CameraMode = 'auto' | 'user'   // §5: 'auto' runs scripted flyTo; first user gesture flips to 'user'
```

On mount: `phase = localStorage.coolspend_seen === '1' ? 'design' : 'intro'`.
A returning judge boots straight into the tool, parked on a **framed site** (never the all-Barcelona tilt).

### 3.2 Screen map — at most ONE dense surface per screen

**DECISION — panel layout conflict.** UX draft: left Rail + right ResultCard. Visual draft: bottom-left
ResultCard + right Action Rail + top-center mode pill. We adopt the **Visual draft's layout** (it is the
prettier, more legible composition and matches the "presentation is the product" bar), and keep the UX
draft's **phase-gated mounting** rule.

| Phase | Camera | Persistent chrome | Single contextual surface | Primary action |
|---|---|---|---|---|
| `intro` | cinematic auto-fly over rank-1 site | none | `Onboarding` full-bleed (§4.1) | "Draw an area" |
| `design` | live free pan; crosshair when tool armed | top-center **Mode Switch** (§4.3) + right **Action Rail** (§4.4) | none (map is the hero; one hint toast) | Draw → Evaluate lights up on `status==='ok'` |
| `result` | `flyTo` evaluated site, pitch 50, zoom 16.5 | Mode Switch + Action Rail (collapsed) | bottom-left **Result Card** (§4.2) + docked Growth Slider | "See the €1M city plan" |
| `citywide` | fly to BCN overview, then site→site | Mode Switch | bottom-left **Citywide Panel** (§4.6) | click a funded site → drill to a `result`-style read |

**Collapsing the clutter (from 5 simultaneous glass panels → ≤2):**
- **Kill the always-on left `Hud`.** Its showcase KPIs confuse pre-draw users. All KPI display moves into the **Result Card**, mounted only in `phase==='result'`.
- **Demote opacity + legend chrome.** `rasterOpacity` (`Hud.tsx` 142–154) and baseline/intervention toggle move into a single **"Map ▦" popover** on the Action Rail. The `Legend` becomes a small always-visible gradient key bottom-right (§4.8).
- **Dock `GrowthSlider`** inside the Result Card (it is meaningless before a result).
- **Fold the depave-chip** (canopy %, permeable %) into the Result Card's dense meta line.

### 3.3 Scene-by-scene storyboard (real copy)

The intro reuses assets already loaded in `bundle`: `baselineImageUrl` / `interventionImageUrl` (the two UTCI PNGs), `bundle.trees`, `bundle.decision`. No new data. **DECISION — number provenance:** the published single-site `eval_bundle/decision.json` is the **mock preview** (`backend: "mock"`, `delta_utci_c: 0.0`). The intro's payoff numbers MUST come from `citywide_plan.json` (real, `cooling_is_measured: true`) or the live evaluate result — **never render the 0.00 °C mock as "measured"**, or the credibility line becomes false.

**Scene 0 — HOOK** (`intro`). Full-bleed satellite Barcelona, UTCI drape fades 0→100% so the city visibly flushes grey→hot, slow push-in toward the rank-1 hot site.
> **Barcelona is running a fever.** Last summer its hottest streets crossed **44 °C** at ground level — not the air, the pavement people walk on.
Button: **"Show me where."** (`mean_lst_celsius` of the top allocated cell = 44.1 °C, `citywide_plan.json`.)

**Scene 1 — THE PROBLEM** (`intro`). Camera settles tight on La Verneda i la Pau (Sant Martí); everything outside the block desaturates (vignette).
> **This block runs 18 °C over comfort.** Concrete, parked cars, no shade. Nobody planned it this way — it just paved over.
Button: **"What if we planted trees?"** (`mean_lst` − `COMFORT_UTCI_C 26.0`, `placement_inputs.py` — this *is* the optimizer's demand input.)

**Scene 2 — THE INTERVENTION (the money moment)** (`intro`). `bundle.trees` canopy disks animate in (staggered `getRadius` 0→true crown), heatmap cross-fades baseline→intervention; orange cools to mint in place. Gentle orbit (`bearing +20°`).
> **We plant only where a tree can actually go** — never a roof, never a wall, never the road. 8 m apart, the right species for each street's width.
Button: **"How much did that cool?"**

**Scene 3 — THE MEASURED PAYOFF** (`intro` → hands off to `design`). One big number counts up.
> **−3.6 °C, measured.** Not a forecast — we re-ran Barcelona's microclimate with these trees in it.
Button: **"Try it on a real block →"** sets `coolspend_seen='1'`, enters `phase='design'`.

**Scene 4 — DRAW** (`design`). Story chrome dissolves; Action Rail + Mode Switch fade in. One hint toast: "Draw any block in Barcelona." Plantable ground glows teal under the cursor; roofs/facades/carriageways stay dark (real exclusion layers — `osm_buildings`, `osm_roads`, `osm_features`). On `status==='ok'`, Evaluate lights up.

**Scene 5 — THEIR REVEAL** (`design`→`result`). Evaluate spinner becomes a narrated moment (§4 / fix #9). On return: the **same cross-fade + tree-grow-in** as Scene 2, on *their* polygon; camera `flyTo` their site (the bug fix, §5).

**Scene 6 — THEIR PAYOFF** (`result`). Result Card slides up: one hero **Cool Score**, the felt-like transition, a 3-up supporting strip, dense meta line. Click any tree → `TreeInspect`.

**Scene 7 — CITYWIDE €1M** (`citywide`). Camera pulls to all-Barcelona; the scored grid fades to a *whisper-faint* context; the **7 funded sites** drop in one-by-one with a running € ticker, each a mint-ringed pin sized by tree count.
> **A million euros. Seven streets. Spent where the heat hurts most.** We scanned **494** blocks, ranked them by heat and who lives there, and funded the **7** that need it first. **99 trees · €990,000 · €10,000 left.**

**Scene 8 — CALL TO ACTION** (footer in Citywide Panel).
> **Shade is the cheapest climate tech we have.** Barcelona needs **€41 a square metre** and the right tree in the right hole.
Links: **"Cool your own block →"** · **"Replay the story"** (re-enters `intro`).

---

## 4. PER-COMPONENT BUILD SPECS

### 4.1 Onboarding / Hook — NEW `Onboarding.tsx` + `.css`
Full-screen, live UTCI heatmap drifting behind a scrim (`--surface-scrim`), one serif sentence, one primary button per beat, persistent **Skip ▸** corner. `role="dialog" aria-modal="true"`, focus trapped, **Esc closes**, focus returns to trigger.
```
┌──────────────────────────────────────────────────────────────┐
│  (live BCN heatmap, slow push-in, scrim)            Skip ▸    │
│                                                                │
│   ◖ COOLSPEND · Barcelona urban-cooling lab                   │  eyebrow 14px mint, tracking-label
│                                                                │
│   Where should Barcelona                                       │  --font-display 80px ink-0
│   plant trees to beat the heat?                                │  line 2 --ink-2
│                                                                │
│   Draw any block. We place real street trees on valid          │  18px --ink-2, max-width 46ch
│   ground and measure the cooling with Infrared.                │
│                                                                │
│   ┌──────────────────────┐   ┌──────────────────────────┐     │
│   │ ▸ Draw an area       │   │  See the €1M city plan   │      │  primary mint / ghost
│   └──────────────────────┘   └──────────────────────────┘     │
│   ● measured UTCI    ● 0–40 yr growth    ● 7 hot sites         │  proof dots 14px --ink-3
└──────────────────────────────────────────────────────────────┘
```

### 4.2 Result Card — replaces `Hud.tsx` (bottom-left)
ONE hero **Cool Score 0–100** (SVG ring gauge, mint arc on `--surface-3` track, number in `--font-display`) — the Tree-Equity-Score move. Then the felt-like transition, then a 3-up supporting strip, then ONE dense meta line. The 8-tile KPI grid is gone (fix #4). `role="region" aria-label="Cooling results"`; each metric is a `<dt>/<dd>` pair (C6) with units spelled for AT ("m²"→"square metres", "ΔUTCI"→"change in thermal comfort").
```
┌─────────────────────────────────────────────┐
│ ◖ EL RAVAL BLOCK            ● MEASURED   ⤢   │  eyebrow + credibility badge (mint) + expand
│   ┌──────┐  Cooling score                     │
│   │  78  │  strong impact                      │  HERO 60px display; verdict 16px --brand
│   │ /100 │  ▁▂▃▅▇ vs city avg 41               │
│   └──────┘                                     │
│ ───────────────────────────────────────────  │
│   Feels like  34.8° → 31.2°    −3.6 °C ◐      │  from(amber)→to(mint), pill delta
│ ───────────────────────────────────────────  │
│   2,140 m²     €41          1,250              │  20px tabular-nums, captions 14px --ink-3
│   cooled       /m² cooled   people served      │
│ ───────────────────────────────────────────  │
│   64 trees · 22% canopy · Tipa, Hackberry      │  14px --ink-2 dense meta (folds depave-chip)
└─────────────────────────────────────────────┘
```
- Badge: `MEASURED` = `--measured-*`; `PREVIEW` = `--estimate-*`. **Never both at once.** Drive off `bundle.decision.backend !== 'mock' && cooling_is_measured`.
- Hero & felt-temp **count up** over `--t-slow` on first reveal (instant under reduced-motion).

### 4.3 Mode Switch — NEW, top-center floating pill (out of both data zones)
`role="tablist"`, `aria-selected` on segments; Design/Citywide panels are the labelled `tabpanel`s. Animated thumb slides (`--ease-spring`), never a hard repaint.
```
        ┌──────────────────────────────────────┐
        │ ▸ Design        │   Citywide €1M      │   thumb slides under active
        └──────────────────────────────────────┘
```

### 4.4 Action Rail — replaces `DrawPanel.tsx` (right edge, vertical icon rail)
Icon buttons (each ≥44×44, `aria-label`: "Draw cooling area", "Polygon", "Clear", "Map options"). The area readout + Evaluate appear as a single inline popover only when a ring exists (`status==='ok'`). Collapses the fat second panel.
```
                                    ┌────┐
                                    │ ✏  │ Draw area   active = mint ring + glow
                                    ├────┤
                                    │ ⬡  │ Polygon
                                    ├────┤
                                    │ ⌫  │ Clear
                                    ├────┤
                                    │ ▦  │ Map (opacity + baseline/intervention popover)
                                    └────┘
  on draw complete (popover anchored to rail):
  ┌────────────────────────────────────────┐
  │ 0.42 ha · within 0.5 ha cap  ✓          │
  │ ~64 valid spots detected                 │
  │        ┌──────────────────────┐          │
  │        │  ▸ Evaluate cooling  │          │  primary mint; status to aria-live (C8)
  │        └──────────────────────┘          │
  └────────────────────────────────────────┘
```

### 4.5 Growth Slider — `GrowthSlider.tsx`, docked in Result Card (bottom-center fallback)
Native `<input type="range">` (C7). A timeline scrubber with ticks at 0/10/20/30/40, mint fill, canopy % tweening live as you scrub (tabular-nums, no jitter). `aria-valuemin=0 aria-valuemax=40 aria-valuenow aria-valuetext="Year 12 — canopy 18%"`; Left/Right ±1, PageUp/Dn ±5, Home/End 0/40; thumb ≥24×24 (target 44); dependent KPIs update in `aria-live="polite"`.
```
┌──────────────── CANOPY OVER TIME ────────────────┐
│ Year 12                          22% → canopy     │
│ ●━━━━━━━━○──────────────────────────────────────  │
│ 0    10        20        30        40             │
│ newly planted · crown 3.1 m · allometric per spp. │  14px --ink-3
└────────────────────────────────────────────────────┘
```

### 4.6 Citywide Panel — `city-plan` (bottom-left, mirrors Result Card)
Hero strip = **people protected + €1M + ha greened**. Sites become a **ranked leaderboard** with rank medallions and a per-site mint spend bar — prominent + scannable (fix #5). Each row is a real `<button>` (C4) that flies to + spotlights the site. Numbers from `citywide_plan.json`.
```
┌──────────────────────────────────────────────┐
│ ◖ CITYWIDE PLAN              ● €1,000,000      │
│   22,590         7 sites        ~5,412 m²       │  hero strip (people / funded / canopy)
│   people served  funded         new canopy      │
│ ─────────────────────────────────────────────  │
│  ①  Sant Martí · La Verneda  ███████░ €150k ▸  │  rank medallion, mint spend bar,
│  ②  Sant Andreu · Bon Pastor ██████░░ €…  ▸    │  hover → fly-to + spotlight that site
│  ③  Sants-Montjuïc           █████░░░ €…  ▸    │
│  …                                              │
│ ─────────────────────────────────────────────  │
│  494 blocks scanned · funded the 7 hottest first│  14px --ink-3
└──────────────────────────────────────────────┘
```

### 4.7 Tree Inspector — `TreeInspect.tsx` (keep right-bottom; restyle to tokens)
Lead with **common name** (`--font-display`) + scientific (italic), 3-up stat tiles, then horizontal meters for cooling/canopy/drought filled via `--ramp-utci`. Swap hardcoded hex → tokens. `role="dialog"`, accessible name, **Esc closes**, focus returns to marker; appears on focus too (C5/E5). Species by shape/icon + label, not colour alone (B2).

### 4.8 Legend — `Legend.tsx` (gradient key, bottom-right, always visible)
Compact horizontal bar using `--ramp-utci` with **printed numeric breakpoints** at the UTCI stress thresholds (the existing `UTCI_STOPS` values: 26/32/38/46) — colour is never the sole signal (B2). A faint hatch/contour marks the ≥38 °C "very strong" band for greyscale/total-CVD readers.
```
  FEELS-LIKE (UTCI °C)
  ▐░░▒▒▓▓███▌    ◣ hatch ≥38
  20   26   32   38   46+
  cool ·············· extreme
```

### 4.9 The Heat Layer — from "flat orange blob" to a luminous thermal field
Six changes in `lib/colorscale.ts` + `lib/layers.ts`:
1. **Replace `UTCI_STOPS` colours** with the §2 monotonic-lightness CVD-safe ramp (keep the existing `value`/`label` anchors 26/32/38/46 so the legend literature reading is intact).
2. **Smooth, don't pixelate** — render the grid as a blurred bitmap drape (bilinear `BitmapLayer`, σ≈1.2 cells) so it reads as a continuous field, not Lego.
3. **Alpha-by-intensity** — add an alpha ramp export: comfortable cells α≈0.35, extreme α≈0.9, so danger glows and safe zones let the city show through. **This single change kills the "flat blob."**
4. **Bloom on the hottest cells** — a second additive `BitmapLayer` of just the top-quartile cells, blurred wider, low alpha (`parameters:{blendFunc:[GL.SRC_ALPHA, GL.ONE]}`).
5. **Focus vs context (citywide)** — the 7 funded sites stay full-saturation; everything else drops to α≈0.4 + `saturate(0.7)`; funded sites get a 1.5px mint contour ring (`--brand`, `--sh-glow`).
6. **Thin iso-contours** at 26/32/38/46 °C (`rgba(255,255,255,0.12)`) — turns a gradient into readable thermal topography.

---

## 5. deck.gl / MAPBOX CAMERA + LAYER CHANGES

**Fix the camera (the #1 reported bug).** Root cause: `Scene.tsx` initializes `viewState` once (zoom 16 at `site_center_lonlat`, ~lines 74–80) but **never issues an imperative `flyTo`**; `handleEvaluated` (~179) only spreads `longitude/latitude`, keeping stale zoom/pitch; and the bundle center can be a citywide centroid.
```ts
// useEffect keyed on bundle.decision.site_center_lonlat AND on evaluate result:
const map = mapRef.current?.getMap()
if (prefersReducedMotion) {
  map?.jumpTo({ center: [lon, lat], zoom: 16.5, pitch: 50, bearing: -18 })  // D1: instant cut
} else {
  setCameraMode('auto')
  map?.flyTo({ center: [lon, lat], zoom: 16.5, pitch: 50, bearing: -18,
               duration: 1200, curve: 1.42, speed: 0.9, easing: easeInOut })
}
```
- Make `viewState` the **result of `onMove` only**; `flyTo`/`jumpTo` is the authority for programmatic moves.
- **Camera authority flag:** `cameraMode: 'auto' | 'user'`. Intro beats + post-evaluate flights set `'auto'`; the first user drag/zoom (`onMove`) flips to `'user'` and cancels any in-flight fly — this is what lets a power user grab the map to interrupt the story (the "don't trap me" affordance).

**Signature reveal choreography (Evaluate / site-click):** during the ~1.2 s `flyTo`, vignette opacity 0.55→0.85 (dim the city); on arrival fade vignette back, **pop trees in** via deck.gl `transitions:{ getRadius: 800 }` with a 60 ms stagger (`--ease-spring`), and **cross-fade two stacked UTCI `BitmapLayer`s** (baseline opacity→0, intervention 0→target) over `--t-slow` — replacing the jarring hard image swap at `Scene.tsx` ~227–230 (fixes #6/#7). First result auto-plays the full reveal; subsequent evaluations use a shorter transition; reduced-motion → instant.

**Vignette + spotlight** — a non-interactive overlay above the map, below the UI: `radial-gradient(120% 90% at 50% 42%, transparent 38%, rgba(4,8,10,0.55) 100%)`, opacity animated with the flight.

**Citywide pins** — replace the flat `opacity:0.55` smear: numbered, radius∝`tree_count` pins that drop in sequentially with a € ticker; the site list cross-highlights the pin on hover.

**Narrated 30 s wait** (fix #9) — dim the map, centered progress card rotating real pipeline lines ("Placing trees on plantable spots… Running Infrared UTCI… Measuring cooled area…"), each tied to an actual stage; status to `aria-live` (C8).

---

## 6. ACCESSIBILITY ACCEPTANCE CRITERIA (binding; manual items gate release)

Conformance target **WCAG 2.2 AA**, with 2.3.3 (reduced motion) and 44px touch targets treated as MUST given the heat/motion-heavy public-facing nature.

- **A — Contrast over the busy map (MUST).** Never paint live text on the map. Every text cluster sits on `--surface-1` (≥92% opaque); any label floating on the map carries a `--map-pill` scrim (≥0.85) + ≥4px padding. Text ≥**4.5:1**; large text / hero ≥**3:1**; non-text UI (borders, focus ring, slider track/handle, legend swatch outlines) ≥**3:1**. Pre-cleared palette: `--ink-0/1/2/3`; **nothing dimmer than `--ink-3` (#8FA6B0, ~4.6:1) for text.** Toggling the basemap off MUST NOT change any pass/fail (A4). Text-shadow is supplement, never the technique.
- **B — CVD-safe palette + non-colour redundancy (MUST).** UTCI drape uses the §2 monotonic-lightness ramp (passes Coblis deuteran/protan/tritan; adjacent bins stay distinct). ΔUTCI uses the teal↔magenta diverging ramp (never red–green). Legend shows numeric °C breakpoints (1.4.1). Funded sites distinguished by **rank number + € label + ring**, not colour alone. Any colour-encoded value is recoverable as a number via hover/click/inspect.
- **C — Keyboard, focus, ARIA (MUST).** Full Design + Citywide flow operable mouse-unplugged, no trap. DOM order = visual order: skip-link → Mode Switch → primary action → Result Card → Growth Slider → Legend → map. Visible focus ring (`--focus-ring`, ≥2px, ≥3:1) on every control; never `outline:none` without replacement. **The map is not a black hole:** provide a keyboard-navigable list of trees and of the 7 sites (real `<button>`/`<li>` with name, ΔT, spend, rank) as the *primary* accessible path; focusable markers expose role + name + Enter-to-inspect. Landmarks: `<header>`/`<main>`/`<nav>`; Mode Switch = `tablist`; Onboarding + TreeInspect = `role="dialog"` with Esc + focus return; icon buttons have `aria-label`. KPIs are `<dt>/<dd>` with units spelled for AT. Async status + errors → `aria-live="polite"` / `role="alert"`. Skip link first.
- **D — `prefers-reduced-motion` (MUST).** flyTo → `jumpTo` (land already at the focal point — the camera-bug fix must itself respect this); scrolly reveals → instant state; growth scrub → instant; pulsing/shimmer/auto-play disabled. Motion-only meaning (which site) MUST also be in a text heading. No flash >3×/s. Any auto-advance >5 s needs pause/stop. Default flyTo ≤1.2 s, single easing.
- **E — Type sizes + hit targets (MUST).** Meaningful text floor **14px**; body/interactive ≥16px; hero ≥40px; line-height ≥1.4. Every control ≥**24×24** (target **44×44**). Tree click also available via the C4 list (no dependence on a 6px disk). Resizes to 200% and reflows to 320 px wide with no clipping/h-scroll (panels stack). Survives user text-spacing overrides. TreeInspect/tooltips appear on focus too, dismissible with Esc, stay while hovered.

**Manual-only release gates** (axe/Lighthouse cannot see these over a canvas): A2 contrast on rendered app, A4 basemap-off, B1 CVD simulation, C2 focus order through deck.gl, C4 non-canvas data path, D1 reduced-motion.

---

## 7. PRIORITISED IMPLEMENTATION PLAN

**Phase 1 — Legible + pretty + story-driven, fastest (highest leverage; do in this order):**
1. **Camera flyTo authority** (`Scene.tsx`) — fixes the #1 bug; `viewState`=onMove-only, `flyTo`/`jumpTo` authoritative, `cameraMode` flag, reduced-motion `jumpTo`. *Pure refactor, unblocks everything.*
2. **Tokens + visual system** — add `tokens.css`, load Fraunces/Inter/IBM Plex Mono, define the one `.panel` glass + flat `.tile` + vignette. *Turns "dashboard" into "FWA".*
3. **Phase machine + panel collapse** (`App.tsx`, `Scene.tsx`) — `Phase` state, phase-gated mounting; kill always-on `Hud`; build Result Card (hero Cool Score + 3-up + meta), Mode Switch, Action Rail; dock Growth Slider; fold depave-chip. *5 panels → ≤2.*
4. **Heat layer beautify** (`colorscale.ts`, `layers.ts`) — swap to CVD-safe monotonic ramp + alpha-by-intensity + bloom + iso-contours + funded-site rings. *Kills the orange blob.*
5. **Reveal animations** — cross-fade baseline→intervention + tree-grow-in `transitions:{getRadius:800}` + vignette dim-on-fly. *The "presentation is the product" wow.*
6. **Onboarding intro** (`Onboarding.tsx`) — Scenes 0–3, Skip + `localStorage` gate, drives the real layers. Wire payoff numbers to `citywide_plan.json` / live result — **never the 0.00 °C mock.**

**Phase 2 — Polish + scale:** Citywide ranked-pins + leaderboard panel with € ticker (#5); narrated 30 s Evaluate progress (#9); TreeInspect restyle to tokens; Legend gradient key with breakpoints (#10).

**Phase 3 — Accessibility hardening (release gate):** keyboard tree/site list (C4); full ARIA (tablist, dialogs, dt/dd, aria-live); focus order + visible rings; reduced-motion paths everywhere; run the manual gate matrix (A2, A4, B1, C2, C4, D1) + zoom/reflow at 200%/400%/320px.

---

## EXECUTIVE SUMMARY (12 lines)

1. Direction: **Guided-Sunroof** — a Sunroof "place→measured-result" tool opened by a skippable Bloomberg-style heat reveal; story is the on-ramp, the app is the destination.
2. Emulate: Project Sunroof (interaction), Tree Equity Score (one legible score), Bloomberg coolest-spots (cinematic heat storytelling).
3. The intro drives the *real* deck.gl layers (no fake canvas), is one-time `localStorage`-gated, one-click-skippable, and grab-the-map-to-interrupt.
4. Collapse 5 simultaneous glass panels → **≤2**: top-center Mode Switch + right Action Rail persistent; one contextual card (Result / Citywide) per phase.
5. Every screen leads with **ONE hero number** (Cool Score 0–100 in result; people-served + €1M in citywide); everything else demotes to a supporting strip.
6. Visual system: near-opaque dark glass (`--surface-1` ≥92%), Fraunces display + Inter UI, mint `#3BE8C0` accent reserved for "the active thing", cinematic vignette spotlight.
7. Fix the camera bug: `flyTo`/`jumpTo` is authoritative, `viewState`=onMove-only, `cameraMode` flag, reduced-motion lands instantly at the focal point.
8. Kill the orange blob: CVD-safe monotonic-lightness UTCI ramp + alpha-by-intensity + bloom + iso-contours + mint rings on the 7 funded sites.
9. Signature reveal: cross-fade baseline→intervention + tree-grow-in (`transitions:{getRadius:800}`) + vignette dim on the ≤1.2 s flyTo.
10. Credibility rule: badge `MEASURED` only when real; the published single-site bundle is the **mock** — wire payoff to `citywide_plan.json` (24,356 m², €41/m², 22,590 people, measured) or the live result.
11. Accessibility is a release gate: text never on the map, ≥4.5:1, keyboard tree/site list as the primary path, full reduced-motion, 14px floor, 44px targets.
12. **Phase 1 task list:** (1) camera flyTo authority; (2) tokens + visual system; (3) phase machine + panel collapse / Result Card / Mode Switch / Action Rail; (4) heat-layer beautify (CVD ramp + alpha + bloom + rings); (5) reveal animations; (6) Onboarding intro wired to real measured numbers.
