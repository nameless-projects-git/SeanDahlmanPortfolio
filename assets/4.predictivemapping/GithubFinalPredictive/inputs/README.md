# Inputs

This folder ships the small supporting data needed by the analysis pipeline. The large raw federal datasets are not included in the repo (they're public and free, just bulky).

## Already in this folder

| File | Source | Size |
|---|---|---|
| `ForestDistricts.{shp,shx,dbf,prj,cpg,qmd}` | USDA Forest Service FSGeodata Clearinghouse | ~6 MB |

The TIGER 2024 Idaho primary/secondary roads shapefile lives in `../analysis/data/roads_idaho/` (already extracted there).

The intermediate `../analysis/data/v2_features.parquet` is also shipped, so you can run model training (`02_train_models.py`) without rebuilding features from scratch.

## To rerun feature building from raw shapefiles

You need three additional downloads. Place them under `inputs/raw/` (or set `$RAW_DATA_DIR` to wherever you put them):

```
inputs/raw/
├── Bio_InvasivePlantCurrent/
│   └── S_USA.Bio_InvasivePlantCurrent.shp  (+ sidecars)
├── Actv_TimberHarvest/
│   └── S_USA.Actv_TimberHarvest.shp        (+ sidecars)
└── Hillshade/
    └── output_USGS30m.tif
```

### Download instructions

**1. Invasive plant surveys** (`S_USA.Bio_InvasivePlantCurrent`)
- https://data.fs.usda.gov/geodata/edw/datasets.php
- Search for *"invasive plant current"* → download the zipped shapefile.
- ~5 GB unzipped (national, 910k polygons).

**2. Timber harvests** (`S_USA.Actv_TimberHarvest`)
- Same FSGeodata Clearinghouse.
- Search for *"timber harvest"* (the `Actv_TimberHarvest` layer).
- ~5 GB unzipped.

**3. USGS 30 m DEM for Idaho** (`output_USGS30m.tif`)
- https://apps.nationalmap.gov/downloader/
- Filter to Idaho boundaries, request 1 arc-second DEM, format GeoTIFF.
- Or use any state-extent USGS 30 m DEM file you already have — the script samples elevation at survey-polygon centroids.

Then run:

```sh
python ../analysis/scripts/01_build_features.py
```

That will rebuild `analysis/data/v2_features.parquet` (~3 minutes, dominated by spatial joins).
