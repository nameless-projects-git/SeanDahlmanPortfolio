# Predictive Mapping for Invasive Weed Management

Identifying which Idaho ranger districts need to budget for enhanced post-harvest weed control, and which species they should prepare for. Built from federal datasets (Forest Service invasive surveys, timber harvest records, ranger district boundaries, USGS DEM, TIGER roads) using Random Forest with spatial cross-validation.

**Headline result:** AUC = 0.705 ± 0.065 on 5-fold spatial CV (district held out), trained on 63,503 Idaho survey records. Disturbance proximity (years since harvest, distance to road) and terrain dominate; species composition is a secondary signal.

## What's in this folder

```
portfolio/             Deployable single-page website (GitHub Pages-ready)
analysis/              Reproducible v2 pipeline (feature build + model training)
inputs/                Small supporting data (ranger district polygons + roads)
docs/                  Authoritative findings, web copy
Dahlman_TAA4.pdf       Original assignment writeup, June 2025
COMPARISON.md          How this re-analysis differs from the original paper
README.md              This file
```

## Quick view

The portfolio site is a single-page scrollytelling layout with a MapLibre GL JS map and D3 importance chart. To preview locally:

```sh
cd portfolio
python3 -m http.server 8000
# open http://127.0.0.1:8000
```

Total payload ~660 KB. No build step, no framework, no API keys.

## Quick rerun (analysis only)

If you want to verify the model numbers without rebuilding features from raw shapefiles:

```sh
python analysis/scripts/02_train_models.py
```

This reads `analysis/data/v2_features.parquet` (the joined feature table, included) and fits both the v1-style baseline and the v2 spatial-CV model. Outputs land in `analysis/data/` and `analysis/figures/`.

To rebuild features from raw shapefiles, see `inputs/README.md` for the required downloads and run `analysis/scripts/01_build_features.py`.

## How to read the project

1. **Start with `portfolio/index.html`** — that's the public face of the project.
2. **Then `COMPARISON.md`** — explains what changed between the original paper and the re-analysis, and why.
3. **Then `Dahlman_TAA4.pdf`** — the original assignment, retained for context.
4. **For the methodology** — `analysis/README.md` walks through the pipeline; `docs/FINDINGS.md` is the authoritative numerical summary.

## Stack

- **Spatial joins, model fitting:** Python (geopandas, scikit-learn, rasterio, pandas)
- **Static figures:** matplotlib
- **Website:** vanilla HTML + CSS + ES module JS, MapLibre GL JS, D3 v7 (both via CDN)
- **Data formats:** Shapefile + Parquet for analysis, GeoJSON + JSON for the web

## Data sources

- USDA Forest Service FSGeodata Clearinghouse — invasive plant surveys, timber harvests, district boundaries
- USGS National Map — 30 m DEM
- US Census TIGER/Line 2024 — Idaho primary/secondary roads

All sources public. None require API keys or auth.

## Author

Sean Dahlman · GIS portfolio · 2025–2026
