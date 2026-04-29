# Web-ready copy — Predictive Mapping for Invasive Weed Management

Drop-in text for the portfolio site. Five sections, sized for typical web blocks.

---

## Hero

**Predictive Mapping for Invasive Weed Management**

Which Idaho ranger districts need to budget for enhanced post-harvest weed control — and which species should they prepare for?

Built from 77,648 invasive surveys (1934–2024), every Forest Service timber harvest in Idaho since 1900, 63,503 cleaned terrain points, USGS 30 m DEM, and TIGER 2024 roads. Random Forest with spatial cross-validation.

---

## 02 · The model

A Random Forest classifier predicts whether a location requires enhanced post-harvest weed management. Trained on 63,503 Idaho survey records and validated by holding out entire ranger districts (GroupKFold spatial cross-validation), so the model has to generalize to a district it has never seen.

> **AUC = 0.70 ± 0.07** (5-fold spatial CV, district held out)

Features: genus, land ownership, elevation, distance to nearest harvest, years since that harvest (computed from `DATE_COMPL` × `DATE_COLLE`), distance to nearest TIGER primary/secondary road.

### What predicts invasion (permutation importance)

| Rank | Feature | Importance |
|---|---|---|
| 1 | Elevation | 8.9% |
| 2 | Distance to road | 6.4% |
| 3 | Years since harvest | 4.9% |
| 4 | Distance to harvest | 3.9% |
| 5 | USFS lands | 2.9% |
| 6 | Other ownership | 1.8% |
| 7 | *Centaurea* | 1.1% |
| 8 | *Euphorbia* | 0.7% |

Disturbance proximity (distance to / years since harvest, road access) and terrain dominate. Species composition is a secondary signal once disturbance ecology is accounted for.

> **Why this is a defensible number.** Spatial cross-validation forces the model to generalize across districts, not memorize them. The fold-to-fold variation (std 0.065) reflects real heterogeneity between Idaho's ranger districts. AUC = 0.70 means the model meaningfully outperforms random (0.50) on locations it has never seen — which is the point of a "predictive" map.

---

## 03 · Specialist or enhanced?

A common framing claims certain genera (*Linaria*, *Chondrilla*) only appear after timber disturbance. Checked at the species level statewide:

| Category | Species |
|---|---|
| Harvest-enhanced (in harvest zones AND elsewhere) | **74** |
| Baseline only (never in harvest zones) | 42 |
| Harvest specialist (only in harvest zones, statewide) | **0** |

Of the 116 invasive species in the dataset, 74 are harvest-enhanced and 0 are pure harvest specialists. The "specialist" claim only holds at the district × species pair level (14 such pairs out of 1,073).

**Operational reframing:** post-harvest treatment isn't fighting unique invaders. It's fighting the same 74 species already on the landscape, with disturbance amplifying their establishment rate. Pre-harvest planning matters for *intensity*, not novelty.

Top operational priorities (harvest-enhanced species by total harvest occurrences): *Hieracium caespitosum*, *Centaurea stoebe*, *Leucanthemum vulgare*, *Hypericum perforatum*, *Cirsium arvense*, *Cynoglossum officinale*, *Centaurea biebersteinii*, *Tanacetum vulgare*, *Chondrilla juncea*, *Centaurea maculosa*.

---

## 04 · Where they concentrate

Mid-elevation zones (1,200–2,000 m) carry the heaviest invasion load. This aligns with where timber operations are economically viable: accessible terrain, mild climate, the warm exposures that R-selected invasives thrive on.

*Hieracium* and *Cynoglossum* push higher; *Centaurea* and *Euphorbia* spread more evenly.

---

## 05 · Limitations

1. **TIGER primary/secondary roads only.** Forest Service roads — the actual access points for harvest crews — aren't in the public TIGER file. Real distance-to-road would use the FSGeodata Forest Service Roads layer.
2. **Survey effort skews counts.** Districts surveyed more often have more positive points. Weighting by survey effort per district per year would help.
3. **Constructed target.** `enhanced_mgmt` is defined as `cover_pct ≥ 1` OR (recent harvest within 500 m AND ≤ 7 years). Defensible but not ground truth.
4. **Anachronistic roads.** TIGER roads are from 2024; surveys go back to 1934. The road network from earlier eras is approximated by today's network.
5. **Genus truncation.** 91.4% genus match rate; two genera (`Cynoglossu`, `Leucanthem`) appear as 10-character DBF-truncated names in the source shapefiles.

---

## Methodology

1. **Three-way spatial intersection** — districts × invasive surveys × harvest zones, reprojected to EPSG:4269.
2. **Genus aggregation** — full scientific names parsed to genus level. 91.4% match rate.
3. **Aspect handling** — converted to sin/cos components so 359° and 1° aren't treated as far apart.
4. **DBSCAN outlier removal** — eliminated invalid elevations (the -999999 nodata sentinels).
5. **Disturbance covariates** — for each survey point, found the nearest timber harvest in space and the nearest TIGER road; computed `years_since_harvest` from `DATE_COMPL` × `DATE_COLLE`.
6. **Spatial cross-validation** — GroupKFold by district (district ID is *not* a feature; entire districts are held out at test time).
7. **Random Forest** — 300 trees, max depth 12, min samples leaf 20.
8. **Permutation importance** — for ranking features.

---

## Data sources

- USDA Forest Service FSGeodata Clearinghouse — invasive surveys, timber harvests, district boundaries (https://data.fs.usda.gov/geodata/edw/)
- USGS National Map — 30 m DEM
- US Census TIGER/Line 2024 — Idaho primary/secondary roads
- All analysis code in `NEWANALYSIS/scripts/`. Reproducible from the raw shapefiles.
