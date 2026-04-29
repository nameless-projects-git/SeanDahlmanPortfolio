// MapLibre setup + district choropleth + click handler + point overlay

// --- Initial view: change these three numbers to set the page-load camera.
// Tip: open the browser console, pan/zoom to where you want, and the
// console will print the matching {center, zoom, bearing, pitch} block.
const INITIAL_VIEW = {
  center:  [-113.5, 45.55],
  zoom:    5.75,
  bearing: 0,
  pitch:   0,
};

const COLORS = {
  "Very High": "#c0392b",
  "High":      "#e67e22",
  "Medium":    "#d4ac6b",
  "Low":       "#d8d1c4",
};

const map = new maplibregl.Map({
  container: "map",
  style: {
    version: 8,
    sources: {
      raster: {
        type: "raster",
        tiles: ["https://server.arcgisonline.com/ArcGIS/rest/services/World_Shaded_Relief/MapServer/tile/{z}/{y}/{x}"],
        tileSize: 256,
        attribution: "Esri Shaded Relief"
      }
    },
    layers: [{ id: "bg", type: "raster", source: "raster" }]
  },
  center:  INITIAL_VIEW.center,
  zoom:    INITIAL_VIEW.zoom,
  bearing: INITIAL_VIEW.bearing,
  pitch:   INITIAL_VIEW.pitch,
  attributionControl: { compact: true },
  scrollZoom: false,   // scroll wheel passes through to the page
  boxZoom: false,
});
map.dragRotate.disable();
map.touchZoomRotate.disableRotation();

// Live view logger — pan/zoom and copy the printed block into INITIAL_VIEW above
let _viewLogTimer;
map.on("moveend", () => {
  clearTimeout(_viewLogTimer);
  _viewLogTimer = setTimeout(() => {
    const c = map.getCenter();
    const block = {
      center:  [+c.lng.toFixed(4), +c.lat.toFixed(4)],
      zoom:    +map.getZoom().toFixed(2),
      bearing: +map.getBearing().toFixed(1),
      pitch:   +map.getPitch().toFixed(1),
    };
    console.log("[map view]", JSON.stringify(block));
  }, 250);
});
map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");

map.on("load", async () => {
  const [districts, points, top] = await Promise.all([
    fetch("data/districts.geojson").then(r => r.json()),
    fetch("data/weed_points.json").then(r => r.json()),
    fetch("data/districts_top.json").then(r => r.json()),
  ]);

  const topIds = new Set(top.map(d => d.district_id));
  districts.features.forEach(f => {
    f.properties.is_top = topIds.has(f.properties.district_id);
  });

  map.addSource("districts", { type: "geojson", data: districts });
  map.addLayer({
    id: "districts-fill",
    type: "fill",
    source: "districts",
    paint: {
      "fill-color": [
        "match",
        ["get", "mgmt_intensity"],
        "Very High", COLORS["Very High"],
        "High", COLORS["High"],
        "Medium", COLORS["Medium"],
        "Low", COLORS["Low"],
        "#bbb"
      ],
      "fill-opacity": 0.62,
      "fill-outline-color": "#3a2a25",
    },
  });
  map.addLayer({
    id: "districts-line",
    type: "line",
    source: "districts",
    paint: { "line-color": "#3a2a25", "line-width": 0.5, "line-opacity": 0.7 },
  });
  map.addLayer({
    id: "districts-line-hover",
    type: "line",
    source: "districts",
    paint: { "line-color": "#1a1a1a", "line-width": 2.5 },
    filter: ["==", "district_id", ""],
  });

  // Points: build geojson on the fly from compact array
  const pointsGeoJSON = {
    type: "FeatureCollection",
    features: points.rows.map(r => ({
      type: "Feature",
      geometry: { type: "Point", coordinates: [r[0], r[1]] },
      properties: {
        genus: points.genera[r[2]],
        elevation: r[3],
        enhanced_mgmt: r[4],
      },
    })),
  };
  map.addSource("points", { type: "geojson", data: pointsGeoJSON });
  map.addLayer({
    id: "points",
    type: "circle",
    source: "points",
    paint: {
      "circle-radius": [
        "interpolate", ["linear"], ["zoom"],
        4, 1.2,
        7, 2.2,
        10, 4
      ],
      "circle-color": "#1a1a1a",
      "circle-opacity": 0.55,
      "circle-stroke-width": 0,
    },
  });

  // Click district -> update side panel
  map.on("click", "districts-fill", (e) => {
    const f = e.features[0];
    map.setFilter("districts-line-hover", ["==", "district_id", f.properties.district_id]);
    renderDistrictPanel(f.properties);
  });
  map.on("mouseenter", "districts-fill", () => map.getCanvas().style.cursor = "pointer");
  map.on("mouseleave", "districts-fill", () => map.getCanvas().style.cursor = "");

  // Hero stats + meta
  const meta = await fetch("data/meta.json").then(r => r.json());
  const stats = document.getElementById("data-stats");
  if (stats) {
    const items = [
      [meta.n_surveys.toLocaleString(), "invasive surveys"],
      [meta.n_points_cleaned.toLocaleString(), "cleaned points"],
      [meta.n_districts, "ranger districts"],
      [meta.n_species_total, "invasive species"],
      [(meta.genus_match_rate * 100).toFixed(1) + "%", "genus match rate"],
      [`${meta.elev_range_m[0]}–${meta.elev_range_m[1]} m`, "elevation range"],
    ];
    stats.innerHTML = items.map(([n, l]) =>
      `<li><span class="num">${n}</span><span class="label">${l}</span></li>`
    ).join("");
  }
});

function renderDistrictPanel(p) {
  const el = document.getElementById("district-panel");
  const intensityClass = `badge badge-${p.mgmt_intensity.toLowerCase().replace(" ", "")}`;
  const enhancedPct = (p.enhanced_rate * 100).toFixed(0) + "%";
  const harvestK = p.harvest_ha > 1000
    ? (p.harvest_ha / 1000).toFixed(1) + " k ha"
    : Math.round(p.harvest_ha).toLocaleString() + " ha";

  el.innerHTML = `
    <h3>${p.name}</h3>
    <p class="forest">${p.forest}</p>
    <p><span class="${intensityClass}">${p.mgmt_intensity}</span></p>
    <dl>
      <dt>Enhanced rate</dt><dd>${enhancedPct}</dd>
      <dt>Enhanced species</dt><dd>${p.enhanced_count} / ${p.total_species}</dd>
      <dt>Harvest occurrences</dt><dd>${p.harvest_count.toLocaleString()}</dd>
      <dt>Harvest area</dt><dd>${harvestK}</dd>
      <dt>District acres</dt><dd>${(p.acres / 1000).toFixed(0)} k</dd>
      <dt>District ID</dt><dd>${p.district_id}</dd>
    </dl>
  `;
}
