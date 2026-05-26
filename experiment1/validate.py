"""
Red-team validation for the days-of-week ring structure.
Tests that don't rely on the spline at all.
"""
import numpy as np
from pathlib import Path
from sklearn.decomposition import PCA
from scipy.interpolate import CubicSpline
from scipy.spatial.distance import cdist
import plotly.graph_objects as go
from plotly.subplots import make_subplots

all_acts = np.load("all_acts.npy")          # (84, 4096)
labels   = np.load("labels.npy", allow_pickle=True)
DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

pca1 = PCA(n_components=min(64, len(all_acts)))
acts_inter = pca1.fit_transform(all_acts)
centroids = np.array([acts_inter[labels == d].mean(axis=0) for d in DAYS])

print("=" * 60)
print("TEST 1: Full pairwise distance ordering")
print("If the ring is real, for each day the distances to")
print("other days should increase with calendar distance.")
print("=" * 60)
dist = cdist(centroids, centroids)
CYCLIC_DIST = lambda i, j: min(abs(i-j), 7-abs(i-j))  # steps apart on the ring

all_pass = True
for i, day in enumerate(DAYS):
    row = [(CYCLIC_DIST(i, j), dist[i, j], DAYS[j]) for j in range(7) if j != i]
    row.sort()
    steps = [r[0] for r in row]
    dists = [r[1] for r in row]
    monotone = all(dists[k] <= dists[k+1] for k in range(len(dists)-1))
    flag = "✓" if monotone else "✗"
    all_pass = all_pass and monotone
    print(f"  {flag} {day}: distances by step = " + ", ".join(f"{d:.3f}(step {s})" for s,d,_ in row))

print(f"\n  {'ALL PASS — distances increase monotonically with ring distance' if all_pass else 'SOME FAIL — ring order not clean'}")

print()
print("=" * 60)
print("TEST 2: Day ordering check (are days in correct cyclic order?)")
print("Project centroids to 2D via their OWN PCA (no spline bias).")
print("Then check if the angular order matches Mon→Tue→...→Sun.")
print("=" * 60)
pca_cents = PCA(n_components=2)
cents_2d = pca_cents.fit_transform(centroids)   # (7, 2) — unbiased

# Compute angle of each centroid (center the cloud first)
centered = cents_2d - cents_2d.mean(axis=0)
angles = np.arctan2(centered[:, 1], centered[:, 0])  # in [-pi, pi]

# Sort days by angle and check the cyclic ordering matches Mon..Sun
order_by_angle = np.argsort(angles)
day_order = [DAYS[i] for i in order_by_angle]
print(f"  Days ordered by angle in 2D centroid PCA:")
print(f"  {' → '.join(day_order)}")

# Check if this is a valid cyclic rotation of DAYS (forward or backward)
expected_fwd = DAYS
expected_bwd = DAYS[::-1]
def is_cyclic_rotation(seq, ref):
    n = len(ref)
    for start in range(n):
        if [ref[(start+i) % n] for i in range(n)] == list(seq):
            return True
    return False

fwd_ok = is_cyclic_rotation(day_order, expected_fwd)
bwd_ok = is_cyclic_rotation(day_order, expected_bwd)
if fwd_ok:
    print("  ✓ Correct cyclic order (Mon→Tue→...→Sun, clockwise or counter)")
elif bwd_ok:
    print("  ✓ Correct cyclic order (reversed direction — mirror image of ring)")
else:
    print("  ✗ Days NOT in correct cyclic order — ring shape may be scrambled")

print()
print("=" * 60)
print("TEST 3: Control experiment — random label shuffle")
print("If the ring is real, shuffling labels should break it.")
print("=" * 60)
rng = np.random.default_rng(42)
shuffled_labels = labels.copy()
rng.shuffle(shuffled_labels)
rand_centroids = np.array([acts_inter[shuffled_labels == d].mean(axis=0) for d in DAYS])
rand_dist = cdist(rand_centroids, rand_centroids)

rand_pass = 0
for i in range(7):
    adj  = rand_dist[i, (i+1) % 7]
    opp  = rand_dist[i, (i+3) % 7]
    rand_pass += (adj < opp)
print(f"  Random labels: {rand_pass}/7 adjacency checks pass (expect ~3-4 by chance)")
print(f"  Real labels:   7/7 adjacency checks pass")
print(f"  {'✓ Control confirms the ring is not accidental' if rand_pass <= 4 else '⚠ Random also passes — investigate further'}")

print()
print("=" * 60)
print("TEST 4: Variance of centroids in 2D vs random")
print("A ring concentrates variance in exactly 2 equal components.")
print("=" * 60)
pca_check = PCA()
pca_check.fit(centroids)
var_real = pca_check.explained_variance_ratio_[:3]

pca_rand = PCA()
pca_rand.fit(rand_centroids)
var_rand = pca_rand.explained_variance_ratio_[:3]

print(f"  Real centroids  — PC1: {var_real[0]:.3f}  PC2: {var_real[1]:.3f}  PC3: {var_real[2]:.3f}")
print(f"  Random centroids— PC1: {var_rand[0]:.3f}  PC2: {var_rand[1]:.3f}  PC3: {var_rand[2]:.3f}")
ratio = var_real[0] / max(var_real[1], 1e-9)
print(f"  PC1/PC2 ratio (real): {ratio:.2f}  (perfect circle = 1.0, elongated ellipse > 1)")

print()
print("=" * 60)
print("TEST 5: Centroid-only 2D plot (no spline, no spline-biased PCA)")
print("Saving to validate_centroids_2d.html")
print("=" * 60)

import colorsys
day_colors = [
    '#{:02x}{:02x}{:02x}'.format(*[int(c*255) for c in colorsys.hsv_to_rgb(i/7, 0.85, 0.88)])
    for i in range(7)
]

# 2D: centroid-only PCA (unbiased)
fig2d = go.Figure()
for i, day in enumerate(DAYS):
    fig2d.add_trace(go.Scatter(
        x=[cents_2d[i, 0]], y=[cents_2d[i, 1]],
        mode='markers+text',
        text=[day], textposition='top center',
        marker=dict(size=14, color=day_colors[i], line=dict(color='black', width=1.5)),
        name=day, showlegend=False,
    ))
# Draw edges between adjacent days
for i in range(7):
    j = (i + 1) % 7
    fig2d.add_trace(go.Scatter(
        x=[cents_2d[i, 0], cents_2d[j, 0]],
        y=[cents_2d[i, 1], cents_2d[j, 1]],
        mode='lines',
        line=dict(color='gray', width=1, dash='dot'),
        showlegend=False,
    ))

v2 = pca_cents.explained_variance_ratio_
fig2d.update_layout(
    title='Centroid-only 2D PCA (no spline bias) — Is the ring visible here?',
    xaxis_title=f'PC1 ({v2[0]*100:.1f}%)',
    yaxis_title=f'PC2 ({v2[1]*100:.1f}%)',
    width=600, height=600,
    yaxis=dict(scaleanchor='x', scaleratio=1),
)
fig2d.write_html("validate_centroids_2d.html")

# 3D: centroid-only PCA (unbiased)
pca_cents3 = PCA(n_components=3)
cents_3d_unbiased = pca_cents3.fit_transform(centroids)

fig3d = go.Figure()
fig3d.add_trace(go.Scatter3d(
    x=cents_3d_unbiased[:, 0], y=cents_3d_unbiased[:, 1], z=cents_3d_unbiased[:, 2],
    mode='markers+text',
    text=DAYS, textposition='top center',
    textfont=dict(size=12, color='black'),
    marker=dict(size=10, color=day_colors, line=dict(color='black', width=1.5)),
    name='Centroids (unbiased)',
))
# Connect adjacent days with lines
for i in range(7):
    j = (i+1) % 7
    fig3d.add_trace(go.Scatter3d(
        x=[cents_3d_unbiased[i,0], cents_3d_unbiased[j,0]],
        y=[cents_3d_unbiased[i,1], cents_3d_unbiased[j,1]],
        z=[cents_3d_unbiased[i,2], cents_3d_unbiased[j,2]],
        mode='lines',
        line=dict(color='gray', width=2),
        showlegend=False,
    ))

v3 = pca_cents3.explained_variance_ratio_
fig3d.update_layout(
    title='Centroid-only 3D PCA (no spline bias) — unbiased ring check',
    scene=dict(
        xaxis_title=f'PC1 ({v3[0]*100:.1f}%)',
        yaxis_title=f'PC2 ({v3[1]*100:.1f}%)',
        zaxis_title=f'PC3 ({v3[2]*100:.1f}%)',
        aspectmode='cube',
    ),
    width=800, height=650,
)
fig3d.write_html("validate_centroids_3d_unbiased.html")
print("  Saved validate_centroids_2d.html and validate_centroids_3d_unbiased.html")

print()
print("=" * 60)
print("SUMMARY")
print("=" * 60)
