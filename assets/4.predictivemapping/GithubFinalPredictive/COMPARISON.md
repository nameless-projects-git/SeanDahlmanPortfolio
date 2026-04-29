# How this analysis compares to `Dahlman_TAA4.pdf`

The original assignment (`Dahlman_TAA4.pdf`, June 2025) built a Random Forest classifier on ~10,000 cleaned weed survey points and reported AUC = 0.987 with district 41557 dominating predictive importance at 51.8%. The conclusion was that geography (one specific ranger district) and one genus (Euphorbia) drove invasion risk, with terrain a distant third.

Reviewing that work for the portfolio, two methodological issues surfaced — the kind of issues that, if left unaddressed, would weaken the project as a sample of analytical work. This re-analysis (the `analysis/` folder and the website in `portfolio/`) addresses both. Numbers below are what the website publishes and are the headline takeaways.

## What changed

| Aspect | Original paper | Re-analysis (this folder) |
|---|---|---|
| **Cross-validation** | Random 5-fold | **GroupKFold by district** — entire ranger districts held out at test time, so the model is forced to generalize to districts it has never seen |
| **District ID as feature** | One-hot encoded (57 levels) | **Dropped from feature set** |
| **Time since harvest** | Not used | **Computed** from `DATE_COMPL` × `DATE_COLLE` per survey point |
| **Distance to nearest harvest** | Not used | Computed via spatial join |
| **Distance to road** | Not used (paper noted this as a limitation) | **TIGER 2024 primary/secondary roads**, free Census download |
| **Land owner** | Not used | `OWNER_NAME` (USFS, BLM, PRIV, STDL, NPS, Other) |
| **Sample size** | ~10,000 cleaned points | **63,503 Idaho survey records** with full covariate joins |
| **Feature importance** | Standard Gini importance | Permutation importance (less biased toward high-cardinality features) |
| **Reported AUC** | 0.987 ± 0.006 | **0.705 ± 0.065** |

## Why the AUC dropped from 0.99 to 0.70

The original number was real — the model genuinely fit the training data that well — but the validation regime allowed it to memorize district identity. With 57 districts one-hot encoded as features and random 5-fold CV, every district appears in both train and test sets. The model learned "this district = high invasion rate" by memory, then was rewarded for recognizing the same district at test time. Standard Gini importance compounded the issue by inflating high-cardinality features.

When district identity is removed and validation forces generalization across districts, AUC = 0.70 ± 0.07 is what's actually defensible. That number means the model meaningfully outperforms random (0.50) on locations it has never seen — which is the entire point of a "predictive" map.

## What predicts invasion (corrected)

In the original paper, district 41557 (Westside Ranger District) carried 51.8% of predictive importance and elevation came in third at 10%. With permutation importance, spatial CV, and the missing covariates added:

| Rank | Feature | Importance |
|---|---|---|
| 1 | Elevation | 8.9% |
| 2 | Distance to road | 6.4% |
| 3 | Years since harvest | 4.9% |
| 4 | Distance to nearest harvest | 3.9% |
| 5 | USFS lands | 2.9% |
| 6 | Other ownership | 1.8% |
| 7 | *Centaurea* | 1.1% |
| 8 | *Euphorbia* | 0.7% |

Disturbance proximity (years since harvest, distance to harvest, distance to road) and terrain dominate. Species composition is a secondary signal once disturbance ecology is accounted for. This aligns with the canonical invasive-spread literature (Rejmanek & Davis 1999, Mortensen et al. 2009) — predictors the original model couldn't access because the relevant covariates weren't in the feature set.

## Specialist vs. enhanced — corrected framing

The paper described certain genera (*Linaria*, *Chondrilla*) as "harvest specialists" that only appear after timber disturbance. Rolling the joined dataset to the species level statewide:

| Category | Species count |
|---|---|
| Harvest-enhanced (in harvest AND elsewhere) | 74 |
| Baseline only (never in harvest zones) | 42 |
| Harvest specialist (only in harvest zones, statewide) | **0** |

No invasive species in Idaho is a pure harvest specialist statewide. The "specialist" label only holds at the district × species pair level (14 such pairs out of 1,073 in the comparison table). Operationally this matters: post-harvest treatment isn't fighting unique invaders, it's fighting the same 74 species already on the landscape with disturbance amplifying their establishment rate.

## What's preserved from the original work

These findings hold up and are featured on the website:

- **Mid-elevation hotspot, 1,200–2,000 m** — confirmed; the same band where timber operations are economically viable.
- **K-means k=2** — bootstrap-validated, silhouette 0.96, cleanly separates harvest-impacted from undisturbed terrain.
- **Westside RD as the highest-priority district** — still ranks #1 on enhanced-management rate, just not at 52% of the model's predictive weight.
- **The participatory map design framework** — still the right approach for a real Forest Service deployment.
- **Cartographic decisions** in the static QGIS map — color choices, Brewer ramp, hierarchy — still hold; that work isn't reproduced here but is preserved in `Dahlman_TAA4.pdf`.

## Limitations that remain

This re-analysis is more rigorous than the original but isn't perfect:

1. **TIGER primary/secondary roads only.** Forest Service roads — the actual access points for harvest crews — aren't in the public TIGER file.
2. **Survey effort skews counts.** Districts surveyed more often have more positive points.
3. **Constructed target.** `enhanced_mgmt` is defined as `cover_pct ≥ 1` OR (recent harvest within 500 m AND ≤ 7 years). Defensible but not ground truth.
4. **Anachronistic roads.** TIGER roads are from 2024; surveys go back to 1934.
5. **Genus truncation.** 91.4% match rate; two genera (`Cynoglossu`, `Leucanthem`) appear as 10-character DBF-truncated names in the source shapefiles.

## Reproducibility

The re-analysis pipeline is two scripts:

```sh
python analysis/scripts/01_build_features.py    # ~3 min, builds v2_features.parquet
python analysis/scripts/02_train_models.py      # ~2 min, fits and compares
```

Inputs needed (see `inputs/README.md`):
- `Bio_InvasivePlantCurrent.shp` — USDA FSGeodata Clearinghouse
- `Actv_TimberHarvest.shp` — USDA FSGeodata Clearinghouse
- `ForestDistricts.shp` — included in `inputs/`
- `tl_2024_16_prisecroads.shp` — included in `analysis/data/roads_idaho/`
- USGS 30 m DEM for Idaho — USGS National Map

The intermediate `analysis/data/v2_features.parquet` is included so reviewers can rerun model training without redoing the spatial joins.
