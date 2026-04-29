// Static v2 feature-importance bar chart, animated on first render.
const data = await fetch("data/v2_importance.json").then(r => r.json());
const summary = await fetch("data/auc_summary.json").then(r => r.json());

const COLORS = {
  terrain:     "#7F8C8D",
  access:      "#C0392B",
  disturbance: "#E67E22",
  owner:       "#D4AC6B",
  genus:       "#E8A199",
  other:       "#bbb",
};

const sorted = [...data].sort((a, b) => b.importance - a.importance).reverse();

const margin = { top: 16, right: 90, bottom: 70, left: 180 };
const width = 760;
const height = 30 * sorted.length + margin.top + margin.bottom;

const root = d3.select("#importance-chart").append("svg")
  .attr("viewBox", `0 0 ${width} ${height}`)
  .attr("preserveAspectRatio", "xMidYMid meet");

const g = root.append("g").attr("transform", `translate(${margin.left},${margin.top})`);
const innerW = width - margin.left - margin.right;
const innerH = height - margin.top - margin.bottom;

const xMax = d3.max(sorted, d => d.importance + d.std);
const x = d3.scaleLinear().domain([0, xMax * 1.05]).range([0, innerW]);
const y = d3.scaleBand().domain(sorted.map(d => d.label)).range([innerH, 0]).padding(0.25);

g.append("g").attr("transform", `translate(0,${innerH})`)
  .call(d3.axisBottom(x).ticks(5).tickFormat(d3.format(".1%")));

g.selectAll(".bar").data(sorted).join("rect")
  .attr("class", "bar")
  .attr("x", 0).attr("y", d => y(d.label)).attr("height", y.bandwidth())
  .attr("fill", d => COLORS[d.category] || COLORS.other)
  .attr("width", 0)
  .transition().duration(800).delay((d, i) => i * 40)
  .attr("width", d => x(d.importance));

g.selectAll(".bar-label").data(sorted).join("text")
  .attr("class", "bar-label")
  .attr("text-anchor", "end")
  .attr("x", -8)
  .attr("y", d => y(d.label) + y.bandwidth() / 2)
  .attr("dy", "0.35em")
  .text(d => d.label);

g.selectAll(".bar-value").data(sorted).join("text")
  .attr("class", "bar-value")
  .attr("x", d => x(d.importance) + 6)
  .attr("y", d => y(d.label) + y.bandwidth() / 2)
  .attr("dy", "0.35em")
  .attr("opacity", 0)
  .text(d => (d.importance * 100).toFixed(1) + "%")
  .transition().duration(400).delay((d, i) => 800 + i * 40)
  .attr("opacity", 1);

// Mini legend — measured widths so nothing clips, shifted left into the chart area
const legendData = [
  { category: "terrain",     label: "Terrain" },
  { category: "access",      label: "Road access" },
  { category: "disturbance", label: "Disturbance proximity" },
  { category: "owner",       label: "Land ownership" },
  { category: "genus",       label: "Species composition" },
];
const ITEM_GAP = 18;
const legend = root.append("g")
  .attr("transform", `translate(0,${height - 18})`);
let xOff = 0;
legendData.forEach(d => {
  const grp = legend.append("g").attr("transform", `translate(${xOff},0)`);
  grp.append("rect").attr("width", 10).attr("height", 10).attr("y", -10).attr("fill", COLORS[d.category]);
  const text = grp.append("text").attr("x", 14).attr("y", 0)
    .attr("class", "bar-value").text(d.label);
  const w = text.node().getBBox().width;
  xOff += 14 + w + ITEM_GAP;
});

// Wire AUC into the page
const aucEl = document.getElementById("auc-headline");
if (aucEl) {
  const m = summary.v2;
  aucEl.textContent = `AUC = ${m.auc_mean.toFixed(2)} ± ${m.auc_std.toFixed(2)}`;
}
