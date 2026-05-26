"""
Runner script for days_geometry.ipynb — executes all notebook logic.
Run with: python3.11 run_experiment.py
"""
import os
import numpy as np
import time
import colorsys
from pathlib import Path
from tqdm import tqdm
from sklearn.decomposition import PCA
from scipy.interpolate import CubicSpline
import plotly.graph_objects as go
from huggingface_hub import login as hf_login
import nnsight
from nnsight import LanguageModel

# ── Setup ──────────────────────────────────────────────────────────────────────
HF_TOKEN  = os.environ.get("HF_TOKEN", "")
API_KEY   = os.environ.get("NDIF_API_KEY", "")
MODEL_ID  = "meta-llama/Meta-Llama-3.1-8B"
LAYER_IDX = 28

hf_login(token=HF_TOKEN, add_to_git_credential=False)
nnsight.CONFIG.set_default_api_key(API_KEY)
model = LanguageModel(MODEL_ID)
print(f"Model ready: {MODEL_ID}\n")

# ── Prompt Generation ──────────────────────────────────────────────────────────
DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

templates = [
    lambda day, k: f"What day is {k} days after {day}?",
    lambda day, k: f"If today is {day}, what day will it be in {k} days?",
]

prompts, labels = [], []
for day_idx, day in enumerate(DAYS):
    for k in range(1, 7):
        for tmpl in templates:
            prompts.append(tmpl(day, k))
            labels.append(DAYS[(day_idx + k) % 7])
labels = np.array(labels)

print(f"Total prompts: {len(prompts)}")
print(f"Prompts per answer-day: {[(d, int((labels == d).sum())) for d in DAYS]}")
print(f"\nFirst 4 examples:")
for i in range(4):
    print(f"  '{prompts[i]}' → {labels[i]}")
print()

# ── Activation Extraction ──────────────────────────────────────────────────────
CACHE_ACTS = Path("all_acts.npy")
CACHE_LABELS = Path("labels.npy")

if CACHE_ACTS.exists():
    print("Cache found — loading from disk (skipping API calls).")
    all_acts = np.load(CACHE_ACTS)
    labels = np.load(CACHE_LABELS, allow_pickle=True)
    print(f"Loaded: all_acts={all_acts.shape}, labels={labels.shape}\n")
else:
    print(f"Extracting activations for {len(prompts)} prompts from layer {LAYER_IDX}...")
    all_acts = []

    for i, prompt in enumerate(tqdm(prompts, desc="Extracting hidden states")):
        for attempt in range(3):
            try:
                with model.trace(prompt, remote=True):
                    hidden = model.model.layers[LAYER_IDX].output[:, -1, :].save()
                act = hidden.squeeze(0).cpu().float().numpy()
                all_acts.append(act)
                break
            except Exception as e:
                print(f"\n  Prompt {i} attempt {attempt+1} failed: {e}")
                if attempt < 2:
                    time.sleep(5)
                else:
                    raise
        time.sleep(0.25)

    all_acts = np.stack(all_acts)
    np.save(CACHE_ACTS, all_acts)
    np.save(CACHE_LABELS, labels)
    print(f"\nSaved to disk. Shape: {all_acts.shape}\n")

# ── PCA Step 1: 64D Intermediate Space ────────────────────────────────────────
N_INTER = min(64, len(prompts))
pca1 = PCA(n_components=N_INTER)
acts_inter = pca1.fit_transform(all_acts)

cumvar = np.cumsum(pca1.explained_variance_ratio_)
print(f"PCA Step 1 → {N_INTER}D intermediate space")
print(f"  Variance in top 64 PCs: {cumvar[-1]:.3f}")
print(f"  Variance in top  7 PCs: {cumvar[6]:.3f}")
print(f"  Variance in top  3 PCs: {cumvar[2]:.3f}\n")

# ── Compute Per-Day Centroids ──────────────────────────────────────────────────
centroids = np.array([
    acts_inter[labels == day].mean(axis=0)
    for day in DAYS
])
print(f"Centroids: {centroids.shape}")
for day in DAYS:
    n = int((labels == day).sum())
    print(f"  {day}: averaged from {n} prompts")
print()

# ── Periodic Cubic Spline in 64D ──────────────────────────────────────────────
centroids_periodic = np.vstack([centroids, centroids[0:1]])
t_knots = np.arange(8, dtype=float)

spline = CubicSpline(t_knots, centroids_periodic, bc_type='periodic')
t_dense = np.linspace(0, 7, 300)
curve_inter = spline(t_dense)

close_dist = np.linalg.norm(curve_inter[0] - curve_inter[-1])
print(f"Spline curve: {curve_inter.shape}")
print(f"Curve closure distance (should be ~0): {close_dist:.6f}\n")

# ── PCA Step 2: 3D from Manifold ──────────────────────────────────────────────
pca2 = PCA(n_components=3)
curve_3d = pca2.fit_transform(curve_inter)
centroids_3d = pca2.transform(centroids)

var = pca2.explained_variance_ratio_
print(f"PCA Step 2 → 3D (fit on spline samples)")
print(f"  PC1={var[0]:.3f}  PC2={var[1]:.3f}  PC3={var[2]:.3f}")
print(f"  Total variance in 3D: {var.sum():.3f}")
if var[:2].sum() > 0.8:
    print("  → PC1+PC2 > 80%: strong planar ring structure!")
elif var[:2].sum() > 0.6:
    print("  → PC1+PC2 > 60%: moderate ring structure")
else:
    print("  → Lower PC1+PC2: check 3D plot for geometry")
print()

# ── Sanity Check: Pairwise Distances ──────────────────────────────────────────
from scipy.spatial.distance import cdist
dist_matrix = cdist(centroids, centroids)

print("Adjacent vs opposite-day centroid distances (64D):")
for i in range(7):
    adj = dist_matrix[i, (i + 1) % 7]
    opp = dist_matrix[i, (i + 3) % 7]
    flag = "✓" if adj < opp else "✗"
    print(f"  {flag} {DAYS[i]:9s}→{DAYS[(i+1)%7]:9s}: {adj:.3f}  |  "
          f"{DAYS[i]:9s}→{DAYS[(i+3)%7]:9s}: {opp:.3f}")
print()

# ── 3D Visualization ───────────────────────────────────────────────────────────
day_colors = [
    '#{:02x}{:02x}{:02x}'.format(*[int(c * 255) for c in colorsys.hsv_to_rgb(i / 7, 0.85, 0.88)])
    for i in range(7)
]
colorscale = [[i / 6, day_colors[i]] for i in range(7)]

fig = go.Figure()

fig.add_trace(go.Scatter3d(
    x=curve_3d[:, 0], y=curve_3d[:, 1], z=curve_3d[:, 2],
    mode='lines',
    name='Manifold Curve',
    line=dict(color=t_dense, colorscale=colorscale, width=6, showscale=False),
    hovertemplate='t=%.2f<extra>Spline</extra>',
))

fig.add_trace(go.Scatter3d(
    x=centroids_3d[:, 0], y=centroids_3d[:, 1], z=centroids_3d[:, 2],
    mode='markers+text',
    name='Day Centroids',
    text=DAYS,
    textposition='top center',
    textfont=dict(size=13, color='black', family='Arial Black'),
    marker=dict(size=10, color=day_colors, symbol='circle',
                line=dict(color='black', width=1.5)),
    hovertemplate='%{text}<br>PC1=%{x:.3f} PC2=%{y:.3f} PC3=%{z:.3f}<extra></extra>',
))

fig.update_layout(
    title=dict(
        text=(
            f'Days-of-Week Cyclic Ring — Llama 3.1 8B, Layer {LAYER_IDX}<br>'
            f'<sup>Multi-step PCA: 4096D → {N_INTER}D → Periodic Spline → 3D | '
            f'{len(prompts)} prompts, {len(DAYS)} centroids</sup>'
        ),
        x=0.5, font=dict(size=14),
    ),
    scene=dict(
        xaxis_title=f'PC1 ({var[0]*100:.1f}%)',
        yaxis_title=f'PC2 ({var[1]*100:.1f}%)',
        zaxis_title=f'PC3 ({var[2]*100:.1f}%)',
        aspectmode='cube',
        camera=dict(eye=dict(x=1.5, y=1.5, z=0.8)),
    ),
    legend=dict(x=0.02, y=0.98),
    width=900, height=720,
    margin=dict(t=100, b=20, l=20, r=20),
)

out_html = Path("days_geometry_3d.html")
fig.write_html(str(out_html))
print(f"Saved interactive plot → {out_html.resolve()}")
print("\nOpen days_geometry_3d.html in your browser to view the 3D ring.")
