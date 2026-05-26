import colorsys
import numpy as np
from sklearn.decomposition import PCA
from scipy.interpolate import CubicSpline
from models import ConceptSpec


def _make_colors(n: int, cyclic: bool) -> list[str]:
    if cyclic:
        return [
            "#{:02x}{:02x}{:02x}".format(
                *[int(c * 255) for c in colorsys.hsv_to_rgb(i / n, 0.82, 0.90)]
            )
            for i in range(n)
        ]
    # Sequential: cool blue → warm red
    return [
        "#{:02x}{:02x}{:02x}".format(
            int(255 * i / (n - 1)) if n > 1 else 128,
            int(80 * (1 - abs(2 * i / (n - 1) - 1))) if n > 1 else 80,
            int(255 * (1 - i / (n - 1))) if n > 1 else 128,
        )
        for i in range(n)
    ]


def run_pipeline(spec: ConceptSpec, all_acts: np.ndarray) -> tuple[dict, list[float]]:
    labels = np.array([p.answer for p in spec.prompts])
    N = len(spec.values)

    # PCA step 1 → intermediate space
    N_INTER = min(64, len(all_acts))
    pca1 = PCA(n_components=N_INTER)
    acts_inter = pca1.fit_transform(all_acts)

    # Per-value centroids (skip values with no matching prompts)
    centroids = []
    valid_values = []
    for v in spec.values:
        mask = labels == v
        if mask.sum() == 0:
            continue
        centroids.append(acts_inter[mask].mean(axis=0))
        valid_values.append(v)

    if len(valid_values) < 3:
        raise ValueError(f"Only {len(valid_values)} concept values have prompts — need at least 3.")

    centroids = np.stack(centroids)
    N = len(valid_values)

    # Spline
    if spec.is_cyclic and N >= 3:
        centroids_w = np.vstack([centroids, centroids[0:1]])
        t_knots = np.arange(N + 1, dtype=float)
        spline = CubicSpline(t_knots, centroids_w, bc_type="periodic")
        t_dense = np.linspace(0, N, 300)
    else:
        t_knots = np.arange(N, dtype=float)
        spline = CubicSpline(t_knots, centroids)
        t_dense = np.linspace(0, N - 1, 300)

    curve_inter = spline(t_dense)

    # PCA step 2 → 3D (fit on spline samples)
    pca2 = PCA(n_components=3)
    curve_3d = pca2.fit_transform(curve_inter)
    cents_3d = pca2.transform(centroids)
    var = pca2.explained_variance_ratio_.tolist()

    colors = _make_colors(N, spec.is_cyclic and N >= 3)
    colorscale = [[i / max(N - 1, 1), colors[i]] for i in range(N)]

    figure = {
        "data": [
            {
                "type": "scatter3d",
                "mode": "lines",
                "name": "Manifold Curve",
                "x": curve_3d[:, 0].tolist(),
                "y": curve_3d[:, 1].tolist(),
                "z": curve_3d[:, 2].tolist(),
                "line": {
                    "color": t_dense.tolist(),
                    "colorscale": colorscale,
                    "width": 6,
                },
                "hovertemplate": "t=%{line.color:.2f}<extra>Spline</extra>",
            },
            {
                "type": "scatter3d",
                "mode": "markers+text",
                "name": "Centroids",
                "x": cents_3d[:, 0].tolist(),
                "y": cents_3d[:, 1].tolist(),
                "z": cents_3d[:, 2].tolist(),
                "text": valid_values,
                "textposition": "top center",
                "textfont": {"size": 13, "color": "white", "family": "Arial Black"},
                "marker": {
                    "size": 10,
                    "color": colors,
                    "line": {"color": "white", "width": 1.5},
                },
                "hovertemplate": "%{text}<extra></extra>",
            },
        ],
        "layout": {
            "paper_bgcolor": "#0d1117",
            "plot_bgcolor": "#0d1117",
            "font": {"color": "#e6edf3"},
            "scene": {
                "xaxis": {
                    "title": f"PC1 ({var[0]*100:.1f}%)",
                    "gridcolor": "#21262d",
                    "backgroundcolor": "#0d1117",
                    "color": "#8b949e",
                },
                "yaxis": {
                    "title": f"PC2 ({var[1]*100:.1f}%)",
                    "gridcolor": "#21262d",
                    "backgroundcolor": "#0d1117",
                    "color": "#8b949e",
                },
                "zaxis": {
                    "title": f"PC3 ({var[2]*100:.1f}%)",
                    "gridcolor": "#21262d",
                    "backgroundcolor": "#0d1117",
                    "color": "#8b949e",
                },
                "aspectmode": "cube",
                "camera": {"eye": {"x": 1.5, "y": 1.5, "z": 0.8}},
                "bgcolor": "#0d1117",
            },
            "legend": {"x": 0.02, "y": 0.98, "bgcolor": "rgba(0,0,0,0)"},
            "margin": {"t": 30, "b": 10, "l": 10, "r": 10},
        },
    }

    return figure, var
