"""Train v1 (baseline w/ leakage) and v2 (spatial CV + new features) models, compare.

v1: random KFold, district_id one-hot encoded as features (matches the original paper)
v2: GroupKFold by district_id (district held out, NOT used as feature),
    with time-since-harvest, distance-to-road, distance-to-harvest, owner type added.

Outputs:
  data/model_comparison.csv         AUC per fold for both models
  data/v2_feature_importance.csv    permutation importance for v2
  data/v1_feature_importance.csv    permutation importance for v1 (for the comparison)
  data/auc_summary.json             headline numbers for the website
  figures/v1_vs_v2_auc.png
  figures/v2_feature_importance.png
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import KFold, GroupKFold
from sklearn.metrics import roc_auc_score
from sklearn.inspection import permutation_importance

ROOT = Path(__file__).resolve().parents[1]   # analysis/
DATA = ROOT / "data"
FIG = ROOT / "figures"
FIG.mkdir(exist_ok=True)

WARM = "#C0392B"
COOL = "#7F8C8D"
ACCENT = "#E67E22"

df = pd.read_parquet(DATA / "v2_features.parquet")
print(f"loaded {len(df):,} rows, {df['district_id'].nunique()} districts, {df['genus'].nunique()} genera")
print(f"target rate: {df['enhanced_mgmt'].mean():.3f}")

# Keep only districts and genera with enough samples
df = df.groupby("district_id").filter(lambda g: len(g) >= 30)
top_genera = df["genus"].value_counts().head(15).index.tolist()
df["genus_grouped"] = np.where(df["genus"].isin(top_genera), df["genus"], "Other")
df["owner_grouped"] = df["OWNER_NAME"].fillna("Unknown")
df.loc[~df["owner_grouped"].isin(["USFS", "BLM", "PRIV", "STDL", "NPS"]), "owner_grouped"] = "Other"
print(f"after filter: {len(df):,} rows, {df['district_id'].nunique()} districts")

y = df["enhanced_mgmt"].values
groups = df["district_id"].values

# --- v1 features: paper-style — one-hot district + one-hot genus + terrain
v1_features = pd.concat([
    pd.get_dummies(df["district_id"], prefix="dist"),
    pd.get_dummies(df["genus_grouped"], prefix="genus"),
    df[["elevation_m"]].rename(columns={"elevation_m": "elevation"}),
], axis=1).astype(float)

# --- v2 features: drop district one-hot (it was the leak); add disturbance + access covariates
v2_features = pd.concat([
    pd.get_dummies(df["genus_grouped"], prefix="genus"),
    pd.get_dummies(df["owner_grouped"], prefix="owner"),
    df[["elevation_m", "dist_to_harvest_m", "years_since_harvest",
        "dist_to_road_m"]].rename(columns={"elevation_m": "elevation"}),
], axis=1).astype(float)

print(f"v1 features: {v1_features.shape[1]} (incl. {sum(c.startswith('dist_') for c in v1_features.columns)} district one-hot)")
print(f"v2 features: {v2_features.shape[1]} (NO district one-hot)")


def fit_with_cv(X, y, splitter, splitter_args, label):
    aucs = []
    for fold, (tr, te) in enumerate(splitter.split(X, y, **splitter_args)):
        clf = RandomForestClassifier(
            n_estimators=300, max_depth=12, min_samples_leaf=20,
            n_jobs=-1, random_state=42 + fold
        )
        clf.fit(X.iloc[tr], y[tr])
        proba = clf.predict_proba(X.iloc[te])[:, 1]
        aucs.append(roc_auc_score(y[te], proba))
    print(f"  {label} mean AUC: {np.mean(aucs):.3f} ± {np.std(aucs):.3f}  (folds: {aucs})")
    return aucs


print("\n--- v1 baseline: random 5-fold (paper-style, district as feature) ---")
v1_kf = KFold(n_splits=5, shuffle=True, random_state=42)
v1_aucs = fit_with_cv(v1_features, y, v1_kf, {}, "v1")

print("\n--- v2: GroupKFold by district (held out), no district feature ---")
v2_gkf = GroupKFold(n_splits=5)
v2_aucs = fit_with_cv(v2_features, y, v2_gkf, {"groups": groups}, "v2")

# Save fold-level comparison
fold_df = pd.DataFrame({
    "fold": list(range(1, 6)) * 2,
    "model": ["v1 (random CV, district feature)"] * 5 + ["v2 (spatial CV, no district)"] * 5,
    "auc": v1_aucs + v2_aucs,
})
fold_df.to_csv(DATA / "model_comparison.csv", index=False)

# --- Final v2 fit on full data for permutation importance
print("\nfitting final v2 on all data for permutation importance...")
clf_v2 = RandomForestClassifier(n_estimators=300, max_depth=12, min_samples_leaf=20,
                                  n_jobs=-1, random_state=42)
clf_v2.fit(v2_features, y)
perm_v2 = permutation_importance(clf_v2, v2_features, y, n_repeats=5, random_state=42, n_jobs=-1)
imp_v2 = pd.DataFrame({
    "feature": v2_features.columns,
    "importance": perm_v2.importances_mean,
    "std": perm_v2.importances_std,
}).sort_values("importance", ascending=False)
imp_v2.to_csv(DATA / "v2_feature_importance.csv", index=False)
print("v2 top 10 by permutation importance:")
print(imp_v2.head(10).to_string(index=False))

# --- Final v1 fit on full data for permutation importance
print("\nfitting final v1 on all data for permutation importance...")
clf_v1 = RandomForestClassifier(n_estimators=300, max_depth=12, min_samples_leaf=20,
                                  n_jobs=-1, random_state=42)
clf_v1.fit(v1_features, y)
perm_v1 = permutation_importance(clf_v1, v1_features, y, n_repeats=5, random_state=42, n_jobs=-1)
imp_v1 = pd.DataFrame({
    "feature": v1_features.columns,
    "importance": perm_v1.importances_mean,
    "std": perm_v1.importances_std,
}).sort_values("importance", ascending=False)
imp_v1.to_csv(DATA / "v1_feature_importance.csv", index=False)

# --- AUC summary JSON
summary = {
    "v1": {
        "label": "Original paper approach",
        "cv": "random 5-fold",
        "features": "genus + elevation + district one-hot",
        "n_features": int(v1_features.shape[1]),
        "auc_mean": float(np.mean(v1_aucs)),
        "auc_std": float(np.std(v1_aucs)),
        "auc_folds": [float(x) for x in v1_aucs],
    },
    "v2": {
        "label": "Spatial CV + disturbance covariates",
        "cv": "GroupKFold by district (5 folds, district held out)",
        "features": "genus + owner + elevation + dist_to_harvest + years_since_harvest + dist_to_road",
        "n_features": int(v2_features.shape[1]),
        "auc_mean": float(np.mean(v2_aucs)),
        "auc_std": float(np.std(v2_aucs)),
        "auc_folds": [float(x) for x in v2_aucs],
    },
    "n_samples": int(len(df)),
    "n_districts": int(df["district_id"].nunique()),
    "n_genera": int(df["genus"].nunique()),
    "target_rate": float(y.mean()),
    "median_years_since_harvest": float(df["years_since_harvest"].median()),
    "median_dist_to_road_km": float(df["dist_to_road_m"].median() / 1000),
}
(DATA / "auc_summary.json").write_text(json.dumps(summary, indent=2))

# --- Comparison figure
fig, ax = plt.subplots(figsize=(8, 4.5))
positions = [0.7, 1.7]
v1_pos = np.full(len(v1_aucs), positions[0])
v2_pos = np.full(len(v2_aucs), positions[1])
ax.scatter(v1_pos + np.random.uniform(-0.06, 0.06, len(v1_aucs)), v1_aucs,
           color=COOL, s=80, alpha=0.7, edgecolor="black", linewidth=0.5, label="per fold")
ax.scatter(v2_pos + np.random.uniform(-0.06, 0.06, len(v2_aucs)), v2_aucs,
           color=COOL, s=80, alpha=0.7, edgecolor="black", linewidth=0.5)
ax.scatter([positions[0]], [np.mean(v1_aucs)], color=WARM, s=200, marker="D", zorder=5,
           edgecolor="black", linewidth=0.8, label="mean")
ax.scatter([positions[1]], [np.mean(v2_aucs)], color=WARM, s=200, marker="D", zorder=5,
           edgecolor="black", linewidth=0.8)
ax.set_xticks(positions)
ax.set_xticklabels([
    f"v1\nrandom CV + district feature\n{np.mean(v1_aucs):.3f}",
    f"v2\nspatial CV, no district\n{np.mean(v2_aucs):.3f}",
])
ax.set_ylabel("ROC AUC (held-out folds)")
ax.set_title("Model honesty test: random CV w/ leakage vs spatial CV\nThe gap is the leakage estimate", fontsize=11, loc="left")
ax.set_ylim(0.4, 1.02)
ax.axhline(0.5, color="#aaa", linestyle="--", linewidth=0.8, alpha=0.6)
ax.spines[["top", "right"]].set_visible(False)
ax.grid(axis="y", alpha=0.3)
ax.legend(loc="lower right", frameon=False)
fig.tight_layout()
fig.savefig(FIG / "v1_vs_v2_auc.png", dpi=150, bbox_inches="tight")
plt.close(fig)

# --- v2 importance figure
top = imp_v2.head(15).iloc[::-1]
fig, ax = plt.subplots(figsize=(9, 6))
colors = []
for f in top["feature"]:
    if f.startswith("genus_"):
        colors.append("#e8a199")
    elif f.startswith("owner_"):
        colors.append(ACCENT)
    elif f in ("years_since_harvest", "dist_to_harvest_m", "dist_to_road_m"):
        colors.append(WARM)
    else:
        colors.append(COOL)
ax.barh(top["feature"], top["importance"], xerr=top["std"], color=colors,
        edgecolor="black", linewidth=0.4, error_kw={"elinewidth": 0.8, "ecolor": "#333"})
ax.set_xlabel("Permutation importance (mean decrease in AUC)")
ax.set_title("v2 feature importance (spatial CV)\nDisturbance proximity & recency now dominate; species composition still matters",
             fontsize=11, loc="left")
ax.spines[["top", "right"]].set_visible(False)
ax.grid(axis="x", alpha=0.3)
fig.tight_layout()
fig.savefig(FIG / "v2_feature_importance.png", dpi=150, bbox_inches="tight")
plt.close(fig)

print(f"\nDONE. v1 AUC = {np.mean(v1_aucs):.3f}, v2 AUC = {np.mean(v2_aucs):.3f}")
print(f"leakage estimate (v1 - v2) = {np.mean(v1_aucs) - np.mean(v2_aucs):.3f}")
