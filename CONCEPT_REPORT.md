# CONCEPT REPORT: Tree Budget Optimizer
**Project:** Infrared City Hackathon 2026
**Topic:** The Tree Budget — Maximizing "Carbon of Stress Relief"
**Date:** May 20, 2026

## 1. Executive Summary
The Tree Budget Optimizer is a spatial decision-support tool that utilizes the Infrared City SDK and evolutionary algorithms (NSGA-II) to identify optimal tree placement in urban environments. By balancing high-fidelity thermal simulation against explicit ecological and financial constraints, the system maximizes the cooling ROI of urban forestry. This approach replaces manual "intuition-based" planting with a data-driven strategy that delivers the most significant temperature relief per Euro invested.

## 2. Problem Statement
Urban heat islands significantly impact pedestrian health and energy consumption. While tree planting is a primary mitigation strategy, its effectiveness is highly sensitive to local microclimates and built-environment geometry. Traditional planning often lacks the tools to quantify the precise thermal benefit of a specific placement, leading to sub-optimal resource allocation in municipal "Tree Budgets."

## 3. Technical Architecture
The proposed system operates on a three-tier architecture:

### 3.1 Data & Spatial Engine
The system ingests local OpenStreetMap (OSM) data to create a high-fidelity collision layer. Buildings, street centerlines, and existing green infrastructure are treated as hard spatial constraints to ensure all proposed planting configurations are viable for real-world implementation.

### 3.2 Fitness & Optimization
We utilize the **NSGA-II (Non-dominated Sorting Genetic Algorithm II)** to solve a multi-objective optimization problem:
1.  **Thermal Relief:** Measured via the Infrared City SDK's UTCI analysis. The goal is to maximize the delta between the baseline plaza temperature and the tree-augmented intervention.
2.  **Ecological Coherence:** A rule-based scoring system derived from permaculture principles. It rewards species diversity and optimal spacing to prevent overcrowding and promote resilient urban guilds.
3.  **Financial Efficiency:** Calculating the Total Cost of Ownership (TCO) per degree of cooling relief.

### 3.3 Rule-Based Permaculture Engine
Unlike standard optimizers that may cluster trees excessively, our engine enforces explicit ecological rules:
*   **Minimum Spacing:** Prevents root competition and ensures canopy health.
*   **Diversity Index:** Ensures a resilient mix of species to mitigate disease risks (e.g., the 30-20-10 rule).
*   **Energy Exchange:** Considers the surrounding built environment's influence on tree health and vice versa.

## 4. Financial Optimization: The "Tree Budget"
Each tree is modeled as an investment with both CapEx (planting) and OpEx (maintenance) requirements. The "Carbon of Stress Relief" is the primary KPI, defined as the annual reduction in high-heat UTCI hours per unit of cost. This allows municipal planners to defend their budgets by showing the direct health and comfort returns on urban greening.

## 5. Conclusion
By integrating professional-grade CFD simulation (Infrared SDK) with rigorous evolutionary optimization, the Tree Budget Optimizer provides a defensible, deterministic path for urban cooling. This prototype demonstrates that urban design "coherence" can be quantified and optimized, bridging the gap between ecological theory and municipal execution.
