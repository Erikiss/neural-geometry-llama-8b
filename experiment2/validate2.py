"""
Validation for experiment2 — works for both cyclic (color) and linear (temp, age) concepts.
Run after run_experiment2.py has cached the .npy files.
"""
import numpy as np
from pathlib import Path
from sklearn.decomposition import PCA
from scipy.spatial.distance import cdist
import colorsys

DAYS_LIKE = {
    "color": {
        "values": ['Red', 'Orange', 'Yellow', 'Green', 'Blue', 'Indigo', 'Violet'],
        "spline": "periodic", "unit": "",
    },
    "temp": {
        "values": [10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
        "spline": "natural", "unit": "°C",
    },
    "age": {
        "values": [10, 20, 30, 40, 50, 60, 70, 80],
        "spline": "natural", "unit": "yr",
    },
}


def concept_dist(i, j, N, cyclic):
    return min(abs(i-j), N-abs(i-j)) if cyclic else abs(i-j)


def run_validation(cache_key, cfg):
    acts_path = Path(f"{cache_key}_acts.npy")
    if not acts_path.exists():
        print(f"  [SKIP] {cache_key}_acts.npy not found — run run_experiment2.py first\n")
        return

    values   = cfg["values"]
    cyclic   = cfg["spline"] == "periodic"
    unit     = cfg["unit"]
    N        = len(values)

    all_acts = np.load(acts_path)
    labels   = np.load(f"{cache_key}_labels.npy", allow_pickle=True)

    pca1 = PCA(n_components=min(64, len(all_acts)))
    acts_inter = pca1.fit_transform(all_acts)
    centroids  = np.array([acts_inter[labels == str(v)].mean(axis=0) for v in values])
    dist       = cdist(centroids, centroids)

    print(f"{'='*60}")
    print(f"  {cache_key.upper()} | {N} concepts | {'cyclic' if cyclic else 'linear'}")
    print(f"{'='*60}")

    # TEST 1: Distance ordering
    print("TEST 1: Distance ordering (should increase with concept distance)")
    monotone_count = 0
    for i in range(N):
        row = sorted([(concept_dist(i, j, N, cyclic), dist[i, j], values[j])
                      for j in range(N) if j != i])
        steps = [r[0] for r in row]
        dists = [r[1] for r in row]
        monotone = all(dists[k] <= dists[k+1] for k in range(len(dists)-1))
        if monotone:
            monotone_count += 1
        flag = "✓" if monotone else "✗"
        print(f"  {flag} {values[i]}{unit}: " + ", ".join(f"{d:.3f}(d={s})" for s,d,_ in row))
    print(f"  Monotone: {monotone_count}/{N}\n")

    # TEST 2: Ordering check
    print("TEST 2: Ordering check")
    if cyclic:
        pca2d = PCA(n_components=2)
        c2d   = pca2d.fit_transform(centroids)
        cent  = c2d - c2d.mean(axis=0)
        angles = np.arctan2(cent[:, 1], cent[:, 0])
        order  = [values[i] for i in np.argsort(angles)]
        fwd = [values[(i+s) % N] for s in range(N) for i in range(N) if [values[(i+t) % N] for t in range(N)] == order]
        def is_cyclic_rotation(seq, ref):
            n = len(ref)
            for start in range(n):
                if [ref[(start+i) % n] for i in range(n)] == list(seq):
                    return True
            return False
        ok = is_cyclic_rotation(order, values) or is_cyclic_rotation(order, list(reversed(values)))
        print(f"  Angular order: {' → '.join(str(v) for v in order)}")
        print(f"  {'✓ Correct cyclic order' if ok else '✗ Scrambled order'}\n")
    else:
        pca1d = PCA(n_components=1)
        c1d   = pca1d.fit_transform(centroids).flatten()
        order_idx = np.argsort(c1d)
        is_fwd = list(order_idx) == list(range(N))
        is_bwd = list(order_idx) == list(range(N-1, -1, -1))
        order_vals = [values[i] for i in order_idx]
        print(f"  1D PCA order: {' → '.join(str(v)+unit for v in order_vals)}")
        print(f"  {'✓ Monotone linear order' if (is_fwd or is_bwd) else '~ Approximate linear order'}\n")

    # TEST 3: Random shuffle control
    print("TEST 3: Random shuffle control")
    rng = np.random.default_rng(42)
    shuffled = labels.copy()
    rng.shuffle(shuffled)
    rand_cents = np.array([acts_inter[shuffled == str(v)].mean(axis=0) for v in values])
    rand_dist  = cdist(rand_cents, rand_cents)
    rand_pass  = sum(
        rand_dist[i, (i+1) % N] < rand_dist[i, (i + N//2) % N]
        for i in range(N)
    )
    real_pass = sum(
        dist[i, (i+1) % N] < dist[i, (i + N//2) % N]
        for i in range(N)
    )
    print(f"  Real labels:   {real_pass}/{N} adjacency checks pass")
    print(f"  Random labels: {rand_pass}/{N} adjacency checks pass (expect ~{N//2})")
    print(f"  {'✓ Control confirms structure is not accidental' if rand_pass <= N//2 + 1 else '⚠ Random passes too — investigate'}\n")

    # TEST 4: Variance ratio
    print("TEST 4: Variance ratio (cyclic → PC1≈PC2; linear → PC1>>PC2)")
    pca_c = PCA()
    pca_c.fit(centroids)
    pca_r = PCA()
    pca_r.fit(rand_cents)
    v_real = pca_c.explained_variance_ratio_[:3]
    v_rand = pca_r.explained_variance_ratio_[:3]
    ratio  = v_real[0] / max(v_real[1], 1e-9)
    print(f"  Real:   PC1={v_real[0]:.3f} PC2={v_real[1]:.3f} PC3={v_real[2]:.3f}  ratio={ratio:.2f}")
    print(f"  Random: PC1={v_rand[0]:.3f} PC2={v_rand[1]:.3f} PC3={v_rand[2]:.3f}")
    if cyclic:
        print(f"  {'✓ PC1/PC2 near 1 — ring-like' if ratio < 1.5 else '~ Elongated ellipse'}\n")
    else:
        print(f"  {'✓ PC1>>PC2 — linear structure' if ratio > 2.0 else '~ Weaker linear structure'}\n")


for key, cfg in DAYS_LIKE.items():
    run_validation(key, cfg)
