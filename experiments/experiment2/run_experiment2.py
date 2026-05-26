"""
Experiment 2: Color (cyclic), Temperature (linear), Age (linear)
Run with: python3.12 run_experiment2.py
"""
import os
import numpy as np
import time
import colorsys
from pathlib import Path
from tqdm import tqdm
from sklearn.decomposition import PCA
from scipy.interpolate import CubicSpline
from scipy.spatial.distance import cdist
import plotly.graph_objects as go
from huggingface_hub import login as hf_login
import nnsight
from nnsight import LanguageModel

# ── Credentials & model ────────────────────────────────────────────────────────
HF_TOKEN = os.environ.get("HF_TOKEN", "")
API_KEY  = os.environ.get("NDIF_API_KEY", "")
MODEL_ID  = "meta-llama/Meta-Llama-3.1-8B"
LAYER_IDX = 28

hf_login(token=HF_TOKEN, add_to_git_credential=False)
nnsight.CONFIG.set_default_api_key(API_KEY)
model = LanguageModel(MODEL_ID)
print(f"Model ready: {MODEL_ID}\n")

# ── Concept configurations ─────────────────────────────────────────────────────
COLORS = ['Red', 'Orange', 'Yellow', 'Green', 'Blue', 'Indigo', 'Violet']
TEMPS  = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
AGES   = [10, 20, 30, 40, 50, 60, 70, 80]

CONCEPTS = [
    {
        "name": "Color",
        "values": COLORS,
        "k_range": range(1, 7),
        "templates": [
            lambda v, k: f"In the rainbow (Red, Orange, Yellow, Green, Blue, Indigo, Violet), what color is {k} positions after {v}?",
            lambda v, k: f"The rainbow goes Red, Orange, Yellow, Green, Blue, Indigo, Violet. Starting at {v} and moving {k} steps forward, what color do you reach?",
        ],
        "answer_fn": lambda vals, idx, k: vals[(idx + k) % len(vals)],
        "spline": "periodic",
        "cache": "color",
        "unit": "",
    },
    {
        "name": "Temperature",
        "values": TEMPS,
        "k_range": range(1, 6),
        "templates": [
            lambda v, k: f"What temperature is {k} degrees Celsius warmer than {v - k}°C?",
            lambda v, k: f"If the temperature is {v - k} degrees Celsius and it rises by {k} degrees, what is the new temperature in Celsius?",
        ],
        "answer_fn": lambda vals, idx, k: vals[idx],
        "spline": "natural",
        "cache": "temp",
        "unit": "°C",
    },
    {
        "name": "Age",
        "values": AGES,
        "k_range": range(1, 6),
        "templates": [
            lambda v, k: f"How old is someone who is {k} years older than a {v - k}-year-old?",
            lambda v, k: f"A person is {v - k} years old. In {k} years, how old will they be?",
        ],
        "answer_fn": lambda vals, idx, k: vals[idx],
        "spline": "natural",
        "cache": "age",
        "unit": " years",
    },
]


# ── Generic pipeline functions ─────────────────────────────────────────────────

def generate_prompts(cfg):
    prompts, labels = [], []
    for idx, v in enumerate(cfg["values"]):
        for k in cfg["k_range"]:
            for tmpl in cfg["templates"]:
                prompts.append(tmpl(v, k))
                labels.append(str(cfg["answer_fn"](cfg["values"], idx, k)))
    return prompts, np.array(labels)


def extract_or_load(cfg, prompts, labels):
    acts_path   = Path(f"{cfg['cache']}_acts.npy")
    labels_path = Path(f"{cfg['cache']}_labels.npy")

    if acts_path.exists():
        print(f"  Cache hit — loading {cfg['name']} activations from disk.")
        all_acts = np.load(acts_path)
        labels   = np.load(labels_path, allow_pickle=True)
        print(f"  Loaded: {all_acts.shape}")
        return all_acts, labels

    print(f"  Extracting {len(prompts)} activations for {cfg['name']}...")
    all_acts = []
    for i, prompt in enumerate(tqdm(prompts, desc=f"  {cfg['name']}")):
        for attempt in range(3):
            try:
                with model.trace(prompt, remote=True):
                    hidden = model.model.layers[LAYER_IDX].output[:, -1, :].save()
                act = hidden.squeeze(0).cpu().float().numpy()
                all_acts.append(act)
                break
            except Exception as e:
                print(f"\n    Prompt {i} attempt {attempt+1} failed: {e}")
                if attempt < 2:
                    time.sleep(5)
                else:
                    raise
        time.sleep(0.25)

    all_acts = np.stack(all_acts)
    np.save(acts_path, all_acts)
    np.save(labels_path, labels)
    print(f"  Saved {cfg['name']} activations: {all_acts.shape}")
    return all_acts, labels


def fit_pipeline(cfg, all_acts, labels):
    values = cfg["values"]
    N = len(values)

    # PCA step 1 → 64D
    N_INTER = min(64, len(all_acts))
    pca1 = PCA(n_components=N_INTER)
    acts_inter = pca1.fit_transform(all_acts)
    cumvar = np.cumsum(pca1.explained_variance_ratio_)
    print(f"  PCA-{N_INTER}: var(top 3)={cumvar[2]:.3f}, var(top 7)={cumvar[min(6,N_INTER-1)]:.3f}")

    # Centroids
    centroids = np.array([
        acts_inter[labels == str(v)].mean(axis=0)
        for v in values
    ])

    # Spline
    if cfg["spline"] == "periodic":
        centroids_w = np.vstack([centroids, centroids[0:1]])
        t_knots = np.arange(N + 1, dtype=float)
        spline = CubicSpline(t_knots, centroids_w, bc_type='periodic')
        t_dense = np.linspace(0, N, 300)
    else:
        t_knots = np.arange(N, dtype=float)
        spline = CubicSpline(t_knots, centroids)
        t_dense = np.linspace(0, N - 1, 300)

    curve_inter = spline(t_dense)

    # PCA step 2 → 3D (fit on spline samples)
    pca2 = PCA(n_components=3)
    curve_3d     = pca2.fit_transform(curve_inter)
    centroids_3d = pca2.transform(centroids)
    var = pca2.explained_variance_ratio_
    print(f"  PCA-3D: PC1={var[0]:.3f} PC2={var[1]:.3f} PC3={var[2]:.3f} total={var.sum():.3f}")

    # Centroid-only unbiased PCA (2D)
    pca_c = PCA(n_components=min(2, N - 1))
    cents_2d = pca_c.fit_transform(centroids)
    var_c = pca_c.explained_variance_ratio_

    return {
        "centroids": centroids,
        "centroids_3d": centroids_3d,
        "curve_3d": curve_3d,
        "t_dense": t_dense,
        "pca2_var": var,
        "cents_2d": cents_2d,
        "pca_c_var": var_c,
    }


def make_colors(n, spline_type):
    if spline_type == "periodic":
        # Cyclic HSV hues
        return ['#{:02x}{:02x}{:02x}'.format(*[int(c*255) for c in colorsys.hsv_to_rgb(i/n, 0.85, 0.88)])
                for i in range(n)]
    else:
        # Sequential colormap: cool blue → warm red
        return ['#{:02x}{:02x}{:02x}'.format(
                    int(255 * i/(n-1)),
                    int(80 * (1 - abs(2*i/(n-1) - 1))),
                    int(255 * (1 - i/(n-1))))
                for i in range(n)]


def plot_3d(cfg, result, colors):
    values    = cfg["values"]
    unit      = cfg["unit"]
    labels_v  = [f"{v}{unit}" for v in values]
    var       = result["pca2_var"]
    t_dense   = result["t_dense"]
    curve_3d  = result["curve_3d"]
    cents_3d  = result["centroids_3d"]
    N         = len(values)

    colorscale = [[i / (N-1), colors[i]] for i in range(N)]

    fig = go.Figure()
    fig.add_trace(go.Scatter3d(
        x=curve_3d[:, 0], y=curve_3d[:, 1], z=curve_3d[:, 2],
        mode='lines', name='Manifold Curve',
        line=dict(color=t_dense, colorscale=colorscale, width=6, showscale=False),
        hovertemplate='t=%.2f<extra>Spline</extra>',
    ))
    fig.add_trace(go.Scatter3d(
        x=cents_3d[:, 0], y=cents_3d[:, 1], z=cents_3d[:, 2],
        mode='markers+text', name='Centroids',
        text=labels_v, textposition='top center',
        textfont=dict(size=12, color='black', family='Arial Black'),
        marker=dict(size=10, color=colors, symbol='circle',
                    line=dict(color='black', width=1.5)),
        hovertemplate='%{text}<extra></extra>',
    ))
    fig.update_layout(
        title=dict(
            text=(f"{cfg['name']} Geometry — Llama 3.1 8B Layer {LAYER_IDX}<br>"
                  f"<sup>4096D → 64D PCA → {'Periodic' if cfg['spline']=='periodic' else 'Natural'} Spline → 3D | "
                  f"{N} concepts</sup>"),
            x=0.5, font=dict(size=13),
        ),
        scene=dict(
            xaxis_title=f"PC1 ({var[0]*100:.1f}%)",
            yaxis_title=f"PC2 ({var[1]*100:.1f}%)",
            zaxis_title=f"PC3 ({var[2]*100:.1f}%)",
            aspectmode='cube',
            camera=dict(eye=dict(x=1.5, y=1.5, z=0.8)),
        ),
        legend=dict(x=0.02, y=0.98),
        width=900, height=720,
        margin=dict(t=110, b=20, l=20, r=20),
    )
    out = Path(f"{cfg['cache']}_geometry_3d.html")
    fig.write_html(str(out))
    return out


def plot_2d_unbiased(cfg, result, colors):
    values   = cfg["values"]
    unit     = cfg["unit"]
    labels_v = [f"{v}{unit}" for v in values]
    cents_2d = result["cents_2d"]
    var_c    = result["pca_c_var"]
    N        = len(values)

    fig = go.Figure()
    # Connect adjacent concepts
    for i in range(N - 1):
        fig.add_trace(go.Scatter(
            x=[cents_2d[i, 0], cents_2d[i+1, 0]],
            y=[cents_2d[i, 1], cents_2d[i+1, 1]],
            mode='lines', line=dict(color='lightgray', width=1.5, dash='dot'),
            showlegend=False,
        ))
    if cfg["spline"] == "periodic":
        fig.add_trace(go.Scatter(
            x=[cents_2d[-1, 0], cents_2d[0, 0]],
            y=[cents_2d[-1, 1], cents_2d[0, 1]],
            mode='lines', line=dict(color='lightgray', width=1.5, dash='dot'),
            showlegend=False,
        ))
    for i, lbl in enumerate(labels_v):
        fig.add_trace(go.Scatter(
            x=[cents_2d[i, 0]], y=[cents_2d[i, 1]],
            mode='markers+text', text=[lbl], textposition='top center',
            marker=dict(size=14, color=colors[i], line=dict(color='black', width=1.5)),
            name=lbl, showlegend=False,
        ))
    fig.update_layout(
        title=f"{cfg['name']} — Centroid-only 2D PCA (no spline bias)",
        xaxis_title=f"PC1 ({var_c[0]*100:.1f}%)" if len(var_c) > 0 else "PC1",
        yaxis_title=f"PC2 ({var_c[1]*100:.1f}%)" if len(var_c) > 1 else "PC2",
        width=620, height=580,
        yaxis=dict(scaleanchor='x', scaleratio=1),
    )
    out = Path(f"{cfg['cache']}_geometry_2d_unbiased.html")
    fig.write_html(str(out))
    return out


def sanity_check(cfg, result):
    centroids = result["centroids"]
    values    = cfg["values"]
    N         = len(values)
    dist      = cdist(centroids, centroids)
    is_cyclic = cfg["spline"] == "periodic"
    concept_dist = (lambda i, j: min(abs(i-j), N-abs(i-j))) if is_cyclic else (lambda i, j: abs(i-j))

    adj_pass = 0
    for i in range(N):
        adj  = dist[i, (i+1) % N] if is_cyclic else (dist[i, i+1] if i+1 < N else None)
        opp_idx = (i + N//2) % N if is_cyclic else min(i + N//2, N-1)
        opp  = dist[i, opp_idx]
        if adj is not None and adj < opp:
            adj_pass += 1
    total = N if is_cyclic else N - 1
    print(f"  Adjacency check: {adj_pass}/{total} pass ({'✓' if adj_pass == total else '~'})")


# ── Main loop ──────────────────────────────────────────────────────────────────

for cfg in CONCEPTS:
    print(f"\n{'='*60}")
    print(f"  CONCEPT: {cfg['name']}  ({cfg['spline']} spline)")
    print(f"{'='*60}")

    prompts, labels = generate_prompts(cfg)
    n_per = len(prompts) // len(cfg["values"])
    print(f"  {len(prompts)} prompts ({n_per} per answer-value), {len(cfg['values'])} concepts")

    all_acts, labels = extract_or_load(cfg, prompts, labels)
    result = fit_pipeline(cfg, all_acts, labels)
    colors = make_colors(len(cfg["values"]), cfg["spline"])
    sanity_check(cfg, result)

    out3d  = plot_3d(cfg, result, colors)
    out2d  = plot_2d_unbiased(cfg, result, colors)
    print(f"  Saved: {out3d.name}  |  {out2d.name}")

print(f"\n{'='*60}")
print("All concepts complete. Open the HTML files in your browser.")
print("='*60}")
