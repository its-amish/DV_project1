# DV Project 1 — Travel Intent Visualizations (Q1–Q4)

This folder contains four D3-based visualizations (Q1–Q4). Each answers a different analytical question about travel intent and planning behavior.

## How to run

Open the corresponding HTML file in a browser (best via a local server so JSON loads correctly).

- Option 1 (VS Code): use a Live Server extension and open the HTML.
- Option 2 (Python): run `python -m http.server` from the DV_project1 folder and open the shown localhost URL.

---

## Q1 — Travel decision flow (Sankey)

**Visualization**: Sankey diagram showing how choices flow through: Purpose → Transport → Scope → Budget.

**Question this visualization answers**

- What are the most common travel “paths” from trip purpose to transport mode to domestic/abroad scope to budget tier?
- Where do users “converge” (dominant nodes) and what transitions are strongest (dominant links)?

**Marks & channels used**

- **Marks**: rectangular nodes; curved link paths between nodes.
- **Position (layout)**: Sankey layout places stages left→right (Purpose, Transport, Scope, Budget); nodes are vertically arranged by flow.
- **Size**:
  - Node height encodes total volume through that category.
  - Link thickness encodes the number of records/prompts flowing between two categories.
- **Color**: link + node colors use an ordinal palette (Tableau scheme) primarily to differentiate categories (source-based styling for links).
- **Text**: node labels annotate categories.

**Use case (user-story relevance)**

- Travel product/analytics teams can identify the dominant decision funnels (e.g., “Vacation → Flight → Abroad → Luxury”) to:
  - prioritize inventory/partnerships (airlines vs rail/bus, domestic vs abroad packages),
  - design recommendation rules, and
  - detect smaller but important segments (e.g., emergency travel patterns).

**Interaction**

- Hover link: tooltip shows absolute volume and % share relative to source and target totals.
- Hover node: highlights (activates) connected paths and fades unrelated links to isolate the full upstream/downstream flow.

Files

- [Q1/index.html](Q1/index.html)
- [Q1/data2.json](Q1/data2.json)

---

## Q2 — Global travel intent + spending by age (Linked choropleth + radial)

**Visualization**: A linked view combining:

1. a world choropleth map of travel intent counts, and
2. a radial (donut/pie) chart for spending share by age group for the selected country.

**Question this visualization answers**

- Which countries show higher travel intent (relative counts) in the dataset?
- For a selected country, how is spending distributed across age groups (18–25, 26–35, 36–50, 50+)?

**Marks & channels used**

- **Map (choropleth)**
  - **Marks**: country polygons (paths).
  - **Color (sequential)**: fill intensity (Blues) encodes travel intent count for countries that have linked radial data.
  - **Special color**: white indicates “no linked spend data”.
  - **Position**: geographic projection (Natural Earth) encodes latitude/longitude.
- **Radial chart (donut/pie)**
  - **Marks**: arc segments.
  - **Angle**: arc angle encodes share of total average spend for that country (normalized to 100%).
  - **Color (categorical)**: distinct colors map age groups.
  - **Text**: subtle in-arc % labels; center label shows exact values on hover.

**Use case (user-story relevance)**

- Marketing and planning teams can:
  - spot geographies with higher intent (where demand is concentrated), and
  - tailor messaging/offers by age segment in each country (e.g., youth-oriented low-cost trips vs higher-spend segments).

**Interaction**

- Click a country: updates the radial chart for that country.
- Hover an age slice: expands the arc and shows share + approximate spend in the center label.
- Map legend communicates the intent-count scale.

Files

- [Q2/index.html](Q2/index.html)
- [Q2/script.js](Q2/script.js)
- [Q2/travel_choropleth.json](Q2/travel_choropleth.json)
- [Q2/linked_radial_data.json](Q2/linked_radial_data.json)

---

## Q3 — Seasonal travel preference hierarchy (Zoomable sunburst)

**Visualization**: Zoomable sunburst (partition) showing: Season → Place Type → Activity Preference.

**Question this visualization answers**

- How do travel preferences distribute across seasons, and within each season, what place types and activity preferences dominate?
- What is the share of a segment relative to the whole dataset and relative to its parent segment?

**Marks & channels used**

- **Marks**: hierarchical arc segments arranged in rings.
- **Radial position (rings)**: depth encodes hierarchy level (inner: Season, middle: Place Type, outer: Activity Preference).
- **Angle / arc length**: encodes count (value) for each node.
- **Color**:
  - Inner ring uses a season palette.
  - Middle ring uses a place-type palette.
  - Outer ring uses an activity palette.
    (Colors reset per ring to keep categories distinct within each level.)
- **Text (center labels + tooltip)**: center label summarizes the focused segment; tooltip shows the full path and counts.

**Use case (user-story relevance)**

- Travel planners and content/product teams can:
  - create seasonal campaigns (e.g., Summer → Beach → Leisure),
  - allocate resources to popular seasonal offerings, and
  - discover niche combinations worth supporting (smaller arcs with clear context).

**Interaction**

- Hover a segment: highlights its ancestry path and shows tooltip with count + % of total and % of parent.
- Click a segment: zooms in to focus on that subtree; click the center to zoom out.

Files

- [Q3/index.html](Q3/index.html)
- [Q3/script.js](Q3/script.js)
- [Q3/seasonal_sunburst.json](Q3/seasonal_sunburst.json)

---

## Q4 — Travel purpose vs planning effort + priorities (Interactive stacked bars)

**Visualization**: Interactive stacked bar chart with a metric toggle:

- Mode A: average planning complexity by travel purpose
- Mode B: average preparation days by travel purpose

Each bar is stacked by the distribution of “priority” categories (Activities, Accommodation, Transport, Dining).

**What the two metrics mean**

- **Planning complexity**: a proxy for how detailed/constraint-heavy a prompt is (higher when more distinct entities/requirements must be satisfied, such as duration, group size, dietary constraints, proximity constraints, budget, and location).
  - Low planning complexity (~2.0) example: “What are things to do in Paris?” (Only 1 entity: Location).
  - High planning complexity (~9.0) example: “Plan a 14-day trip to Japan for a vegetarian family of 4, including hotels near rail stations on a $5,000 budget.” (6+ entities: Duration, Group Size, Diet, Proximity, Budget, Location).
- **Preparation days (prep days)**: the duration between the moment the prompt was written and the actual date the trip is intended to occur.

**Question this visualization answers**

- Which travel purposes are associated with higher planning complexity or longer preparation time?
- For each travel purpose, what do users prioritize most (distribution across Activities/Accommodation/Transport/Dining)?

**Marks & channels used**

- **Marks**: stacked rectangles (bar segments).
- **X position**: travel purpose (categorical) as band scale.
- **Y position / height**: metric magnitude (either avg complexity or avg prep days), with stacks representing priority contributions.
- **Color (categorical)**: bar segment color encodes priority category (Tableau categorical palette).
- **Text**: axis labels, legend labels; tooltip shows the priority % share for the hovered segment.

**Use case (user-story relevance)**

- UX/design and travel assistant tooling can use this to:
  - identify purposes that need more planning support (checklists, reminders, templates),
  - understand what users focus on first for each purpose (e.g., business trips may prioritize transport/accommodation), and
  - tailor onboarding and recommendations based on purpose.

**Interaction**

- Toggle buttons switch the y-axis metric between planning complexity and preparation days.
- Hover a segment shows a tooltip with the segment’s priority percentage for that purpose.

Files

- [Q4/index.html](Q4/index.html)
- [Q4/travel_data_complete.json](Q4/travel_data_complete.json)

---

## Notes

- All visualizations are implemented with D3.js (v7).
- Interactions are designed to support exploratory analysis: hover for details, click for focus/selection.
