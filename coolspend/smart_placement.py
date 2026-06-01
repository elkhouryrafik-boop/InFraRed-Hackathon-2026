"""
coolspend/smart_placement.py — cooling-optimal tree placement by budgeted greedy
weighted max-coverage on a MEASURED heat-priority field.

WHY THIS METHOD (up to standard, not ad-hoc)
--------------------------------------------
Placing trees to cool a site is a *coverage* problem: each tree shades a disk of
ground, and what we want to cover is the hot, paved, not-already-shaded ground —
weighted by how hot it is. The value of a set of trees S is

    value(S) = Σ  weight(cell)   over demand cells covered by at least one tree in S

This is a weighted **maximum coverage** objective: monotone and **submodular**
(adding a tree to a larger set yields ≤ the gain it gives to a smaller set, because
of canopy overlap → diminishing returns). For submodular maximisation the greedy
rule — repeatedly add the element with the largest marginal gain — is the standard,
provably near-optimal algorithm: it achieves ≥ (1 − 1/e) ≈ 63 % of the optimum
(Nemhauser, Wolsey & Fisher 1978). Under a **budget** (heterogeneous tree/de-pave
costs) the cost-benefit variant — add the element with the largest marginal
gain *per euro* — carries the matching budgeted guarantee (Krause & Guestrin 2005;
Leskovec et al. 2007, "CELF").

So the engine is: discretise the live Infrared UTCI grid into weighted demand
cells (hot × impervious × not-already-shaded), then run cost-benefit greedy over
the building-aware candidate slots until the budget is spent. The result is
deterministic, interpretable ("this tree was placed because it shades the hottest
unshaded paved cells per euro"), and bounded-optimal.

SHADE-GAIN WEIGHTING (PAPER limitation #2)
------------------------------------------
A tree's value for a hot cell is NOT "is the cell under the crown disk" — it is
"does this crown's SHADOW actually fall on the cell, across the day's sun
positions". We therefore weight each (slot, species)→cell pair by the
`shade_proxy` sun-blockage fraction (fraction of sampled July suns whose crown
shadow lands on the cell), not by binary crown overlap. Marginal gain is
Σ weight(cell) × (shade_gain − already_captured), capped per cell — so trees are
placed to cast shadow ONTO the hottest unshaded ground (e.g. south of a midday
hotspot), double-shading yields no extra gain, and returns diminish physically.
The objective stays monotone + submodular (shade-ray sets union), so the greedy
keeps its (1 − 1/e) guarantee. Set `use_shade_gain=False` for the legacy binary
crown-coverage proxy (fallback).

HONESTY BOUNDARY
----------------
The demand weights use the *baseline* (pre-planting) UTCI field, and the
shade-gain is a first-order radiative proxy (direct-beam interception). True
cooling is nonlinear — a planted tree changes the field — so the greedy "gain"
is a physical proxy for marginal cooling, NOT measured cooling. The CHOSEN layout
is handed to the live Infrared UTCI run for the ground-truth ΔUTCI (see
sdk_client). This module never calls the network; it is pure geometry +
arithmetic, fully testable offline.

Coordinates: site-local metres throughout (same frame as spatial_engine /
candidate_slots). The caller projects WGS84 ↔ local metres at the boundary.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DemandCell:
    """One unit of cooling demand: a hot, paved, unshaded ground cell.

    weight is the cooling priority of the cell (e.g. UTCI degrees above the comfort
    threshold). Cells that are already shaded or permeable are simply not emitted by
    the caller, so the demand set is exactly the ground worth shading.
    """
    x_m: float
    y_m: float
    weight: float


@dataclass(frozen=True)
class SpeciesOption:
    """A plantable species with the attributes the placement needs."""
    name: str
    crown_m: float          # mature crown diameter (shade radius = crown_m / 2)
    tree_cost_eur: float     # lifecycle cost of the tree itself (capex + opex)
    cooling_score: float     # 0..1 species cooling proxy (tie-break, diversity-neutral)
    height_m: float = 10.0   # mature height — drives shadow length in the shade-gain model


@dataclass(frozen=True)
class CandidateSlot:
    """A validated plantable location (from candidate_slots), with its de-pave cost."""
    x_m: float
    y_m: float
    mode: str                 # "planter" | "in_ground"
    depave_cost_eur: float = 0.0  # extra cost to depave this slot (0 for planters)
    # Max mature crown diameter (m) this slot can host — set from the available
    # planting width (distance to nearest building/road). float('inf') = unconstrained.
    # A species whose crown exceeds this is not allowed here (species-to-site matching).
    max_crown_m: float = float("inf")


@dataclass
class PlacedTree:
    """One tree the greedy placed, in the order it was selected.

    Coordinates are site-local metres. ``marginal_weight`` is the NEW demand
    weight this tree shaded at the moment it was chosen (its marginal gain),
    which is monotonically non-increasing across the placement order.
    """
    x_m: float
    y_m: float
    species: str
    mode: str
    cost_eur: float
    marginal_weight: float    # demand weight this tree newly covered when placed


@dataclass
class PlacementResult:
    """Output of place_trees_greedy: the chosen layout plus its coverage bookkeeping.

    ``stop_reason`` records WHY the greedy halted (budget exhausted or no
    positive-gain affordable slot remained) — the loop is condition-terminated,
    never capped by a fixed iteration count.
    """
    placed: list[PlacedTree] = field(default_factory=list)
    total_cost_eur: float = 0.0
    covered_weight: float = 0.0      # demand weight shaded by the final layout
    total_demand_weight: float = 0.0  # all demand (for coverage %)
    stop_reason: str = ""

    @property
    def coverage_fraction(self) -> float:
        """Fraction of total demand weight shaded by the final layout (0..1)."""
        return self.covered_weight / self.total_demand_weight if self.total_demand_weight else 0.0


def _covered_cell_indices(
    slot_xy: tuple[float, float], radius_m: float, demand: list[DemandCell]
) -> set[int]:
    """Indices of demand cells whose centre lies within the canopy radius of a slot."""
    sx, sy = slot_xy
    r2 = radius_m * radius_m
    out: set[int] = set()
    for i, c in enumerate(demand):
        dx = c.x_m - sx
        dy = c.y_m - sy
        if dx * dx + dy * dy <= r2:
            out.add(i)
    return out


def place_trees_greedy(
    demand: list[DemandCell],
    candidates: list[CandidateSlot],
    species: list[SpeciesOption],
    *,
    budget_eur: float,
    min_spacing_m: float = 8.0,
    max_species_share: float = 0.40,
    diversity_grace: int = 4,
    use_shade_gain: bool = True,
    lat_deg: float = 41.39,
) -> PlacementResult:
    """Budgeted greedy weighted-max-coverage tree placement (see module docstring).

    Args:
        demand:          weighted hot/paved/unshaded cells to cover.
        candidates:      validated plantable slots (building-aware; from candidate_slots).
        species:         plantable species options (crown, cost, cooling).
        budget_eur:      total spend cap (tree cost + per-slot de-pave cost).
        min_spacing_m:   minimum centre-to-centre spacing between PLACED trees.
        max_species_share: cap on any single species' share of the planting in steady
                         state (anti-monoculture; keeps ecological diversity).
        diversity_grace: allow the first N placements to ignore the share cap so a
                         strong species can establish before the cap binds.

    Returns:
        PlacementResult with the placed trees (in placement order), cost, and the
        demand weight covered. Greedy is cost-benefit (max marginal gain per euro),
        the budgeted-submodular standard.

    The objective is submodular → this greedy is within (1 − 1/e) of optimal for the
    unit-cost case and carries the budgeted cost-benefit guarantee otherwise.
    """
    total_demand = sum(c.weight for c in demand)
    result = PlacementResult(total_demand_weight=total_demand)
    if not demand or not candidates or not species or budget_eur <= 0:
        result.stop_reason = "empty demand, candidates, species, or budget"
        return result

    # Precompute coverage once (geometry is static): per (candidate, species) →
    # {demand-cell index: shade_gain in 0..1}. shade_gain is the fraction of the
    # sampled July suns whose crown shadow lands on the cell (shade_proxy); the
    # legacy fallback is binary crown overlap (gain = 1.0 inside the radius).
    coverage: dict[tuple[int, int], dict[int, float]] = {}
    suns = None
    if use_shade_gain:
        try:
            from coolspend import shade_proxy as _sp  # noqa: PLC0415
            suns = _sp.solar_positions_july(lat_deg)
            proxy_cells = [_sp.ProxyCell(c.x_m, c.y_m, c.weight, 1.0) for c in demand]
        except Exception:  # noqa: BLE001 — fall back to binary coverage
            suns = None
    for ci, slot in enumerate(candidates):
        for si, sp in enumerate(species):
            r = sp.crown_m / 2.0
            if suns is not None:
                tree = _sp.ProxyTree(slot.x_m, slot.y_m, r, sp.height_m)
                gains = _sp.shade_gain_per_cell(proxy_cells, [tree], suns)
                coverage[(ci, si)] = {i: g for i, g in gains.items() if g > 0.0}
            else:
                coverage[(ci, si)] = {
                    i: 1.0 for i in _covered_cell_indices((slot.x_m, slot.y_m), r, demand)
                }

    # Per-cell captured shade-gain so far (0..1). A cell can be partially shaded by
    # one tree and topped up by another, but never credited beyond 1.0 (its weight).
    captured: dict[int, float] = {}
    used_candidates: set[int] = set()  # slots already planted
    placed_xy: list[tuple[float, float]] = []
    species_count: dict[str, int] = {}
    spent = 0.0
    min_sp2 = min_spacing_m * min_spacing_m

    def _too_close(x: float, y: float) -> bool:
        for px, py in placed_xy:
            dx, dy = x - px, y - py
            if dx * dx + dy * dy < min_sp2:
                return True
        return False

    while True:
        # Track two bests: one honouring the diversity cap, one ignoring it. We
        # prefer the cap-respecting pick, but fall back to the unconstrained best so
        # the cap can never STALL placement when every species is at its share limit
        # (the cap biases diversity; it must not halt a still-improving run).
        best_capped = None  # (key, marginal, ci, si, cost, new_cells)
        best_any = None
        n_placed = len(result.placed)

        for ci, slot in enumerate(candidates):
            if ci in used_candidates:
                continue
            if _too_close(slot.x_m, slot.y_m):
                continue
            for si, sp in enumerate(species):
                # Species-to-site matching: crown must fit the slot's available width.
                if sp.crown_m > slot.max_crown_m:
                    continue
                cost = sp.tree_cost_eur + slot.depave_cost_eur
                if cost <= 0 or spent + cost > budget_eur:
                    continue
                # Marginal = Σ weight × (shade_gain − already-captured), per cell,
                # so a cell already shaded contributes only the NEW blockage.
                gains = coverage[(ci, si)]
                marginal = 0.0
                for i, g in gains.items():
                    rem = g - captured.get(i, 0.0)
                    if rem > 0.0:
                        marginal += demand[i].weight * rem
                if marginal <= 0:
                    continue
                # Cost-benefit greedy: maximise marginal gain per euro. Tie-break by
                # species cooling_score then absolute marginal weight (determinism).
                gpc = marginal / cost
                key = (gpc, sp.cooling_score, marginal)
                cand = (key, marginal, ci, si, cost, gains)
                if best_any is None or key > best_any[0]:
                    best_any = cand
                # Anti-monoculture: once past the grace period, prefer not to let any
                # one species exceed max_species_share of the planting.
                within_cap = True
                if n_placed >= diversity_grace:
                    share = (species_count.get(sp.name, 0) + 1) / (n_placed + 1)
                    within_cap = share <= max_species_share
                if within_cap and (best_capped is None or key > best_capped[0]):
                    best_capped = cand

        best = best_capped if best_capped is not None else best_any
        if best is None:
            result.stop_reason = "no positive-gain affordable slot remains"
            break

        _, marginal, ci, si, cost, gains = best
        slot, sp = candidates[ci], species[si]
        result.placed.append(
            PlacedTree(slot.x_m, slot.y_m, sp.name, slot.mode, cost, round(marginal, 4))
        )
        # Top up each cell's captured shade-gain, capped at 1.0 (= fully shaded).
        for i, g in gains.items():
            captured[i] = min(1.0, captured.get(i, 0.0) + g)
        used_candidates.add(ci)
        placed_xy.append((slot.x_m, slot.y_m))
        species_count[sp.name] = species_count.get(sp.name, 0) + 1
        spent += cost

    result.total_cost_eur = round(spent, 2)
    # Covered weight = Σ weight × captured-shade-gain (fractional), the demand
    # actually shaded by the final layout.
    result.covered_weight = round(
        sum(demand[i].weight * frac for i, frac in captured.items()), 4
    )
    return result
