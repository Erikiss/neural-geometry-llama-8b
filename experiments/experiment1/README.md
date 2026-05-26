# Experiment 1: Days-of-Week Cyclic Geometry

Replicating the cyclic ring structure of day-of-week representations from:
> *Manifold Steering Reveals the Shared Geometry of Neural Network Representation and Behavior* (Goodfire, 2025)

## What This Shows

LLMs internally represent cyclic concepts (days of the week) as a geometric ring in activation space. This experiment extracts those hidden states and projects them to 3D using the paper's multi-step PCA pipeline, revealing the circle.

## Configuration

| Parameter | Value | Notes |
|-----------|-------|-------|
| **Model** | `meta-llama/Meta-Llama-3.1-8B` | Via nnsight NDIF remote API |
| **Layer** | 28 (0-indexed) | Out of 32 total; paper uses layer 28 as the richest semantic layer |
| **Token position** | Last token (`[:, -1, :]`) | Encodes full causal context of the question |
| **Activation type** | Residual stream hidden states | Post-LayerNorm output of the decoder block, 4096-dim |
| **Prompt templates** | 2 templates (see below) | Doubled to enable full 64D intermediate PCA |
| **Prompts total** | 84 | 2 templates × 7 starting days × 6 k-values |
| **Grouping strategy** | By *correct answer day* | Not by starting day — prompts with same answer cluster together |
| **Centroids** | 7 (one per day) | Mean of 12 activations each |

## Prompt Templates

```
Template 1: "What day is {k} days after {day}?"
Template 2: "If today is {day}, what day will it be in {k} days?"
```

where `day ∈ {Monday..Sunday}` and `k ∈ {1, 2, 3, 4, 5, 6}`.

Each prompt's label is the **correct answer day** (i.e., `(day_idx + k) % 7`), not the starting day.

## Multi-Step PCA Pipeline

The paper uses a two-stage approach — NOT naive PCA to 3D:

```
Raw activations (84 × 4096)
        │
        ▼ PCA Step 1
Intermediate space (84 × 64)
        │
        ▼ Average by answer-day label
Day centroids (7 × 64)
        │
        ▼ Periodic cubic spline (scipy CubicSpline, bc_type='periodic')
Smooth manifold curve (300 × 64) sampled at t ∈ [0, 7]
        │
        ▼ PCA Step 2 (fit on spline samples)
3D visualization (300 × 3)
```

**Why two PCA stages?**
- PCA Step 1 (→64D): Finds a rich subspace from all 84 individual activations, not just the 7 centroids. This gives a well-conditioned intermediate space.
- Spline fitting: Enforces the cyclic structure explicitly. `bc_type='periodic'` ensures the curve closes smoothly from Sunday back to Monday.
- PCA Step 2 (→3D): Fit *on the spline samples*, not on raw activations. This means the principal components capture the manifold's own geometric directions. The 3D plot directly shows the manifold shape.

## Output Files

| File | Description |
|------|-------------|
| `days_geometry.ipynb` | Main notebook — run top to bottom |
| `all_acts.npy` | Cached activation matrix `(84, 4096)` — saved after API extraction |
| `labels.npy` | Answer-day labels `(84,)` — saved alongside activations |

## What to Expect

- The 3D plot should show 7 labeled points in a **closed ring**
- Monday and Sunday should appear adjacent (cyclic, not linear)
- PCA Step 2 explained variance: top 2 components should dominate if the geometry is cleanly circular
- The continuous spline curve should connect all 7 centroids smoothly and close back on Monday

## Varying Configurations (Future Experiments)

| Variable | This Experiment | Try Next |
|----------|----------------|----------|
| Layer | 28 | 16, 20, 24, 31 — track when ring emerges |
| Templates | 2 | 3–4 for denser centroid averaging |
| Intermediate PCA dims | 64 | 32, 128 — check stability |
| Spline samples | 300 | 100, 500 — visual resolution |
| Model | Llama 3.1 8B | Llama 3.1 70B, Gemma 2 |
