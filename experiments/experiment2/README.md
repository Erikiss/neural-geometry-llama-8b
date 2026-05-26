# Experiment 2: Color, Temperature, Age Geometry

Extends experiment1 to three new concepts, comparing **cyclic** vs **linear** geometry
in Llama 3.1 8B's activation space (layer 28).

## Concept Configurations

| Parameter | Color | Temperature | Age |
|-----------|-------|-------------|-----|
| Values | Red, Orange, Yellow, Green, Blue, Indigo, Violet (7) | 10–100°C step 10 (10) | 10–80yr step 10 (8) |
| K-range | 1–6 | 1–5 | 1–5 |
| Prompts | 84 (12 per color) | 100 (10 per temp) | 80 (10 per age) |
| Spline type | **Periodic cubic** | Natural cubic | Natural cubic |
| Expected geometry | Ring (like days) | Arc / line | Arc / line |
| Grouping | By answer color | By answer temp | By answer age |

## Prompt Templates

### Color
```
"In the rainbow (Red, Orange, Yellow, Green, Blue, Indigo, Violet), what color is {k} positions after {color}?"
"The rainbow goes Red, Orange, Yellow, Green, Blue, Indigo, Violet. Starting at {color} and moving {k} steps forward, what color do you reach?"
```

### Temperature
```
"What temperature is {k} degrees Celsius warmer than {T-k}°C?"
"If the temperature is {T-k} degrees Celsius and it rises by {k} degrees, what is the new temperature in Celsius?"
```

### Age
```
"How old is someone who is {k} years older than a {A-k}-year-old?"
"A person is {A-k} years old. In {k} years, how old will they be?"
```

## Pipeline

Same multi-step PCA as experiment1:

```
Raw activations (N × 4096)
    │
    ▼ PCA Step 1 → min(64, N) dimensions
Intermediate space
    │
    ▼ Average by answer-concept label
Centroids (n_concepts × 64)
    │
    ▼ Periodic spline (color) or Natural spline (temp, age)
Smooth manifold curve (300 × 64)
    │
    ▼ PCA Step 2 (fit on spline samples)
3D visualization
```

**Spline type matters:**
- **Periodic** (`bc_type='periodic'`): wraps end back to start — produces a closed ring.
  Used for color (Violet → Red on the hue wheel).
- **Natural** (default `not-a-knot`): open curve — produces an arc or line.
  Used for temperature and age which don't wrap around.

## Output Files

| File | Description |
|------|-------------|
| `{concept}_geometry_3d.html` | Interactive 3D plot (spline-biased projection) |
| `{concept}_geometry_2d_unbiased.html` | Centroid-only 2D plot (no spline bias — honest view) |
| `{concept}_acts.npy` | Cached activations `(N_prompts, 4096)` |
| `{concept}_labels.npy` | Answer labels `(N_prompts,)` |

## What to Expect

- **Color 3D:** Ring structure, similar to days-of-week
- **Temperature 3D:** Smooth arc from cold (10°C) to hot (100°C) — not closed
- **Age 3D:** Smooth arc from young (10yr) to old (80yr) — not closed
- **Validation:** PC1/PC2 ratio near 1 for color (ring), PC1 >> PC2 for temp/age (line)

## Varying Configurations (Future Experiments)

| Variable | This Experiment | Try Next |
|----------|----------------|----------|
| Layer | 28 | Sweep 16–31 |
| Color system | ROYGBIV linear | HSV full 360° |
| Temp range | 10–100°C, step 10 | Continuous with named anchors |
| Age increments | Decade-level | Year-level (more waypoints) |
| Model | Llama 3.1 8B | Llama 3.1 70B |
