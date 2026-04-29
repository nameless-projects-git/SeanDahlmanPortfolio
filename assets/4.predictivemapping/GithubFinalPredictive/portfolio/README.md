# Predictive Mapping for Invasive Weed Management — portfolio site

Single-page scrollytelling site for GitHub Pages. No build step.

## Stack

- **MapLibre GL JS** (CDN) — interactive choropleth + point overlay, no API key needed
- **D3 v7** (CDN) — animated bar chart with standard↔permutation toggle
- **Vanilla HTML/CSS/JS** — no framework, no bundler, no `node_modules`
- **IntersectionObserver** — scroll fade-in for story sections

## Run locally

```sh
python3 -m http.server 8000
# open http://127.0.0.1:8000
```

Any static server will do (`npx serve`, `caddy file-server`, etc.). ES modules require an HTTP server — opening `index.html` via `file://` will fail.

## Deploy to GitHub Pages

1. Commit `WEBSITE/portfolio/` to your repo
2. Settings → Pages → source: branch `main`, folder `/WEBSITE/portfolio` (or move to repo root)
3. Done — total payload ~1.1 MB on first load, ~360 KB after caching

## File map

```
index.html             5 sections of scrollytelling narrative
style.css              CSS Grid layout, warm-sequential palette matching the QGIS map
js/
  map.js               MapLibre setup, click-to-explore district panel
  charts.js            D3 bar chart, standard↔permutation toggle (the headline interaction)
  scroll.js            IntersectionObserver fade-in
data/
  districts.geojson    57 ranger district polygons + management metrics (270 KB)
  weed_points.json     ~2,500 stratified-sampled invasive points, compact array (70 KB)
  v2_importance.json   Top 15 features, permutation importance
  auc_summary.json     AUC results from spatial cross-validation
  species.json         116 species with category (harvest_enhanced / baseline_only)
  districts_top.json   Top 10 priority districts
  meta.json            Hero stats
figures/               Pre-rendered ridge plot + specialist breakdown
```

## Regenerate data

The data files are produced by `../scripts/04_prep_web_data.py` from the authoritative shapefiles in `RobustAnalysis/` and `FinalAnalysis/FinalPRIME/`. Run it after any analysis change.

## What's intentionally not here

- No predict-at-a-click ML inference (the trained model has known leakage; covered in section 5)
- No time slider (sparse pre-1990 harvest data made it unconvincing)
- No 3D terrain (flex, not finding)
- No framework

These could be v2 additions if the project grows.
