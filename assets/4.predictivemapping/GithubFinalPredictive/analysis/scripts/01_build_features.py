"""Build v2 feature set: time-since-harvest, distance-to-road, owner, terrain.

Inputs (raw, see inputs/README.md for downloads):
  $RAW/Bio_InvasivePlantCurrent/S_USA.Bio_InvasivePlantCurrent.shp
  $RAW/Actv_TimberHarvest/S_USA.Actv_TimberHarvest.shp
  $RAW/Hillshade/output_USGS30m.tif

Inputs (shipped with this folder):
  inputs/ForestDistricts.shp
  analysis/data/roads_idaho/tl_2024_16_prisecroads.shp

Output:
  analysis/data/v2_features.parquet  (one row per weed survey, Idaho only)
"""
from pathlib import Path
import os
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.warp import transform as rio_transform

PROJECT = Path(__file__).resolve().parents[2]   # GithubFinalPredictive/
ANALYSIS = PROJECT / "analysis"
# Raw federal datasets live wherever you downloaded them.
# Default: inputs/raw/. Override with: RAW_DATA_DIR=/some/path python 01_build_features.py
RAW = Path(os.environ.get("RAW_DATA_DIR", PROJECT / "inputs" / "raw"))

BIO_PATH     = RAW / "Bio_InvasivePlantCurrent" / "S_USA.Bio_InvasivePlantCurrent.shp"
HARVEST_PATH = RAW / "Actv_TimberHarvest" / "S_USA.Actv_TimberHarvest.shp"
DEM_PATH     = RAW / "Hillshade" / "output_USGS30m.tif"
DIST_PATH    = PROJECT / "inputs" / "ForestDistricts.shp"
ROADS_PATH   = ANALYSIS / "data" / "roads_idaho" / "tl_2024_16_prisecroads.shp"

OUT = ANALYSIS / "data" / "v2_features.parquet"

# --- 1. Load Idaho districts and build a buffered Idaho mask
districts = gpd.read_file(DIST_PATH).to_crs("EPSG:4326")
print(f"districts: {len(districts)}")
idaho_union = districts.geometry.union_all()

# --- 2. Load and filter Bio surveys to Idaho-intersecting polygons
print("loading invasive surveys...")
bio = gpd.read_file(BIO_PATH)
bio = bio.to_crs("EPSG:4326")
print(f"  global rows: {len(bio):,}")
bio = bio[bio.intersects(idaho_union)].copy()
print(f"  idaho rows: {len(bio):,}")

bio = bio[[
    "SITE_ID_FS", "SCIENTIFIC", "DATE_COLLE", "TREATMENT_",
    "INFESTED_A", "COVER_PCT", "OWNER_NAME", "GIS_ACRES", "geometry"
]].copy()
bio["DATE_COLLE"] = pd.to_datetime(bio["DATE_COLLE"], errors="coerce")
bio = bio.dropna(subset=["DATE_COLLE", "SCIENTIFIC"])
bio["genus"] = bio["SCIENTIFIC"].str.split().str[0]
bio["year_collected"] = bio["DATE_COLLE"].dt.year
bio["centroid"] = bio.geometry.centroid

# --- 3. Load and filter harvests to Idaho
print("loading harvests...")
harv = gpd.read_file(HARVEST_PATH)
harv = harv.to_crs("EPSG:4326")
harv = harv[harv["STATE_ABBR"] == "ID"].copy()
print(f"  idaho harvest rows: {len(harv):,}")
harv["DATE_COMPL"] = pd.to_datetime(harv["DATE_COMPL"], errors="coerce")
harv = harv.dropna(subset=["DATE_COMPL"])
harv["harvest_year"] = harv["DATE_COMPL"].dt.year
harv = harv[["FACTS_ID", "harvest_year", "GIS_ACRES", "geometry"]].copy()
harv["centroid"] = harv.geometry.centroid

# --- 4. Spatial join: nearest harvest to each weed point (in projected CRS for accurate distances)
print("computing time-since-harvest + distance-to-harvest...")
PROJ = "EPSG:5070"  # CONUS Albers (meters)
bio_pts = bio.set_geometry("centroid")[["SITE_ID_FS", "year_collected", "genus", "OWNER_NAME",
                                          "INFESTED_A", "COVER_PCT", "TREATMENT_", "GIS_ACRES",
                                          "centroid"]].copy()
bio_pts = bio_pts.set_geometry("centroid").set_crs("EPSG:4326").to_crs(PROJ)

harv_pts = harv.set_geometry("centroid")[["FACTS_ID", "harvest_year", "centroid"]].copy()
harv_pts = harv_pts.set_geometry("centroid").set_crs("EPSG:4326").to_crs(PROJ)

joined = gpd.sjoin_nearest(bio_pts, harv_pts, how="left", distance_col="dist_to_harvest_m")
joined["years_since_harvest"] = joined["year_collected"] - joined["harvest_year"]

# Keep only the nearest harvest per point (sjoin_nearest can return ties)
joined = joined.sort_values("dist_to_harvest_m").drop_duplicates("SITE_ID_FS", keep="first")
joined = joined.drop(columns=[c for c in ["index_right"] if c in joined.columns])
print(f"  joined rows: {len(joined):,}")
print(f"  median dist to nearest harvest: {joined['dist_to_harvest_m'].median():.0f} m")
print(f"  median years since harvest: {joined['years_since_harvest'].median():.1f} y")

# --- 5. Distance to nearest primary/secondary road
print("loading TIGER roads...")
roads = gpd.read_file(ROADS_PATH).to_crs(PROJ)
print(f"  road segments: {len(roads):,}")
joined = gpd.sjoin_nearest(joined, roads[["geometry"]].assign(_road=1),
                            how="left", distance_col="dist_to_road_m")
joined = joined.drop(columns=[c for c in ["index_right", "_road"] if c in joined.columns])
joined = joined.sort_values("dist_to_road_m").drop_duplicates("SITE_ID_FS", keep="first")
print(f"  median dist to road: {joined['dist_to_road_m'].median():.0f} m")

# --- 6. Sample DEM at each centroid (elevation, slope from neighbors)
print("sampling DEM...")
joined_ll = joined.to_crs("EPSG:4326")
xs = joined_ll.geometry.x.values
ys = joined_ll.geometry.y.values

elevs = np.full(len(joined_ll), np.nan)
with rasterio.open(DEM_PATH) as src:
    pts_proj = list(rio_transform("EPSG:4326", src.crs, xs, ys))
    sample_xy = list(zip(pts_proj[0], pts_proj[1]))
    for i, val in enumerate(src.sample(sample_xy)):
        elevs[i] = val[0]
joined["elevation_m"] = elevs

# --- 7. Spatial join districts to assign district_id (group for spatial CV)
print("assigning district groups...")
districts_proj = districts[["DISTRICTOR", "geometry"]].rename(columns={"DISTRICTOR": "district_id"}).to_crs(PROJ)
joined = gpd.sjoin(joined, districts_proj, how="left", predicate="intersects")
joined = joined.drop(columns=[c for c in ["index_right"] if c in joined.columns])
joined = joined.drop_duplicates("SITE_ID_FS", keep="first")
print(f"  district id null count: {joined['district_id'].isna().sum()}")

# --- 8. Build target: enhanced management proxy = recent + relatively high cover/area
# Use the same definition as the original: harvest_enhanced via cover or proximity
# Here: location needs enhanced management if either cover_pct >= 1 OR within 500m of a harvest within 7 years
joined["recent_harvest"] = (joined["years_since_harvest"].between(0, 7)).astype(int)
joined["near_harvest"] = (joined["dist_to_harvest_m"] < 500).astype(int)
joined["enhanced_mgmt"] = (
    (joined["COVER_PCT"].fillna(0) >= 1.0) |
    ((joined["recent_harvest"] == 1) & (joined["near_harvest"] == 1))
).astype(int)

# --- 9. Final feature table
keep = [
    "SITE_ID_FS", "district_id", "genus", "year_collected",
    "elevation_m", "dist_to_harvest_m", "years_since_harvest",
    "dist_to_road_m", "OWNER_NAME", "INFESTED_A", "COVER_PCT", "GIS_ACRES",
    "recent_harvest", "near_harvest", "enhanced_mgmt",
]
out = joined[keep].copy()
out = out.dropna(subset=["district_id", "elevation_m", "years_since_harvest", "dist_to_road_m"])
out["elevation_m"] = out["elevation_m"].astype(float).round(1)
out["dist_to_harvest_m"] = out["dist_to_harvest_m"].round(0)
out["dist_to_road_m"] = out["dist_to_road_m"].round(0)
out["years_since_harvest"] = out["years_since_harvest"].astype(int)
out["INFESTED_A"] = out["INFESTED_A"].fillna(0)
out["COVER_PCT"] = out["COVER_PCT"].fillna(0)

out.to_parquet(OUT, index=False)
print(f"\nwrote {OUT}")
print(f"  rows: {len(out):,}")
print(f"  enhanced_mgmt positive rate: {out['enhanced_mgmt'].mean():.3f}")
print(f"  unique districts: {out['district_id'].nunique()}")
print(f"  unique genera: {out['genus'].nunique()}")
print(f"  feature summary:")
print(out[["elevation_m", "dist_to_harvest_m", "years_since_harvest", "dist_to_road_m"]].describe().round(1))
