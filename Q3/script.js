const WIDTH = 700;
const RADIUS = WIDTH / 2;

const SEASONS = ["Spring", "Summer", "Autumn", "Winter"];
const seasonColor = d3.scaleOrdinal().domain(SEASONS).range([
  "#14b8a6", // Spring: teal
  "#fbbf24", // Summer: golden
  "#fb7185", // Autumn: rose
  "#6366f1", // Winter: indigo
]);

// Middle ring: place types (explicit 4-color scheme + neutral for Other)
const PLACE_TYPES = ["City", "Mountain", "Cultural", "Beach", "Other"];
const placeTypeColor = d3.scaleOrdinal().domain(PLACE_TYPES).range([
  "#7c3aed", // City: violet
  "#16a34a", // Mountain: green
  "#0ea5e9", // Cultural: sky
  "#f59e0b", // Beach: amber/sand
  "#94a3b8", // Other: slate
]);

// Outer ring: activity preference
const ACTIVITIES = ["Adventure", "Leisure", "Cultural", "General", "Other"];
const activityColor = d3.scaleOrdinal().domain(ACTIVITIES).range([
  "#ef4444", // Adventure: red
  "#3b82f6", // Leisure: blue
  "#06b6d4", // Cultural: cyan
  "#64748b", // General: slate
  "#94a3b8", // Other: light slate
]);

function topSeason(node) {
  let p = node;
  while (p.depth > 1) p = p.parent;
  return p?.data?.name;
}

function nodeFill(node) {
  // Use separate palettes per ring for clarity.
  if (node.depth === 1) return seasonColor(node.data.name) ?? "#94a3b8";
  if (node.depth === 2) return placeTypeColor(node.data.name) ?? "#94a3b8";
  if (node.depth === 3) return activityColor(node.data.name) ?? "#94a3b8";
  return "#94a3b8";
}

function renderLegend() {
  const legend = d3.select("#legend");
  if (legend.empty()) return;

  legend.html("");
  legend
    .append("div")
    .attr("class", "legend-title")
    .text("Legend (colors reset per ring)");

  const sections = [
    {
      title: "Inner ring — Season",
      items: SEASONS.map((name) => ({ name, color: seasonColor(name) })),
    },
    {
      title: "Middle ring — Place type",
      // Requested logical order: City → Mountain → Cultural → Beach
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

  const section = legend
    .selectAll("div.legend-section")
    .data(sections)
    .join("div")
    .attr("class", "legend-section");

  section.append("h3").text((d) => d.title);

  const items = section
    .selectAll("div.legend-item")
    .data((d) => d.items)
    .join("div")
    .attr("class", "legend-item");

  items
    .append("span")
    .attr("class", "legend-swatch")
    .style("background", (d) => d.color ?? "#94a3b8");

  items.append("span").text((d) => d.name);

  legend
    .append("div")
    .attr("class", "legend-note")
    .text(
      "Tip: hover a segment to see the full path (Season → Place → Activity) and counts in the tooltip.",
    );
}

const format = d3.format(",d");
const tooltip = d3.select("#tooltip");

d3.json("seasonal_sunburst.json").then((data) => {
  const root = d3
    .hierarchy(data)
    .sum((d) => d.value)
    .sort((a, b) => b.value - a.value);

  const partition = d3.partition().size([2 * Math.PI, RADIUS]);

  partition(root);

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
    .select("#chart")
    .append("svg")
    .attr("viewBox", [0, 0, WIDTH, WIDTH]);

  const g = svg.append("g").attr("transform", `translate(${RADIUS},${RADIUS})`);

  const centerG = g.append("g");
  const centerTitle = centerG
    .append("text")
    .attr("text-anchor", "middle")
    .attr("dy", "-0.1em")
    .style("font-size", "14px")
    .style("font-weight", "700")
    .style("fill", "#0f172a")
    .text("Travel Preferences");

  const centerSub = centerG
    .append("text")
    .attr("text-anchor", "middle")
    .attr("dy", "1.25em")
    .style("font-size", "12px")
    .style("font-weight", "600")
    .style("fill", "#64748b")
    .text("Hover or click a segment");

  const pathsG = g.append("g").attr("class", "paths");

  const path = pathsG
    .selectAll("path")
    .data(root.descendants().slice(1))
    .join("path")
    .attr("fill", (d) => nodeFill(d))
    .attr("fill-opacity", (d) => (arcVisible(d.current) ? 0.9 : 0))
    .attr("stroke", "rgba(255,255,255,0.85)")
    .attr("stroke-width", 1)
    .attr("cursor", "pointer")
    .attr("d", (d) => arcGen(d.current))
    .on("mouseover", (event, d) => {
      const totalPct = root.value ? (100 * d.value) / root.value : 0;
      const parentPct = d.parent?.value
        ? (100 * d.value) / d.parent.value
        : 100;

      const pathNames = d
        .ancestors()
        .reverse()
        .map((n) => n.data.name)
        .join(" → ");

      // Highlight ancestors and fade others.
      const ancestorSet = new Set(d.ancestors());
      path.attr("fill-opacity", (p) => {
        if (!arcVisible(p.current)) return 0;
        return ancestorSet.has(p) ? 1 : 0.14;
      });

      d3.select(event.currentTarget)
        .raise()
        .attr("stroke", "rgba(15,23,42,0.28)")
        .attr("stroke-width", 1.2)
        .attr("d", arcHoverGen(d.current));

      centerTitle.text(d.data.name);
      centerSub.text(`${format(d.value)} • ${totalPct.toFixed(1)}% of total`);

      tooltip.style("opacity", 1).html(`
          <div class="path">${pathNames}</div>
          <div class="meta">
            <div><strong>Count:</strong> ${format(d.value)}</div>
            <div><strong>Share of total:</strong> ${totalPct.toFixed(1)}%</div>
            <div><strong>Share of parent:</strong> ${parentPct.toFixed(1)}%</div>
          </div>
        `);
    })
    .on("mousemove", (event) => {
      tooltip
        .style("left", event.pageX + 10 + "px")
        .style("top", event.pageY + 10 + "px");
    })
    .on("mouseout", (event, d) => {
      tooltip.style("opacity", 0);

      // Restore default opacity.
      path.attr("fill-opacity", (p) => (arcVisible(p.current) ? 0.9 : 0));

      d3.select(event.currentTarget)
        .attr("stroke", "rgba(255,255,255,0.85)")
        .attr("stroke-width", 1)
        .attr("d", arcGen(d.current));

      centerTitle.text("Travel Preferences");
      centerSub.text("Hover or click a segment");
    })
    .on("click", clicked);

  // No arc labels (keeps the chart clean and consistent).

  const parentCircle = g
    .append("circle")
    .datum(root)
    // Match the actual inner hole radius so it doesn't cover the inner ring.
    .attr(
      "r",
      Math.max(
        34,
        root.children?.[0]?.y0 ? root.children[0].y0 - 3 : RADIUS / 4,
      ),
    )
    .attr("fill", "rgba(255,255,255,0.84)")
    .attr("stroke", "rgba(148,163,184,0.55)")
    .attr("stroke-width", 1)
    .attr("pointer-events", "all")
    .on("click", clicked);

  // Ensure the center text stays visible above the clickable circle.
  centerG.raise();

  function clicked(event, p) {
    root.each(
      (d) =>
        (d.target = {
          x0:
            Math.max(0, Math.min(1, (d.x0 - p.x0) / (p.x1 - p.x0))) *
            2 *
            Math.PI,
          x1:
            Math.max(0, Math.min(1, (d.x1 - p.x0) / (p.x1 - p.x0))) *
            2 *
            Math.PI,
          y0: Math.max(0, d.y0 - p.y0),
          y1: Math.max(0, d.y1 - p.y0),
        }),
    );

    const t = g.transition().duration(750).ease(d3.easeCubicInOut);

    path
      .transition(t)
      .tween("data", (d) => {
        const i = d3.interpolate(d.current, d.target);
        return (t) => (d.current = i(t));
      })
      .attr("fill-opacity", (d) => (arcVisible(d.target) ? 0.9 : 0))
      .attrTween("d", (d) => () => arcGen(d.current));

    // Update center helper text for the focused node.
    const isRoot = p === root;
    centerTitle.text(isRoot ? "Travel Preferences" : p.data.name);
    centerSub.text(
      isRoot ? "Hover or click a segment" : "Click center to zoom out",
    );
  }

  function arcVisible(d) {
    return d.y1 <= RADIUS && d.y0 >= 0 && d.x1 > d.x0;
  }

  renderLegend();
});
