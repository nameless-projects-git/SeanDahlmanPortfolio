# NEWANALYSIS — v2 model with spatial CV + disturbance covariates

This is the rigorous re-do of the original predictive mapping project, addressing the leakage caveat surfaced during the WEBSITE patch.

## What changed vs v1

| Aspect | v1 (original paper) | v2 (this folder) |
|---|---|---|
| Cross-validation | Random 5-fold | **GroupKFold by district** (district held out) |
| District ID | One-hot encoded as feature | **Dropped** (was the leak) |
| Time since harvest | Not used | **Computed from `DATE_COMPL` × `DATE_COLLE`** |
| Distance to nearest harvest | Not used | **From spatial join** |
| Distance to road | Not used | **TIGER 2024 primary/secondary roads** |
| Land owner | Not used | **`OWNER_NAME`** (USFS, BLM, PRIV, STDL, NPS, Other) |
| Sample size | ~10,000 cleaned points | **~63,500 Idaho survey records** with full covariates |
| AUC reported | 0.987 | (see `data/auc_summary.json`) |

## Why this is more honest

The v1 model had two compounding issues:

1. **Random CV with district as a feature.** When you randomly split 53k points across 57 districts, every district appears in both train and test sets. The model learns "this district = high invasion rate" by memorization, then is rewarded for recognizing the same district at test time. AUC = 0.99 is the consequence.
2. **Missing the obvious covariates.** Disturbance recency and road proximity are the canonical predictors of invasive spread in the literature (see Rejmanek & Davis 1999, Mortensen et al. 2009). The v1 model had no way to express them — so district ID became a proxy.

v2 fixes both: districts are held out as test groups (the model has to generalize to a district it has never seen), and the missing covariates are added so the legitimate signal has somewhere to live.

## Pipeline

```
01_build_features.py    — joins Bio + Harvest + DEM + Roads + Districts → v2_features.parquet
02_train_models.py       — fits v1 + v2 with their respective CV regimes, saves comparison
```

Reproducible from the raw shapefiles in `data/`. Takes ~3 min on a modern laptop.

## Key files

| File | Description |
|---|---|
| `data/v2_features.parquet` | One row per Idaho survey, all covariates |
| `data/model_comparison.csv` | Per-fold AUC for v1 and v2 |
| `data/v2_feature_importance.csv` | Permutation importance ranking |
| `data/auc_summary.json` | Headline numbers (for the website) |
| `figures/v1_vs_v2_auc.png` | The before/after chart |
| `figures/v2_feature_importance.png` | What actually predicts invasion when district leakage is removed |

## Limitations that remain

Even v2 isn't perfect:

- **TIGER primary/secondary roads only.** Forest roads (the actual access points for harvest crews) aren't in the TIGER public file. Real distance-to-road would use the FSGeodata Forest Service Roads layer; that's a tier-2 add.
- **Survey effort still skews counts.** Districts surveyed more often have more positive points. Weighting by survey effort per district per year would help.
- **`enhanced_mgmt` is a constructed target.** We define it as `cover_pct ≥ 1` OR (recent harvest within 500 m AND ≤ 7 years). That definition is defensible but not ground truth.
- **TIGER roads are 2024;** weed surveys go back to 1934. The road network from earlier eras is approximated by today's network.

## What this does NOT replace

- The story map in `WEBSITE/portfolio/` — should be updated to feature the v2 numbers.
- The original paper — leave it as v1, link to NEWANALYSIS as the rigorous follow-up.
