# CONCEPT REPORT: Tree Budget Optimizer
**Project:** Infrared City Hackathon 2026
**Topic:** The Tree Budget — Maximizing "Carbon of Stress Relief"
**Date:** May 20, 2026

## 1. Executive Summary
The Tree Budget Optimizer is a spatial decision-support tool that uses the Infrared City SDK (a fast urban microclimate API) and evolutionary algorithms (NSGA-II) to identify optimal tree placement in urban environments. By balancing UTCI thermal-comfort analysis against explicit ecological and financial constraints, the system maximizes the cooling ROI of urban forestry. This approach replaces manual "intuition-based" planting with a data-driven strategy that delivers the most significant temperature relief per Euro invested. An analytical surrogate optimizes placement; final picks are re-simulated with Infrared UTCI to confirm rankings.

## 2. Problem Statement
Urban heat islands significantly impact pedestrian health and energy consumption. While tree planting is a primary mitigation strategy, its effectiveness is highly sensitive to local microclimates and built-environment geometry. Traditional planning often lacks the tools to quantify the precise thermal benefit of a specific placement, leading to sub-optimal resource allocation in municipal "Tree Budgets."

## 3. Technical Architecture
The proposed system operates on a three-tier architecture:

### 3.1 Data & Spatial Engine
The system ingests local OpenStreetMap (OSM) data to create a high-fidelity collision layer. Buildings, street centerlines, and existing green infrastructure are treated as hard spatial constraints to ensure all proposed planting configurations are viable for real-world implementation.

### 3.2 Fitness & Optimization
We utilize the **NSGA-II (Non-dominated Sorting Genetic Algorithm II)** to solve a multi-objective optimization problem:
1.  **Thermal Relief:** Measured via the Infrared City SDK's UTCI analysis. The goal is to maximize the delta between the baseline plaza temperature and the tree-augmented intervention.
2.  **Ecological Coherence:** A rule-based scoring system that rewards species diversity and optimal spacing to prevent overcrowding and promote resilient urban plantings.
3.  **Financial Efficiency:** Calculating the Total Cost of Ownership (TCO) per degree of UTCI cooling relief.

### 3.3 Rule-Based Ecological Scoring
Unlike standard optimizers that may cluster trees excessively, our engine enforces explicit ecological rules:
*   **Minimum Spacing:** Prevents root competition and ensures canopy health.
*   **Diversity Index:** Ensures a resilient mix of species to mitigate disease risks (e.g., the 30-20-10 rule).
*   **Spatial Distribution:** Considers the surrounding built environment's influence on placement viability and canopy reach.

## 4. Financial Optimization: The "Tree Budget"
Each tree is modeled as an investment with both CapEx (planting) and OpEx (maintenance) requirements. The "Carbon of Stress Relief" is the primary KPI, defined as the annual reduction in high-heat UTCI hours per unit of cost. This allows municipal planners to defend their budgets by showing the direct health and comfort returns on urban greening.

The headline KPI is reported as an interval [lo, hi] using the surrogate uncertainty band — never as a bare point estimate. The surrogate ceiling (ΔTmrt ≈ 12°C, mapped to ~3–5°C UTCI) is anchored to Schrodi et al. 2023 (arXiv:2310.05691, venue PENDING) and Rahman et al. 2022 (DOI PENDING) as pedestrian-height Tmrt magnitude references; Garcia-Nevado 2020 is a shade-structure/surface-temp analogue only. The 12°C cap is still an unsourced linear cap — REQUIRES_VERIFICATION. See MOCKS.md for the full honesty ledger.

## 5. Out-of-Scope / Not Modeled

This tool provides **geometric feasibility, not engineering siting sign-off.** The following factors are explicitly not modeled and must be addressed in a full engineering assessment before any planting decision is executed:

- **Subsurface utilities** — underground pipes, cables, and conduits are not represented
- **Soil volume** — rooting volume constraints and subgrade conditions are not assessed
- **Irrigation / water demand** — tree water requirements and irrigation infrastructure are not modeled
- **Sightlines** — visual obstruction and traffic sight-distance impacts are not evaluated
- **Solar access to buildings** — winter shading of building facades or photovoltaic panels is not considered
- **Root-vs-pavement conflict** — long-term root uplift and pavement damage potential is not assessed

Municipal engineering, arboriculture, and infrastructure teams must review all proposed placements against these factors before implementation.

## 6. Conclusion
By integrating the Infrared City SDK's UTCI API with rigorous evolutionary optimization, the Tree Budget Optimizer provides a defensible, deterministic path for urban cooling. This prototype demonstrates that urban design "coherence" can be quantified and optimized, bridging the gap between ecological theory and municipal execution. Understatement is the moat: the tool surfaces the best analytical candidates and confirms the top picks with real Infrared UTCI re-simulation, so every output carries a clear data provenance.
