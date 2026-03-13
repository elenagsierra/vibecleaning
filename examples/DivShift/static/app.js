const PROJECT_NAME = "DivShiftNAWC";
const LOGICAL_NAME = "divshift_nawc.csv";
const STORAGE_KEY = "divshift_bias_dashboard_state_v1";

class DivShiftDashboard {
  constructor({ mountEl, heroStatsEl }) {
    this.mountEl = mountEl;
    this.heroStatsEl = heroStatsEl;
    this.datasetId = "";
    this.summary = null;
    this.state = this.loadState();
  }

  loadState() {
    try {
      const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
      return {
        familyKey: parsed.familyKey || "",
        groupKey: parsed.groupKey || "",
        partitionKey: parsed.partitionKey || "",
      };
    } catch {
      return { familyKey: "", groupKey: "", partitionKey: "" };
    }
  }

  saveState() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(this.state));
  }

  async init() {
    this.mountEl.innerHTML = `<div class="status">Loading project state for <code>${PROJECT_NAME}</code>...</div>`;
    const projectState = await this.fetchJSON(`/api/project/${encodeURIComponent(PROJECT_NAME)}/state`);
    this.datasetId = projectState.project.current_dataset_id;
    this.mountEl.innerHTML = `<div class="status">Scanning <code>${LOGICAL_NAME}</code>. The first load can take a while because the summary is built directly from the raw CSV.</div>`;
    this.summary = await this.fetchJSON(
      `/api/project/${encodeURIComponent(PROJECT_NAME)}/apps/divshift/dataset/${encodeURIComponent(this.datasetId)}/summary?logical_name=${encodeURIComponent(LOGICAL_NAME)}`
    );
    this.ensureValidSelection();
    this.render();
  }

  async fetchJSON(url) {
    const response = await fetch(url);
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || `Request failed for ${url}`);
    }
    return payload;
  }

  ensureValidSelection() {
    const family = this.getSelectedFamily() || this.summary.families[0];
    if (!family) {
      return;
    }
    this.state.familyKey = family.key;
    const group = family.groups.find((item) => item.key === this.state.groupKey) || family.groups[0];
    this.state.groupKey = group ? group.key : "";
    const partition = group?.partitions.find((item) => item.key === this.state.partitionKey) || group?.partitions[0];
    this.state.partitionKey = partition ? partition.key : "";
    this.saveState();
  }

  getSelectedFamily() {
    return this.summary?.families.find((item) => item.key === this.state.familyKey) || null;
  }

  getSelectedGroup() {
    const family = this.getSelectedFamily();
    return family?.groups.find((item) => item.key === this.state.groupKey) || null;
  }

  getSelectedPartition() {
    const group = this.getSelectedGroup();
    return group?.partitions.find((item) => item.key === this.state.partitionKey) || null;
  }

  setFamily(familyKey) {
    this.state.familyKey = familyKey;
    this.state.groupKey = "";
    this.state.partitionKey = "";
    this.ensureValidSelection();
    this.render();
  }

  setPartition(groupKey, partitionKey) {
    this.state.groupKey = groupKey;
    this.state.partitionKey = partitionKey;
    this.ensureValidSelection();
    this.render();
  }

  numberFormat(value) {
    return new Intl.NumberFormat("en-US").format(value || 0);
  }

  percentFormat(value) {
    return `${(100 * (value || 0)).toFixed(1)}%`;
  }

  imageUrl(sample) {
    const params = new URLSearchParams({
      state_name: sample.state_name,
      photo_id: sample.photo_id,
    });
    return `/api/project/${encodeURIComponent(PROJECT_NAME)}/apps/divshift/image?${params.toString()}`;
  }

  artifactUrl() {
    return `/api/project/${encodeURIComponent(PROJECT_NAME)}/artifact/${encodeURIComponent(this.datasetId)}/${encodeURIComponent(LOGICAL_NAME)}`;
  }

  renderHeroStats() {
    const overview = this.summary.overview;
    const stats = [
      {
        label: "Images indexed",
        value: this.numberFormat(overview.total_rows),
        copy: "Every CSV row maps to a single image path inside the state folders.",
      },
      {
        label: "Distinct taxa",
        value: this.numberFormat(overview.distinct_species),
        copy: "Taxonomic spread is broad, but the long tail remains thin compared with the dominant taxa.",
      },
      {
        label: "Distinct observers",
        value: this.numberFormat(overview.distinct_observers),
        copy: `Top 10 observers contribute ${this.percentFormat(overview.top_10_observer_share)} of all rows.`,
      },
      {
        label: "Temporal span",
        value: `${overview.date_start || "?"} to ${overview.date_end || "?"}`,
        copy: "The year and season bands below show which parts of that span dominate collection volume.",
      },
      {
        label: "States covered",
        value: this.numberFormat(overview.distinct_states),
        copy: "State counts and socioeconomic splits show geography beyond a single west coast core.",
      },
      {
        label: "Summary build",
        value: `${overview.build_seconds.toFixed(2)}s`,
        copy: "Built live from the raw CSV and cached in-process for repeat views.",
      },
    ];
    this.heroStatsEl.innerHTML = stats.map((item) => `
      <article class="stat">
        <div class="stat-label">${item.label}</div>
        <div class="stat-value">${item.value}</div>
        <div class="stat-copy">${item.copy}</div>
      </article>
    `).join("");
  }

  renderAtlas() {
    const bounds = this.summary.bounds;
    const width = 960;
    const height = 360;
    const points = this.summary.geo_points.map((point) => {
      const x = ((point.lon - bounds.min_lon) / Math.max(bounds.max_lon - bounds.min_lon, 1e-6)) * width;
      const y = height - (((point.lat - bounds.min_lat) / Math.max(bounds.max_lat - bounds.min_lat, 1e-6)) * height);
      let color = "#b56a43";
      if (point.split === "train") {
        color = "#345642";
      } else if (point.split === "test") {
        color = "#d4a64d";
      }
      return `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="2.2" fill="${color}" fill-opacity="0.55"></circle>`;
    }).join("");
    return `
      <div class="atlas">
        <div class="atlas-frame">
          <svg class="atlas-svg" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" aria-label="Spatial distribution atlas">
            <defs>
              <linearGradient id="atlasWash" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stop-color="rgba(52,86,66,0.10)"></stop>
                <stop offset="100%" stop-color="rgba(181,106,67,0.02)"></stop>
              </linearGradient>
            </defs>
            <rect x="0" y="0" width="${width}" height="${height}" fill="url(#atlasWash)"></rect>
            <g opacity="0.18" stroke="#345642" stroke-width="1">
              <line x1="0" y1="${height / 3}" x2="${width}" y2="${height / 3}"></line>
              <line x1="0" y1="${(2 * height) / 3}" x2="${width}" y2="${(2 * height) / 3}"></line>
              <line x1="${width / 3}" y1="0" x2="${width / 3}" y2="${height}"></line>
              <line x1="${(2 * width) / 3}" y1="0" x2="${(2 * width) / 3}" y2="${height}"></line>
            </g>
            ${points}
          </svg>
        </div>
        <div class="atlas-legend">
          <span class="legend-dot" style="color:#345642">Spatial train</span>
          <span class="legend-dot" style="color:#d4a64d">Spatial test</span>
          <span class="legend-dot" style="color:#b56a43">No spatial split label</span>
        </div>
      </div>
    `;
  }

  renderFamilyTabs() {
    return `
      <div class="family-tabs">
        ${this.summary.families.map((family) => `
          <button class="family-tab ${family.key === this.state.familyKey ? "active" : ""}" data-family-key="${family.key}">
            ${family.title}
          </button>
        `).join("")}
      </div>
    `;
  }

  renderBiasGroups(family) {
    const selectedGroup = this.getSelectedGroup();
    const selectedPartition = this.getSelectedPartition();
    return `
      <div class="bias-grid">
        ${family.groups.map((group) => `
          <article class="group-card">
            <h3>${group.label}</h3>
            <p>${group.description}</p>
            <div class="partition-list">
              ${group.partitions.map((partition) => `
                <button
                  class="partition-button ${selectedGroup?.key === group.key && selectedPartition?.key === partition.key ? "active" : ""}"
                  data-group-key="${group.key}"
                  data-partition-key="${partition.key}">
                  <div class="partition-top">
                    <span class="partition-name">${partition.label}</span>
                    <span class="partition-count">${this.numberFormat(partition.count)} images</span>
                  </div>
                  <div class="bar"><span style="width:${Math.max(3, 100 * partition.share)}%"></span></div>
                </button>
              `).join("")}
            </div>
          </article>
        `).join("")}
      </div>
    `;
  }

  renderGallery() {
    const family = this.getSelectedFamily();
    const group = this.getSelectedGroup();
    const partition = this.getSelectedPartition();
    const samples = partition?.samples || [];
    if (!family || !group || !partition) {
      return "";
    }
    return `
      <section class="panel">
        <div class="panel-head">
          <div>
            <h2>${family.title}</h2>
            <p>${family.description}</p>
          </div>
          <div>
            <a href="${this.artifactUrl()}" target="_blank" rel="noreferrer">Open raw CSV artifact</a>
          </div>
        </div>
        ${this.renderFamilyTabs()}
        ${this.renderBiasGroups(family)}
        <div class="gallery">
          <div class="gallery-head">
            <div>
              <h3>${group.label}: ${partition.label}</h3>
              <p>${this.numberFormat(partition.count)} rows fall into this partition. The thumbnails below link back to the original images.</p>
            </div>
          </div>
          <div class="gallery-grid">
            ${samples.map((sample) => `
              <a class="sample-card" href="${this.imageUrl(sample)}" target="_blank" rel="noreferrer">
                <img loading="lazy" src="${this.imageUrl(sample)}" alt="${sample.name}">
                <div class="sample-copy">
                  <div class="sample-title">${sample.name}</div>
                  <div class="sample-meta">${sample.state_name.replaceAll("_", " ")} · ${sample.observed_on || "Unknown date"}</div>
                  <div class="sample-meta">${sample.quality_grade} · observer ${sample.observer_id || "unknown"}</div>
                </div>
              </a>
            `).join("")}
          </div>
        </div>
        <div class="footer-note">
          Images are resolved at request time from the nested state folders using <code>photo_id</code>. If a row has a missing image on disk, that card will 404 rather than silently redirect.
        </div>
      </section>
    `;
  }

  renderBarList(items, labelKey) {
    const max = Math.max(...items.map((item) => item.count), 1);
    return `
      <div class="list-bars">
        ${items.map((item) => `
          <div class="list-row">
            <div class="list-row-top">
              <span>${item[labelKey]}</span>
              <span>${this.numberFormat(item.count)}</span>
            </div>
            <div class="bar"><span style="width:${(100 * item.count) / max}%"></span></div>
          </div>
        `).join("")}
      </div>
    `;
  }

  renderTimeline() {
    const yearCounts = this.summary.year_counts.slice(-10);
    const max = Math.max(...yearCounts.map((item) => item.count), 1);
    return `
      <div class="timeline">
        ${yearCounts.map((item) => `
          <div class="timeline-bar">
            <div class="timeline-column" style="height:${Math.max(6, (160 * item.count) / max)}px"></div>
            <div class="timeline-label">${item.year}</div>
          </div>
        `).join("")}
      </div>
    `;
  }

  renderInsights() {
    return `
      <section class="panel">
        <div class="panel-head">
          <div>
            <h2>Context layers</h2>
            <p>These summaries sit underneath the partition browser so you can see why certain groups dominate the data before drilling into images.</p>
          </div>
        </div>
        <div class="insight-grid">
          <article class="insight-card">
            <h3>Temporal skyline</h3>
            ${this.renderTimeline()}
          </article>
          <article class="insight-card">
            <h3>State concentration</h3>
            ${this.renderBarList(this.summary.state_counts, "label")}
          </article>
          <article class="insight-card">
            <h3>Top taxa</h3>
            ${this.renderBarList(this.summary.top_taxa.map((item) => ({ count: item.count, name: item.name })), "name")}
          </article>
          <article class="insight-card">
            <h3>Taxon long tail</h3>
            ${this.renderBarList(this.summary.taxon_tail, "label")}
          </article>
          <article class="insight-card">
            <h3>Quality grades</h3>
            ${this.renderBarList(this.summary.quality_grade_counts, "label")}
          </article>
          <article class="insight-card">
            <h3>Observer concentration</h3>
            ${this.renderBarList(this.summary.top_observers.map((item) => ({ count: item.count, observer_id: item.observer_id })), "observer_id")}
          </article>
          <article class="insight-card">
            <h3>Seasonality</h3>
            ${this.renderBarList(this.summary.month_counts.map((item) => ({ count: item.count, month: item.month })), "month")}
          </article>
          <article class="insight-card">
            <h3>Why this matters</h3>
            <div class="mini-grid">
              <div>
                <div class="stat-label">Spatial</div>
                <p class="stat-copy">Wilderness, modified land, and city-adjacent nature are not interchangeable contexts. The split structure makes those gaps visible.</p>
              </div>
              <div>
                <div class="stat-label">Taxa</div>
                <p class="stat-copy">A few taxa appear repeatedly while many species remain sparse. Balanced and unbalanced partitions expose the tradeoff directly.</p>
              </div>
              <div>
                <div class="stat-label">Sociopolitical</div>
                <p class="stat-copy">State-specific socioeconomic partitions approximate where representation may follow access, infrastructure, or observer concentration.</p>
              </div>
              <div>
                <div class="stat-label">Observer quality</div>
                <p class="stat-copy">Research-grade images and engaged contributors shape the visual quality that downstream models inherit.</p>
              </div>
            </div>
          </article>
        </div>
      </section>
    `;
  }

  bindEvents() {
    this.mountEl.addEventListener("click", (event) => {
      const familyButton = event.target.closest("[data-family-key]");
      if (familyButton) {
        this.setFamily(familyButton.dataset.familyKey);
        return;
      }
      const partitionButton = event.target.closest("[data-group-key][data-partition-key]");
      if (partitionButton) {
        this.setPartition(partitionButton.dataset.groupKey, partitionButton.dataset.partitionKey);
      }
    });
  }

  render() {
    this.renderHeroStats();
    this.mountEl.innerHTML = `
      <div class="layout">
        <section class="panel">
          <div class="panel-head">
            <div>
              <h2>Bias atlas</h2>
              <p>A projected point cloud of the NAWC footprint, colored by the primary spatial split and bounded by the observed latitude/longitude range.</p>
            </div>
          </div>
          ${this.renderAtlas()}
        </section>
        ${this.renderGallery()}
      </div>
      <div style="margin-top:22px;">
        ${this.renderInsights()}
      </div>
    `;
  }
}

async function main() {
  const app = new DivShiftDashboard({
    mountEl: document.getElementById("app"),
    heroStatsEl: document.getElementById("hero-stats"),
  });
  app.bindEvents();
  try {
    await app.init();
  } catch (error) {
    app.mountEl.innerHTML = `<div class="error-card">${error.message}</div>`;
  }
}

main();
