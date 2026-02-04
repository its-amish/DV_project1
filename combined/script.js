/* global d3 */

// -----------------------------
// Utilities
// -----------------------------
const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));

function showTooltip(el, html, x, y) {
  el.innerHTML = html;
  el.style.left = `${x}px`;
  el.style.top = `${y}px`;
  el.classList.add("visible");
}

function hideTooltip(el) {
  el.classList.remove("visible");
}

// -----------------------------
// Q1 — Sankey
// -----------------------------
async function renderQ1() {
  const container = document.querySelector("#q1-chart");
  const tooltip = document.querySelector("#q1-tooltip");
  if (!container) return;

  const rawData = await d3.json("data2.json");

  const margin = { top: 12, right: 120, bottom: 12, left: 120 };
  const width = 1040;
  const height = 520;

  const svg = d3
    .select(container)
    .append("svg")
    .attr("viewBox", `0 0 ${width} ${height}`)
    .attr("role", "img")
    .attr("aria-label", "Sankey diagram: purpose to transport to scope to budget");

  const g = svg
    .append("g")
    .attr("transform", `translate(${margin.left},${margin.top})`);

  const innerW = width - margin.left - margin.right;
  const innerH = height - margin.top - margin.bottom;

  const color = d3.scaleOrdinal(d3.schemeTableau10);

  // Dynamic mapping
  const nodesSet = new Set();
  const linkMap = new Map();

  rawData.forEach((d) => {
    nodesSet.add(d.purpose);
    nodesSet.add(d.transport);
    nodesSet.add(d.scope);
    nodesSet.add(d.budget);

    const flow = [
      `${d.purpose}|${d.transport}`,
      `${d.transport}|${d.scope}`,
      `${d.scope}|${d.budget}`,
    ];

    flow.forEach((k) => linkMap.set(k, (linkMap.get(k) || 0) + 1));
  });

  const nodes = Array.from(nodesSet).map((name) => ({ name }));
  const links = Array.from(linkMap).map(([k, v]) => {
    const [s, t] = k.split("|");
    return {
      source: nodes.findIndex((n) => n.name === s),
      target: nodes.findIndex((n) => n.name === t),
      value: v,
    };
  });

  const sankey = d3
    .sankey()
    .nodeWidth(26)
    .nodePadding(28)
    .extent([
      [0, 0],
      [innerW, innerH],
    ]);

  const graph = sankey({
    nodes: nodes.map((d) => ({ ...d })),
    links: links.map((d) => ({ ...d })),
  });

  const linkSel = g
    .append("g")
    .attr("fill", "none")
    .selectAll("path")
    .data(graph.links)
    .join("path")
    .attr("d", d3.sankeyLinkHorizontal())
    .attr("stroke", (d) => color(d.source.name))
    .attr("stroke-opacity", 0.18)
    .attr("stroke-width", (d) => Math.max(1, d.width))
    .style("cursor", "default")
    .on("mousemove", (event, d) => {
      const outPercent = d.source.value ? (d.value / d.source.value) * 100 : 0;
      const inPercent = d.target.value ? (d.value / d.target.value) * 100 : 0;

      const panel = document.querySelector("#q1-panel");
      const rect = panel?.getBoundingClientRect();
      const x = rect ? event.clientX - rect.left : event.offsetX;
      const y = rect ? event.clientY - rect.top : event.offsetY;

      showTooltip(
        tooltip,
        `<div style="font-weight:800; margin-bottom:6px;">${d.source.name} → ${d.target.name}</div>
         <div style="color: rgba(229,231,235,0.82);">Volume: <strong>${d.value}</strong></div>
         <div style="margin-top:6px; color: rgba(229,231,235,0.82);">
           <div>• ${outPercent.toFixed(1)}% of all <strong>${d.source.name}</strong> choices</div>
           <div>• ${inPercent.toFixed(1)}% of all <strong>${d.target.name}</strong> choices</div>
         </div>`,
        clamp(x + 18, 10, (panel?.clientWidth ?? 600) - 330),
        clamp(y + 18, 10, (panel?.clientHeight ?? 520) - 120),
      );
    })
    .on("mouseleave", () => hideTooltip(tooltip));

  const nodeSel = g
    .append("g")
    .selectAll("g")
    .data(graph.nodes)
    .join("g")
    .on("mouseenter", (event, d) => {
      const associated = new Set();
      const traverse = (n, direction) => {
        (n[direction] || []).forEach((l) => {
          associated.add(l);
          traverse(direction === "sourceLinks" ? l.target : l.source, direction);
        });
      };
      traverse(d, "sourceLinks");
      traverse(d, "targetLinks");

      linkSel
        .attr("stroke-opacity", (l) => (associated.has(l) ? 0.65 : 0.05))
        .attr("stroke", (l) => (associated.has(l) ? color(l.source.name) : "#94a3b8"));
    })
    .on("mouseleave", () => {
      linkSel
        .attr("stroke-opacity", 0.18)
        .attr("stroke", (d) => color(d.source.name));
    });

  nodeSel
    .append("rect")
    .attr("x", (d) => d.x0)
    .attr("y", (d) => d.y0)
    .attr("height", (d) => d.y1 - d.y0)
    .attr("width", (d) => d.x1 - d.x0)
    .attr("rx", 4)
    .attr("fill", (d) => color(d.name))
    .attr("stroke", "rgba(255,255,255,0.65)")
    .attr("stroke-width", 0.8);

  nodeSel
    .append("text")
    .attr("x", (d) => (d.x0 < innerW / 2 ? d.x1 + 10 : d.x0 - 10))
    .attr("y", (d) => (d.y1 + d.y0) / 2)
    .attr("dy", "0.35em")
    .attr("text-anchor", (d) => (d.x0 < innerW / 2 ? "start" : "end"))
    .style("font-size", "11px")
    .style("font-weight", 800)
    .style("fill", "rgba(229,231,235,0.92)")
    .text((d) => d.name);
}

// -----------------------------
// Q2 — Choropleth + radial
// -----------------------------
async function renderQ2() {
  const mapSvg = d3.select("#q2-map");
  const radialSvg = d3.select("#q2-radial");
  const titleEl = document.querySelector("#q2-radial-title");

  if (mapSvg.empty() || radialSvg.empty()) return;

  const [world, choroplethData, radialData] = await Promise.all([
    d3.json("world.geojson"),
    d3.json("travel_choropleth.json"),
    d3.json("linked_radial_data.json"),
  ]);

  const mapWidth = 800;
  const mapHeight = 450;

  const projection = d3
    .geoNaturalEarth1()
    .scale(150)
    .translate([mapWidth / 2, mapHeight / 2]);

  const path = d3.geoPath(projection);

  const colorScale = d3.scaleSequential(d3.interpolateBlues);

  const AGE_ORDER = ["18-25", "26-35", "36-50", "50+"];
  const AGE_COLORS = new Map([
    ["18-25", "#f97316"],
    ["26-35", "#22c55e"],
    ["36-50", "#a855f7"],
    ["50+", "#ef4444"],
  ]);

  const valueByIso = new Map(
    (choroplethData?.data ?? []).map((d) => [d.iso_alpha3, d.travel_intent_count]),
  );

  const nameToIso = new Map(
    (choroplethData?.data ?? []).map((d) => [d.country.toLowerCase(), d.iso_alpha3]),
  );

  const radialByIso = new Map((radialData ?? []).map((d) => [d.iso_alpha3, d]));
  const hasRadial = new Set(radialByIso.keys());

  const linkedChoropleth = (choroplethData?.data ?? []).filter((d) =>
    hasRadial.has(d.iso_alpha3),
  );

  const maxCount = d3.max(linkedChoropleth, (d) => d.travel_intent_count) ?? 0;
  colorScale.domain([0, Math.max(1, maxCount)]).clamp(true);

  function normalizeIso(raw) {
    if (typeof raw !== "string") return null;
    const iso = raw.trim().toUpperCase();
    return /^[A-Z]{3}$/.test(iso) ? iso : null;
  }

  function getIso(feature) {
    const byId = normalizeIso(feature?.id);
    if (byId) return byId;

    const byName = nameToIso.get(feature?.properties?.name?.toLowerCase?.() ?? "");
    return normalizeIso(byName);
  }

  // background
  mapSvg
    .append("rect")
    .attr("x", 0)
    .attr("y", 0)
    .attr("width", mapWidth)
    .attr("height", mapHeight)
    .attr("fill", "rgba(248,250,252,0.05)");

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
    .attr("stroke", "rgba(203, 213, 225, 0.55)")
    .attr("stroke-width", 0.6)
    .style("cursor", (d) => (hasRadial.has(getIso(d)) ? "pointer" : "default"))
    .on("click", (event, d) => {
      const iso = getIso(d);
      if (!iso) return;

      const countryRadial = radialByIso.get(iso);
      if (countryRadial) {
        updateRadial(countryRadial);
      } else {
        updateRadial({ iso_alpha3: iso, age_groups: [] });
      }
    });

  drawMapLegend(maxCount);
  updateRadial(null);

  function drawMapLegend(maxValue) {
    mapSvg.selectAll(".map-legend").remove();

    const legendHeight = 140;
    const legendWidth = 14;

    const x = 16;
    const y = mapHeight - legendHeight - 20;

    const legend = mapSvg
      .append("g")
      .attr("class", "map-legend")
      .attr("transform", `translate(${x},${y})`);

    legend
      .append("rect")
      .attr("x", -10)
      .attr("y", -26)
      .attr("width", 170)
      .attr("height", legendHeight + 62)
      .attr("rx", 12)
      .attr("fill", "rgba(2,6,23,0.55)")
      .attr("stroke", "rgba(148,163,184,0.30)")
      .attr("stroke-width", 1);

    legend
      .append("text")
      .attr("x", 0)
      .attr("y", -10)
      .style("font-size", "12px")
      .style("font-weight", "700")
      .style("fill", "rgba(229,231,235,0.92)")
      .text("Travel intent count");

    const defs = mapSvg.append("defs");
    const gradientId = "choroplethLegendGradient";

    const gradient = defs
      .append("linearGradient")
      .attr("id", gradientId)
      .attr("x1", "0%")
      .attr("y1", "100%")
      .attr("x2", "0%")
      .attr("y2", "0%");

    gradient.append("stop").attr("offset", "0%").attr("stop-color", colorScale(0));
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
      .attr("stroke", "rgba(148,163,184,0.65)")
      .attr("stroke-width", 0.8);

    const scale = d3
      .scaleLinear()
      .domain([0, maxValue || 1])
      .range([legendHeight, 0]);

    legend
      .append("g")
      .attr("transform", `translate(${legendWidth},0)`)
      .call(
        d3
          .axisRight(scale)
          .ticks(5)
          .tickSize(4)
          .tickPadding(6)
          .tickFormat(d3.format("~s")),
      )
      .call((g) =>
        g
          .selectAll("text")
          .style("font-size", "11px")
          .style("fill", "rgba(229,231,235,0.86)"),
      )
      .call((g) => g.selectAll("path, line").style("stroke", "rgba(148,163,184,0.65)"));

    const noDataY = legendHeight + 14;
    legend
      .append("rect")
      .attr("x", 0)
      .attr("y", noDataY)
      .attr("width", 12)
      .attr("height", 12)
      .attr("fill", "#ffffff")
      .attr("stroke", "rgba(148,163,184,0.65)")
      .attr("stroke-width", 0.8);

    legend
      .append("text")
      .attr("x", 18)
      .attr("y", noDataY + 10)
      .style("font-size", "12px")
      .style("fill", "rgba(229,231,235,0.86)")
      .text("No spend data");
  }

  function updateRadial(countryData) {
    radialSvg.selectAll("*").remove();

    const radialSize = 420;
    const radialRadius = radialSize / 2 - 34;

    const g = radialSvg
      .append("g")
      .attr("transform", `translate(${radialSize / 2}, ${radialSize / 2})`);

    const arcsG = g.append("g").attr("class", "radial-arcs");
    const labelsG = g.append("g").attr("class", "radial-labels");

    const centerLabel = radialSvg
      .append("text")
      .attr("x", radialSize / 2)
      .attr("y", radialSize - 12)
      .attr("text-anchor", "middle")
      .style("font-size", "13px")
      .style("font-weight", "700")
      .style("fill", "rgba(229,231,235,0.92)")
      .text(countryData ? "Hover an age group" : "Click a country on the map");

    if (!countryData) {
      if (titleEl) titleEl.textContent = "Click a country to view spending by age group";
      return;
    }

    if (titleEl) titleEl.textContent = `Spend share by age group (${countryData.iso_alpha3})`;

    const spendByAge = new Map(
      (countryData.age_groups ?? []).map((d) => [d.age_group, Number(d.avg_spend)]),
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
    const data = rows.map((d) => ({ ...d, share: d.avg_spend / total }));

    const pie = d3.pie().sort(null).value((d) => d.share);
    const arcs = pie(data);

    const innerR = 78;
    const outerR = radialRadius;

    const arc = d3.arc().innerRadius(innerR).outerRadius(outerR);
    const arcHover = d3.arc().innerRadius(innerR).outerRadius(outerR + 16);

    arcsG
      .selectAll("path")
      .data(arcs)
      .join("path")
      .attr("fill", (d) => AGE_COLORS.get(d.data.age_group) ?? "#64748b")
      .attr("stroke", "rgba(255,255,255,0.70)")
      .attr("stroke-width", 0.6)
      .attr("opacity", 0.95)
      .attr("d", arc)
      .on("mouseover", function (event, d) {
        d3.select(this).raise().transition().duration(160).attr("d", arcHover).attr("opacity", 1);
        const pct = Math.round(d.data.share * 100);
        centerLabel.text(`${d.data.age_group}: $${Math.round(d.data.avg_spend)} (${pct}%)`);
      })
      .on("mouseout", function () {
        d3.select(this).transition().duration(160).attr("d", arc).attr("opacity", 0.95);
        centerLabel.text("Hover an age group");
      });

    labelsG
      .selectAll("text")
      .data(arcs)
      .join("text")
      .attr("text-anchor", "middle")
      .attr("alignment-baseline", "middle")
      .attr("transform", (d) => {
        const [x, y] = arc.centroid(d);
        return `translate(${x},${y})`;
      })
      .style("font-size", "11px")
      .style("font-weight", "800")
      .style("fill", "rgba(2,6,23,0.85)")
      .style("paint-order", "stroke")
      .style("stroke", "rgba(255,255,255,0.90)")
      .style("stroke-width", 3)
      .style("stroke-linejoin", "round")
      .text((d) => `${Math.round(d.data.share * 100)}%`);
  }
}

// -----------------------------
// Q3 — Zoomable Sunburst
// -----------------------------
async function renderQ3() {
  const chartEl = document.querySelector("#q3-chart");
  const legendEl = document.querySelector("#q3-legend");
  const tooltip = document.querySelector("#q3-tooltip");

  if (!chartEl || !legendEl) return;

  const WIDTH = 720;
  const RADIUS = WIDTH / 2;

  const SEASONS = ["Spring", "Summer", "Autumn", "Winter"];
  const seasonColor = d3.scaleOrdinal().domain(SEASONS).range([
    "#14b8a6",
    "#fbbf24",
    "#fb7185",
    "#6366f1",
  ]);

  const PLACE_TYPES = ["City", "Mountain", "Cultural", "Beach", "Other"];
  const placeTypeColor = d3.scaleOrdinal().domain(PLACE_TYPES).range([
    "#7c3aed",
    "#16a34a",
    "#0ea5e9",
    "#f59e0b",
    "#94a3b8",
  ]);

  const ACTIVITIES = ["Adventure", "Leisure", "Cultural", "General", "Other"];
  const activityColor = d3.scaleOrdinal().domain(ACTIVITIES).range([
    "#ef4444",
    "#3b82f6",
    "#06b6d4",
    "#64748b",
    "#94a3b8",
  ]);

  function nodeFill(node) {
    if (node.depth === 1) return seasonColor(node.data.name) ?? "#94a3b8";
    if (node.depth === 2) return placeTypeColor(node.data.name) ?? "#94a3b8";
    if (node.depth === 3) return activityColor(node.data.name) ?? "#94a3b8";
    return "#94a3b8";
  }

  function renderLegend() {
    const root = d3.select(legendEl);
    root.html("");

    const block = root
      .append("div")
      .style("border", "1px solid rgba(148,163,184,0.20)")
      .style("border-radius", "14px")
      .style("background", "rgba(2,6,23,0.35)")
      .style("padding", "12px 12px")
      .style("margin", "0 0 8px");

    block
      .append("div")
      .style("font-size", "13px")
      .style("font-weight", "800")
      .style("margin-bottom", "10px")
      .style("color", "rgba(229,231,235,0.92)")
      .text("Legend (colors reset per ring)");

    const sections = [
      {
        title: "Inner ring — Season",
        items: SEASONS.map((name) => ({ name, color: seasonColor(name) })),
      },
      {
        title: "Middle ring — Place type",
        items: ["City", "Mountain", "Cultural", "Beach", "Other"].map((name) => ({
          name,
          color: placeTypeColor(name),
        })),
      },
      {
        title: "Outer ring — Activity preference",
        items: ["Adventure", "Leisure", "Cultural", "General"].map((name) => ({
          name,
          color: activityColor(name),
        })),
      },
    ];

    sections.forEach((sec) => {
      const s = block.append("div").style("margin", "10px 0 0");
      s.append("div")
        .style("font-size", "12px")
        .style("font-weight", "800")
        .style("letter-spacing", "0.06em")
        .style("text-transform", "uppercase")
        .style("color", "rgba(229,231,235,0.70)")
        .text(sec.title);

      const row = s
        .selectAll("div.item")
        .data(sec.items)
        .join("div")
        .style("display", "flex")
        .style("gap", "8px")
        .style("align-items", "center")
        .style("margin", "6px 0")
        .style("font-size", "13px")
        .style("color", "rgba(229,231,235,0.88)");

      row
        .append("span")
        .style("width", "14px")
        .style("height", "14px")
        .style("border-radius", "4px")
        .style("border", "1px solid rgba(148,163,184,0.25)")
        .style("background", (d) => d.color);

      row.append("span").text((d) => d.name);
    });

    root
      .append("div")
      .style("font-size", "12px")
      .style("color", "rgba(229,231,235,0.70)")
      .style("margin-top", "10px")
      .text("Tip: hover a segment to see full path + shares; click to zoom.");
  }

  const format = d3.format(",d");

  const data = await d3.json("seasonal_sunburst.json");

  const root = d3
    .hierarchy(data)
    .sum((d) => d.value)
    .sort((a, b) => b.value - a.value);

  d3.partition().size([2 * Math.PI, RADIUS])(root);
  root.each((d) => (d.current = d));

  const arcGen = d3
    .arc()
    .startAngle((d) => d.x0)
    .endAngle((d) => d.x1)
    .padAngle((d) => Math.min(0.004, (d.x1 - d.x0) / 2))
    .padRadius(RADIUS / 2)
    .innerRadius((d) => d.y0)
    .outerRadius((d) => Math.max(d.y0 + 1, d.y1 - 1));

  const arcHoverGen = d3
    .arc()
    .startAngle((d) => d.x0)
    .endAngle((d) => d.x1)
    .padAngle((d) => Math.min(0.004, (d.x1 - d.x0) / 2))
    .padRadius(RADIUS / 2)
    .innerRadius((d) => Math.max(0, d.y0 - 2))
    .outerRadius((d) => Math.max(d.y0 + 1, d.y1 + 10));

  const svg = d3
    .select(chartEl)
    .append("svg")
    .attr("viewBox", [0, 0, WIDTH, WIDTH]);

  const g = svg.append("g").attr("transform", `translate(${RADIUS},${RADIUS})`);

  const centerG = g.append("g");
  const centerTitle = centerG
    .append("text")
    .attr("text-anchor", "middle")
    .attr("dy", "-0.1em")
    .style("font-size", "14px")
    .style("font-weight", "900")
    .style("fill", "rgba(229,231,235,0.92)")
    .text("Travel Preferences");

  const centerSub = centerG
    .append("text")
    .attr("text-anchor", "middle")
    .attr("dy", "1.35em")
    .style("font-size", "12px")
    .style("font-weight", "700")
    .style("fill", "rgba(229,231,235,0.65)")
    .text("Hover or click a segment");

  const pathsG = g.append("g").attr("class", "paths");

  const pathSel = pathsG
    .selectAll("path")
    .data(root.descendants().slice(1))
    .join("path")
    .attr("fill", (d) => nodeFill(d))
    .attr("fill-opacity", (d) => (arcVisible(d.current) ? 0.92 : 0))
    .attr("stroke", "rgba(255,255,255,0.75)")
    .attr("stroke-width", 0.6)
    .attr("cursor", "pointer")
    .attr("d", (d) => arcGen(d.current))
    .on("mousemove", (event, d) => {
      const totalPct = root.value ? (100 * d.value) / root.value : 0;
      const parentPct = d.parent?.value ? (100 * d.value) / d.parent.value : 100;

      const pathNames = d
        .ancestors()
        .reverse()
        .map((n) => n.data.name)
        .join(" → ");

      const ancestorSet = new Set(d.ancestors());
      pathSel.attr("fill-opacity", (p) => {
        if (!arcVisible(p.current)) return 0;
        return ancestorSet.has(p) ? 1 : 0.16;
      });

      d3.select(event.currentTarget)
        .raise()
        .attr("stroke", "rgba(2,6,23,0.75)")
        .attr("stroke-width", 0.9)
        .attr("d", arcHoverGen(d.current));

      centerTitle.text(d.data.name);
      centerSub.text(`${format(d.value)} • ${totalPct.toFixed(1)}% of total`);

      const panel = document.querySelector("#q3-panel");
      const rect = panel?.getBoundingClientRect();
      const x = rect ? event.clientX - rect.left : event.offsetX;
      const y = rect ? event.clientY - rect.top : event.offsetY;

      showTooltip(
        tooltip,
        `<div style="font-weight:900; margin-bottom:6px;">${pathNames}</div>
         <div style="color: rgba(229,231,235,0.80);">Count: <strong>${format(d.value)}</strong></div>
         <div style="margin-top:6px; color: rgba(229,231,235,0.76);">
           <div>Share of total: <strong>${totalPct.toFixed(1)}%</strong></div>
           <div>Share of parent: <strong>${parentPct.toFixed(1)}%</strong></div>
         </div>`,
        clamp(x + 14, 10, (panel?.clientWidth ?? 600) - 330),
        clamp(y + 14, 10, (panel?.clientHeight ?? 600) - 120),
      );
    })
    .on("mouseleave", (event, d) => {
      hideTooltip(tooltip);
      pathSel.attr("fill-opacity", (p) => (arcVisible(p.current) ? 0.92 : 0));
      d3.select(event.currentTarget)
        .attr("stroke", "rgba(255,255,255,0.75)")
        .attr("stroke-width", 0.6)
        .attr("d", arcGen(d.current));

      centerTitle.text("Travel Preferences");
      centerSub.text("Hover or click a segment");
    })
    .on("click", clicked);

  const holeR = Math.max(36, root.children?.[0]?.y0 ? root.children[0].y0 - 4 : RADIUS / 4);

  const parentCircle = g
    .append("circle")
    .datum(root)
    .attr("r", holeR)
    .attr("fill", "rgba(2,6,23,0.40)")
    .attr("stroke", "rgba(148,163,184,0.35)")
    .attr("stroke-width", 1)
    .attr("pointer-events", "all")
    .on("click", clicked);

  centerG.raise();
  renderLegend();

  function clicked(event, p) {
    root.each((d) =>
      (d.target = {
        x0:
          Math.max(0, Math.min(1, (d.x0 - p.x0) / (p.x1 - p.x0))) * 2 * Math.PI,
        x1:
          Math.max(0, Math.min(1, (d.x1 - p.x0) / (p.x1 - p.x0))) * 2 * Math.PI,
        y0: Math.max(0, d.y0 - p.y0),
        y1: Math.max(0, d.y1 - p.y0),
      }),
    );

    const t = g.transition().duration(750).ease(d3.easeCubicInOut);

    pathSel
      .transition(t)
      .tween("data", (d) => {
        const i = d3.interpolate(d.current, d.target);
        return (tt) => (d.current = i(tt));
      })
      .attr("fill-opacity", (d) => (arcVisible(d.target) ? 0.92 : 0))
      .attrTween("d", (d) => () => arcGen(d.current));

    const isRoot = p === root;
    centerTitle.text(isRoot ? "Travel Preferences" : p.data.name);
    centerSub.text(isRoot ? "Hover or click a segment" : "Click center to zoom out");

    hideTooltip(tooltip);
  }

  function arcVisible(d) {
    return d.y1 <= RADIUS && d.y0 >= 0 && d.x1 > d.x0;
  }
}

// -----------------------------
// Q4 — Stacked bars (toggle metric)
// -----------------------------
async function renderQ4() {
  const container = document.querySelector("#q4-chart");
  const tooltip = document.querySelector("#q4-tooltip");

  const btnComp = document.querySelector("#q4-btn-comp");
  const btnPrep = document.querySelector("#q4-btn-prep");

  if (!container || !btnComp || !btnPrep) return;

  const rawData = await d3.json("travel_data_complete.json");

  const priorities = ["Activities", "Accommodation", "Transport", "Dining"];

  const rolled = d3.rollup(
    rawData,
    (v) => ({
      avgComplexity: d3.mean(v, (d) => d.complexity),
      avgPrep: d3.mean(v, (d) => d.prepDays),
      dist: Object.fromEntries(
        priorities.map((p) => [p, v.filter((d) => d.priority === p).length / v.length]),
      ),
    }),
    (d) => d.purpose,
  );

  const data = Array.from(rolled, ([purpose, val]) => ({ purpose, ...val }));

  const margin = { top: 34, right: 170, bottom: 70, left: 70 };
  const width = 1040;
  const height = 520;

  const svg = d3
    .select(container)
    .append("svg")
    .attr("viewBox", `0 0 ${width} ${height}`);

  const g = svg.append("g").attr("transform", `translate(${margin.left},${margin.top})`);

  const innerW = width - margin.left - margin.right;
  const innerH = height - margin.top - margin.bottom;

  const x = d3.scaleBand().domain(data.map((d) => d.purpose)).range([0, innerW]).padding(0.36);
  const y = d3.scaleLinear().range([innerH, 0]);

  const color = d3.scaleOrdinal().domain(priorities).range(d3.schemeTableau10);

  const yAxis = g.append("g");
  const xAxis = g
    .append("g")
    .attr("transform", `translate(0,${innerH})`)
    .call(d3.axisBottom(x))
    .call((gg) =>
      gg
        .selectAll("text")
        .style("fill", "rgba(229,231,235,0.78)")
        .style("font-size", "11px")
        .attr("transform", "rotate(-8)")
        .style("text-anchor", "end"),
    )
    .call((gg) => gg.selectAll("path,line").style("stroke", "rgba(148,163,184,0.35)"));

  const yLabel = g
    .append("text")
    .attr("transform", "rotate(-90)")
    .attr("y", -margin.left + 18)
    .attr("x", -innerH / 2)
    .attr("text-anchor", "middle")
    .style("font-size", "12px")
    .style("font-weight", "800")
    .style("fill", "rgba(229,231,235,0.72)");

  g
    .append("text")
    .attr("x", innerW / 2)
    .attr("y", innerH + 52)
    .attr("text-anchor", "middle")
    .style("font-size", "12px")
    .style("font-weight", "800")
    .style("fill", "rgba(229,231,235,0.72)")
    .text("Travel Purpose");

  const legend = g.append("g").attr("transform", `translate(${innerW + 22}, 0)`);
  priorities.forEach((p, i) => {
    const row = legend.append("g").attr("transform", `translate(0, ${i * 24})`);
    row
      .append("rect")
      .attr("width", 14)
      .attr("height", 14)
      .attr("rx", 3)
      .attr("fill", color(p));
    row
      .append("text")
      .attr("x", 20)
      .attr("y", 12)
      .style("font-size", "12px")
      .style("font-weight", "800")
      .style("fill", "rgba(229,231,235,0.78)")
      .text(p);
  });

  function draw(metric) {
    const isComplexity = metric === "avgComplexity";
    yLabel.text(isComplexity ? "Planning Complexity" : "Avg Preparation Days");

    y.domain([0, d3.max(data, (d) => d[metric]) ?? 0]).nice();

    yAxis
      .transition()
      .duration(600)
      .call(d3.axisLeft(y).ticks(6))
      .call((gg) => gg.selectAll("text").style("fill", "rgba(229,231,235,0.78)").style("font-size", "11px"))
      .call((gg) => gg.selectAll("path,line").style("stroke", "rgba(148,163,184,0.35)"));

    const stack = d3
      .stack()
      .keys(priorities)
      .value((d, k) => (d.dist[k] ?? 0) * (d[metric] ?? 0))(data);

    const layers = g.selectAll(".layer").data(stack, (d) => d.key);

    const layersEnter = layers
      .enter()
      .append("g")
      .attr("class", "layer")
      .attr("fill", (d) => color(d.key));

    const layersMerged = layersEnter.merge(layers);

    const rects = layersMerged.selectAll("rect").data((d) => d, (d) => d.data.purpose);

    rects
      .enter()
      .append("rect")
      .attr("x", (d) => x(d.data.purpose))
      .attr("width", x.bandwidth())
      .attr("y", innerH)
      .attr("height", 0)
      .attr("rx", 3)
      .attr("stroke", "rgba(255,255,255,0.15)")
      .attr("stroke-width", 0.6)
      .merge(rects)
      .on("mousemove", function (event, d) {
        const intentName = d3.select(this.parentNode).datum().key;
        const pct = ((d.data.dist[intentName] ?? 0) * 100).toFixed(0);

        const panel = document.querySelector("#q4-panel");
        const rect = panel?.getBoundingClientRect();
        const xPos = rect ? event.clientX - rect.left : event.offsetX;
        const yPos = rect ? event.clientY - rect.top : event.offsetY;

        showTooltip(
          tooltip,
          `<div style="font-size:11px; letter-spacing:0.08em; text-transform:uppercase; color: rgba(229,231,235,0.70); font-weight:900;">${intentName}</div>
           <div style="font-size:16px; font-weight:900; margin-top:4px;">${pct}%</div>
           <div style="margin-top:6px; color: rgba(229,231,235,0.78);">Purpose: <strong>${d.data.purpose}</strong></div>`,
          clamp(xPos + 14, 10, (panel?.clientWidth ?? 600) - 260),
          clamp(yPos + 14, 10, (panel?.clientHeight ?? 520) - 120),
        );

        d3.select(this).attr("opacity", 0.88);
      })
      .on("mouseleave", function () {
        hideTooltip(tooltip);
        d3.select(this).attr("opacity", 1);
      })
      .transition()
      .duration(600)
      .attr("x", (d) => x(d.data.purpose))
      .attr("width", x.bandwidth())
      .attr("y", (d) => y(d[1]))
      .attr("height", (d) => y(d[0]) - y(d[1]));

    rects.exit().remove();
    layers.exit().remove();
  }

  function setActive(active) {
    btnComp.classList.toggle("active", active === "comp");
    btnPrep.classList.toggle("active", active === "prep");
  }

  btnComp.addEventListener("click", () => {
    setActive("comp");
    draw("avgComplexity");
  });

  btnPrep.addEventListener("click", () => {
    setActive("prep");
    draw("avgPrep");
  });

  setActive("comp");
  draw("avgComplexity");
}

// -----------------------------
// Boot
// -----------------------------
(async function main() {
  try {
    await renderQ1();
    await renderQ2();
    await renderQ3();
    await renderQ4();
  } catch (err) {
    // Fail softly: show an error banner at top of page.
    // (Useful if JSON is opened without a local server.)
    console.error(err);
    const hero = document.querySelector(".hero");
    if (hero) {
      const div = document.createElement("div");
      div.style.marginTop = "12px";
      div.style.padding = "10px 12px";
      div.style.borderRadius = "12px";
      div.style.border = "1px solid rgba(239,68,68,0.45)";
      div.style.background = "rgba(239,68,68,0.10)";
      div.style.color = "rgba(229,231,235,0.92)";
      div.innerHTML =
        "<strong>Data load error.</strong> Open this page using a local server (Live Server / <code>python -m http.server</code>) so JSON files can be fetched.";
      hero.appendChild(div);
    }
  }
})();
