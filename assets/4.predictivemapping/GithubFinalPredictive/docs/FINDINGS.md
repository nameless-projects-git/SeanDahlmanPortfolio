# Predictive Mapping for Invasive Weed Management — Authoritative Findings

This file is the source of truth for the website. Numbers below are what gets published.

## Data inputs

| Source | What it is | Path |
|---|---|---|
| Invasive surveys | 77,648 polygons, 1934–2024 | `data/Bio_InvasivePlantCurrent` |
| Timber harvests | 79,990 Idaho harvest polygons, 1900–2024 | `data/Actv_TimberHarvest` |
| Forest districts | 57 Idaho ranger districts | `FinalData/ForestDistricts.shp` |
| TIGER roads | 1,492 primary/secondary segments | `NEWANALYSIS/data/roads_idaho/` |
| DEM | USGS 30 m | `Hillshade/output_USGS30m.tif` |

After Idaho-only filtering, spatial joins, and missing-value drops: **63,503 survey records** with full covariates across **42 ranger districts** and **81 genera**. Genus matching success: 91.4%.

## Headline results

### Model

Random Forest classifier (300 trees, max depth 12, min samples leaf 20). Spatial 5-fold cross-validation by district (GroupKFold) — district ID is not a feature; entire districts are held out at test time.

**AUC = 0.705 ± 0.065** (mean ± std across 5 folds: 0.677, 0.798, 0.609, 0.754, 0.686)

The fold-to-fold variation is itself a finding: it reflects real heterogeneity between Idaho's ranger districts (some are easier to predict than others), not statistical noise.

### Top predictors (permutation importance)

| Feature | Importance | Category |
|---|---|---|
| Elevation | 8.9% | Terrain |
| Distance to road | 6.4% | Access |
| Years since harvest | 4.9% | Disturbance |
| Distance to nearest harvest | 3.9% | Disturbance |
| USFS lands | 2.9% | Ownership |
| Other ownership | 1.8% | Ownership |
| *Centaurea* | 1.1% | Species |
| *Euphorbia* | 0.7% | Species |
| Other (each ≤ 0.5%) | — | — |

**Story:** disturbance proximity (distance to and years since harvest, road access) and terrain dominate. Species composition is a secondary signal once disturbance ecology is accounted for.

### Specialist vs. enhanced (species-level)

| Category | Species count |
|---|---|
| Harvest-enhanced (in harvest AND elsewhere) | 74 |
| Baseline only (never in harvest zones) | 42 |
| Harvest specialist (only in harvest zones, statewide) | **0** |

No invasive species in Idaho is a pure harvest specialist statewide. Specialist behavior only emerges at the district × species pair level (14 such pairs out of 1,073).

### Top operational priorities

By total harvest-zone occurrences:
*Hieracium caespitosum*, *Centaurea stoebe*, *Leucanthemum vulgare*, *Hypericum perforatum*, *Cirsium arvense*, *Cynoglossum officinale*, *Centaurea biebersteinii*, *Tanacetum vulgare*, *Chondrilla juncea*, *Centaurea maculosa*, plus two more.

### Elevation pattern

Mid-elevation zones (1,200–2,000 m) carry the heaviest invasion load — the same band where timber operations are economically viable. *Hieracium* and *Cynoglossum* push higher; *Centaurea* and *Euphorbia* spread more evenly.

### Clustering (terrain × management)

K-means k=2 is bootstrap-validated (silhouette 0.96 on optimal split, drops to 0.45 at k=3). The two clusters cleanly separate harvest-impacted terrain from undisturbed.

## Methodology summary

1. Three-way spatial intersection: districts × invasive surveys × harvest zones, reprojected to EPSG:4269 (CONUS Albers EPSG:5070 for distance computations).
2. Genus aggregation from full scientific names. 91.4% match rate.
3. Aspect converted to sin/cos components.
4. DBSCAN outlier removal for invalid elevations.
5. Disturbance covariates: nearest harvest in space + `DATE_COMPL` − `DATE_COLLE` for time-since-harvest.
6. Random Forest with **GroupKFold spatial cross-validation by district**.
7. Permutation importance for feature ranking.
8. K-means with bootstrap validation.

## Limitations

1. **TIGER primary/secondary roads only.** Forest Service roads aren't in the public TIGER file.
2. **Survey effort still skews counts.** Districts surveyed more often have more positive points.
3. **Constructed target.** `enhanced_mgmt` is defined as `cover_pct ≥ 1` OR (recent harvest within 500 m AND ≤ 7 years). Defensible but not ground truth.
4. **Anachronistic roads.** TIGER 2024 roads applied to surveys back to 1934.
5. **Genus truncation.** 91.4% match rate; two genera (`Cynoglossu`, `Leucanthem`) appear as 10-character DBF-truncated names.

## Files in this folder

- `data/` — authoritative CSV inputs
- `figures/` — regenerated PNGs
- `scripts/` — reproducible regen scripts
- `portfolio/` — the deployable website
- `COPY.md` — web-ready copy

The full pipeline lives in `../NEWANALYSIS/scripts/` (`01_build_features.py` → `02_train_models.py`).
