// -----------------------------
// SVG references
// -----------------------------
const mapSvg = d3.select("#mapSvg");
const radialSvg = d3.select("#radialSvg");

const mapWidth = 800;
const mapHeight = 450;

const radialSize = 400;
const radialRadius = radialSize / 2 - 40;

// -----------------------------
// Scales
// -----------------------------
const colorScale = d3.scaleSequential(d3.interpolateBlues);

const AGE_ORDER = ["18-25", "26-35", "36-50", "50+"];
const AGE_COLORS = new Map([
  ["18-25", "#f97316"],
  ["26-35", "#22c55e"],
  ["36-50", "#a855f7"],
  ["50+", "#ef4444"],
]);

// -----------------------------
// Map projection
// -----------------------------
const projection = d3
  .geoNaturalEarth1()
  .scale(150)
  .translate([mapWidth / 2, mapHeight / 2]);

const path = d3.geoPath(projection);

// -----------------------------
// Load data
// -----------------------------
Promise.all([
  d3.json(
    "https://raw.githubusercontent.com/holtzy/D3-graph-gallery/master/DATA/world.geojson",
  ),
  d3.json("travel_choropleth.json"),
  d3.json("linked_radial_data.json"),
]).then(([world, choroplethData, radialData]) => {
  function normalizeIso(raw) {
    if (typeof raw !== "string") return null;
    const iso = raw.trim().toUpperCase();
    return /^[A-Z]{3}$/.test(iso) ? iso : null;
  }

  // -----------------------------
  // Lookups
  // -----------------------------
  const valueByIso = new Map(
    choroplethData.data.map((d) => [d.iso_alpha3, d.travel_intent_count]),
  );

  const nameToIso = new Map(
    choroplethData.data.map((d) => [d.country.toLowerCase(), d.iso_alpha3]),
  );

  const radialByIso = new Map((radialData ?? []).map((d) => [d.iso_alpha3, d]));

  const hasRadial = new Set(radialByIso.keys());

  const linkedChoropleth = choroplethData.data.filter((d) =>
    hasRadial.has(d.iso_alpha3),
  );
  const maxCount = d3.max(linkedChoropleth, (d) => d.travel_intent_count) ?? 0;
  colorScale.domain([0, Math.max(1, maxCount)]).clamp(true);

  function getIso(feature) {
    const byId = normalizeIso(feature?.id);
    if (byId) return byId;

    const byName = nameToIso.get(
      feature?.properties?.name?.toLowerCase?.() ?? "",
    );
    return normalizeIso(byName);
  }

  // -----------------------------
  // Draw map
  // -----------------------------
  mapSvg
    .append("rect")
    .attr("x", 0)
    .attr("y", 0)
    .attr("width", mapWidth)
    .attr("height", mapHeight)
    .attr("fill", "#f8fafc");

  mapSvg
    .append("g")
    .selectAll("path")
    .data(world.features)
    .join("path")
    .attr("d", path)
    .attr("fill", (d) => {
      const iso = getIso(d);
      if (!iso || !hasRadial.has(iso)) return "#ffffff";

      const v = valueByIso.get(iso);
      return v == null ? colorScale(0) : colorScale(v);
    })
    .attr("stroke", "#cbd5e1")
    .attr("stroke-width", 0.6)
    .style("cursor", (d) => (hasRadial.has(getIso(d)) ? "pointer" : "default"))
    .on("click", (event, d) => {
      const iso = getIso(d);
      if (!iso) return;

      const countryRadial = radialByIso.get(iso);
      if (countryRadial) {
        updateRadial(countryRadial);
        return;
      }

      // Country has no linked radial data; keep it white and show a clear message.
      updateRadial({ iso_alpha3: iso, age_groups: [] });
    });

  drawMapLegend(maxCount);

  // -----------------------------
  // Initial empty radial
  // -----------------------------
  updateRadial(null);

  // -----------------------------
  // Radial update
  // -----------------------------
  function updateRadial(countryData) {
    radialSvg.selectAll("*").remove();

    const g = radialSvg
      .append("g")
      .attr("transform", `translate(${radialSize / 2}, ${radialSize / 2})`);

    // Keep arcs and labels in separate layers so hover expansion never hides labels.
    const arcsG = g.append("g").attr("class", "radial-arcs");
    const labelsG = g.append("g").attr("class", "radial-labels");

    const centerLabel = radialSvg
      .append("text")
      .attr("x", radialSize / 2)
      .attr("y", radialSize - 10)
      .attr("text-anchor", "middle")
      .style("font-size", "14px")
      .style("font-weight", "500")
      .style("fill", "#111")
      .text(countryData ? "Hover an age group" : "Click a country on the map");

    if (!countryData) {
      d3.select("#radialTitle").text(
        "Click a country to view spending by age group",
      );
      return;
    }

    d3.select("#radialTitle").text(
      `Spend share by age group (${countryData.iso_alpha3})`,
    );

    const spendByAge = new Map(
      (countryData.age_groups ?? []).map((d) => [
        d.age_group,
        Number(d.avg_spend),
      ]),
    );

    const rows = AGE_ORDER.map((age) => ({
      age_group: age,
      avg_spend: spendByAge.get(age) ?? 0,
    })).filter((d) => Number.isFinite(d.avg_spend) && d.avg_spend > 0);

    if (rows.length === 0) {
      centerLabel.text("No spend data for this country");
      return;
    }

    const total = d3.sum(rows, (d) => d.avg_spend) || 1;
    const data = rows.map((d) => ({
      ...d,
      share: d.avg_spend / total,
    }));

    const pie = d3
      .pie()
      .sort(null)
      .value((d) => d.share)
      .padAngle(0);

    const arcs = pie(data);

    const innerR = 70;
    const outerR = radialRadius - 10;

    const arc = d3.arc().innerRadius(innerR).outerRadius(outerR);

    const arcHover = d3
      .arc()
      .innerRadius(innerR)
      .outerRadius(outerR + 18);

    arcsG
      .selectAll("path")
      .data(arcs)
      .join("path")
      .attr("fill", (d) => AGE_COLORS.get(d.data.age_group) ?? "#64748b")
      .attr("stroke", "#ffffff")
      .attr("stroke-width", 0)
      .attr("opacity", 0.95)
      .attr("d", arc)
      .on("mouseover", function (event, d) {
        d3.select(this)
          .raise()
          .transition()
          .duration(180)
          .attr("d", arcHover)
          .attr("opacity", 1);

        const pct = Math.round(d.data.share * 100);
        centerLabel.text(
          `${d.data.age_group}: $${Math.round(d.data.avg_spend)} (${pct}%)`,
        );
      })
      .on("mouseout", function () {
        d3.select(this)
          .transition()
          .duration(180)
          .attr("d", arc)
          .attr("opacity", 0.95);

        centerLabel.text("Hover an age group");
      });

    // Percentage labels (kept subtle, no gaps)
    labelsG
      .selectAll(".pct-label")
      .data(arcs)
      .join("text")
      .attr("class", "pct-label")
      .attr("text-anchor", "middle")
      .attr("alignment-baseline", "middle")
      .attr("transform", (d) => {
        const [x, y] = arc.centroid(d);
        return `translate(${x},${y})`;
      })
      .style("font-size", "11px")
      .style("font-weight", "600")
      .style("fill", "#0f172a")
      .style("paint-order", "stroke")
      .style("stroke", "rgba(255,255,255,0.85)")
      .style("stroke-width", 3)
      .style("stroke-linejoin", "round")
      .style("pointer-events", "none")
      .text((d) => `${Math.round(d.data.share * 100)}%`);
  }

  function drawMapLegend(maxValue) {
    mapSvg.selectAll(".map-legend").remove();

    const legendHeight = 140;
    const legendWidth = 14;

    // Place legend in bottom-left (mostly ocean) to avoid covering land.
    const x = 18;
    const y = mapHeight - legendHeight - 22;

    const legend = mapSvg
      .append("g")
      .attr("class", "map-legend")
      .attr("transform", `translate(${x},${y})`);

    // Background panel (keeps text readable without feeling like it "covers" the map)
    legend
      .append("rect")
      .attr("x", -10)
      .attr("y", -26)
      .attr("width", 160)
      .attr("height", legendHeight + 62)
      .attr("rx", 10)
      .attr("fill", "rgba(248,250,252,0.92)")
      .attr("stroke", "#e2e8f0")
      .attr("stroke-width", 1);

    legend
      .append("text")
      .attr("x", 0)
      .attr("y", -10)
      .style("font-size", "12px")
      .style("font-weight", "600")
      .style("fill", "#0f172a")
      .text("Travel intent count (linked)");

    const defs = mapSvg.append("defs");
    const gradientId = "choroplethLegendGradient";
    const gradient = defs
      .append("linearGradient")
      .attr("id", gradientId)
      .attr("x1", "0%")
      .attr("y1", "100%")
      .attr("x2", "0%")
      .attr("y2", "0%");

    gradient
      .append("stop")
      .attr("offset", "0%")
      .attr("stop-color", colorScale(0));

    gradient
      .append("stop")
      .attr("offset", "100%")
      .attr("stop-color", colorScale(maxValue || 1));

    legend
      .append("rect")
      .attr("x", 0)
      .attr("y", 0)
      .attr("width", legendWidth)
      .attr("height", legendHeight)
      .attr("fill", `url(#${gradientId})`)
      .attr("stroke", "#94a3b8")
      .attr("stroke-width", 0.8);

    const scale = d3
      .scaleLinear()
      .domain([0, maxValue || 1])
      .range([legendHeight, 0]);

    const axis = d3
      .axisRight(scale)
      .ticks(5)
      .tickSize(4)
      .tickPadding(6)
      .tickFormat(d3.format("~s"));

    legend
      .append("g")
      .attr("transform", `translate(${legendWidth},0)`)
      .call(axis)
      .call((g) =>
        g.selectAll("text").style("font-size", "11px").style("fill", "#334155"),
      )
      .call((g) => g.selectAll("path, line").style("stroke", "#94a3b8"));

    // No data swatch
    const noDataY = legendHeight + 14;
    legend
      .append("rect")
      .attr("x", 0)
      .attr("y", noDataY)
      .attr("width", 12)
      .attr("height", 12)
      .attr("fill", "#ffffff")
      .attr("stroke", "#94a3b8")
      .attr("stroke-width", 0.8);

    legend
      .append("text")
      .attr("x", 18)
      .attr("y", noDataY + 10)
      .style("font-size", "12px")
      .style("fill", "#334155")
      .text("No spend data (white)");
  }
});
