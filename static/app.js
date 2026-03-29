let categoryChartInstance = null;
let waterChartInstance = null;
let depthChartInstance = null;
let currentPage = 1;
let perPage = 100;

function buildQueryParams() {
  const params = new URLSearchParams();

  const search = document.getElementById("searchInput").value.trim();
  const category = document.getElementById("categoryFilter").value;
  const waterLevel = document.getElementById("waterLevelFilter").value;
  const chartName = document.getElementById("chartFilter").value;
  const dangerous = document.getElementById("dangerousOnly").checked;
  const visible = document.getElementById("visibleOnly").checked;
  const missingDepth = document.getElementById("missingDepthOnly").checked;
  const minDepth = document.getElementById("minDepth").value;
  const maxDepth = document.getElementById("maxDepth").value;

  if (search) params.append("search", search);
  if (category) params.append("category", category);
  if (waterLevel) params.append("water_level", waterLevel);
  if (chartName) params.append("chart_name", chartName);
  if (dangerous) params.append("dangerous", "true");
  if (visible) params.append("visible", "true");
  if (missingDepth) params.append("missing_depth", "true");
  if (minDepth) params.append("min_depth", minDepth);
  if (maxDepth) params.append("max_depth", maxDepth);

  return params.toString();
}

function switchView(viewId) {
  document.querySelectorAll(".view-page").forEach(section => {
    section.classList.remove("active-view");
  });
  document.getElementById(viewId).classList.add("active-view");

  document.querySelectorAll(".nav-btn").forEach(btn => {
    btn.classList.remove("active");
  });
  document.querySelector(`.nav-btn[data-view="${viewId}"]`).classList.add("active");

  const titleMap = {
    overviewView: ["Overview", "Dark ocean analytics view of maritime hazard records"],
    hazardView: ["Hazard Insights", "Focused hazard counts and grouped analytical views"],
    recordsView: ["Records", "Explore filtered records with pagination and drill-down"],
    qualityView: ["Data Quality", "Inspect missing data and structural completeness"]
  };

  document.getElementById("pageTitle").textContent = titleMap[viewId][0];
  document.getElementById("pageSubtitle").textContent = titleMap[viewId][1];
}

async function loadFilterOptions() {
  const res = await fetch("/api/filter-options");
  const data = await res.json();

  const categoryFilter = document.getElementById("categoryFilter");
  const waterLevelFilter = document.getElementById("waterLevelFilter");
  const chartFilter = document.getElementById("chartFilter");

  categoryFilter.innerHTML = `<option value="">All</option>`;
  waterLevelFilter.innerHTML = `<option value="">All</option>`;
  chartFilter.innerHTML = `<option value="">All</option>`;

  data.categories.forEach(item => {
    const option = document.createElement("option");
    option.value = item;
    option.textContent = item;
    categoryFilter.appendChild(option);
  });

  data.water_levels.forEach(item => {
    const option = document.createElement("option");
    option.value = item;
    option.textContent = item;
    waterLevelFilter.appendChild(option);
  });

  data.charts.forEach(item => {
    const option = document.createElement("option");
    option.value = item;
    option.textContent = item;
    chartFilter.appendChild(option);
  });
}

async function loadStats() {
  const params = buildQueryParams();
  const res = await fetch(`/api/stats?${params}`);
  const data = await res.json();

  document.getElementById("totalWrecks").textContent = data.total_wrecks;
  document.getElementById("dangerousWrecks").textContent = data.dangerous_wrecks;
  document.getElementById("visibleWrecks").textContent = data.visible_wrecks;
  document.getElementById("avgDepth").textContent = data.avg_depth ?? "N/A";
  document.getElementById("waterTypes").textContent = data.water_level_types;
  document.getElementById("missingDepthCount").textContent = data.missing_depth_count;
  document.getElementById("hazardCountOnly").textContent = data.dangerous_wrecks;
}

async function loadCategoryChart() {
  const params = buildQueryParams();
  const res = await fetch(`/api/category-counts?${params}`);
  const data = await res.json();

  if (categoryChartInstance) categoryChartInstance.destroy();

  categoryChartInstance = new Chart(document.getElementById("categoryChart"), {
    type: "bar",
    data: {
      labels: data.map(x => x.category),
      datasets: [{
        label: "Count",
        data: data.map(x => x.count)
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: "#edf7ff" } }
      },
      scales: {
        x: { ticks: { color: "#edf7ff" }, grid: { color: "rgba(255,255,255,0.08)" } },
        y: { ticks: { color: "#edf7ff" }, grid: { color: "rgba(255,255,255,0.08)" } }
      }
    }
  });
}

async function loadWaterChart() {
  const params = buildQueryParams();
  const res = await fetch(`/api/water-level-counts?${params}`);
  const data = await res.json();

  if (waterChartInstance) waterChartInstance.destroy();

  waterChartInstance = new Chart(document.getElementById("waterChart"), {
    type: "pie",
    data: {
      labels: data.map(x => x.water_level),
      datasets: [{
        data: data.map(x => x.count)
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: "#edf7ff" } }
      }
    }
  });
}

async function loadDepthChart() {
  const params = buildQueryParams();
  const res = await fetch(`/api/depth-bands?${params}`);
  const data = await res.json();

  if (depthChartInstance) depthChartInstance.destroy();

  depthChartInstance = new Chart(document.getElementById("depthChart"), {
    type: "doughnut",
    data: {
      labels: data.map(x => x.band),
      datasets: [{
        data: data.map(x => x.count)
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: "#edf7ff" } }
      }
    }
  });
}

async function loadQuality() {
  const params = buildQueryParams();
  const res = await fetch(`/api/data-quality?${params}`);
  const data = await res.json();

  document.getElementById("qMissingDepth").textContent = data.missing_depth;
  document.getElementById("qMissingHistory").textContent = data.missing_history;
  document.getElementById("qMissingQuasou").textContent = data.missing_quasou;
  document.getElementById("qMissingChart").textContent = data.missing_chart;
}

async function loadRecords(page = 1) {
  currentPage = page;
  const params = buildQueryParams();
  const res = await fetch(`/api/records?${params}&page=${page}&per_page=${perPage}`);
  const payload = await res.json();

  const data = payload.records;
  const tbody = document.getElementById("recordsTableBody");
  const countLabel = document.getElementById("recordCountLabel");

  tbody.innerHTML = "";
  countLabel.textContent = `Showing page ${payload.page} of ${payload.total_pages} | Total matching records: ${payload.total_count}`;

  data.forEach(row => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${row.wreck_id}</td>
      <td>${row.category_name ?? "N/A"}</td>
      <td>${row.water_level ?? "N/A"}</td>
      <td>${row.depth ?? "N/A"}</td>
      <td>${row.latitude ?? "N/A"}</td>
      <td>${row.longitude ?? "N/A"}</td>
      <td>${row.dangerous ? "Yes" : "No"}</td>
      <td>${row.visible ? "Yes" : "No"}</td>
      <td><button class="secondary detail-btn" data-id="${row.wreck_id}">View</button></td>
    `;
    tbody.appendChild(tr);
  });

  document.querySelectorAll(".detail-btn").forEach(btn => {
    btn.addEventListener("click", async () => {
      const id = btn.dataset.id;
      await openDrawer(id);
    });
  });

  renderPagination(payload.page, payload.total_pages);
}

function renderPagination(page, totalPages) {
  const pagination = document.getElementById("paginationControls");
  pagination.innerHTML = `
    <button ${page <= 1 ? "disabled" : ""} id="prevPageBtn">Previous</button>
    <span>Page ${page} of ${totalPages}</span>
    <button ${page >= totalPages ? "disabled" : ""} id="nextPageBtn">Next</button>
  `;

  const prevBtn = document.getElementById("prevPageBtn");
  const nextBtn = document.getElementById("nextPageBtn");

  if (prevBtn) prevBtn.addEventListener("click", () => loadRecords(page - 1));
  if (nextBtn) nextBtn.addEventListener("click", () => loadRecords(page + 1));
}

async function openDrawer(id) {
  const res = await fetch(`/api/record/${id}`);
  const data = await res.json();

  const content = document.getElementById("drawerContent");
  content.innerHTML = `
    <div class="drawer-field"><strong>Wreck ID</strong>${data.wreck_id}</div>
    <div class="drawer-field"><strong>Category</strong>${data.category_name ?? "N/A"}</div>
    <div class="drawer-field"><strong>Water Level</strong>${data.water_level ?? "N/A"}</div>
    <div class="drawer-field"><strong>Chart Source</strong>${data.chart_name ?? "N/A"}</div>
    <div class="drawer-field"><strong>Latitude</strong>${data.latitude ?? "N/A"}</div>
    <div class="drawer-field"><strong>Longitude</strong>${data.longitude ?? "N/A"}</div>
    <div class="drawer-field"><strong>Depth</strong>${data.depth ?? "N/A"}</div>
    <div class="drawer-field"><strong>Dangerous</strong>${data.dangerous ? "Yes" : "No"}</div>
    <div class="drawer-field"><strong>Visible</strong>${data.visible ? "Yes" : "No"}</div>
    <div class="drawer-field"><strong>History</strong>${data.history ?? "N/A"}</div>
    <div class="drawer-field"><strong>Quasou</strong>${data.quasou ?? "N/A"}</div>
  `;

  document.getElementById("detailDrawer").classList.add("open");
}

function resetFilters() {
  document.getElementById("searchInput").value = "";
  document.getElementById("categoryFilter").value = "";
  document.getElementById("waterLevelFilter").value = "";
  document.getElementById("chartFilter").value = "";
  document.getElementById("dangerousOnly").checked = false;
  document.getElementById("visibleOnly").checked = false;
  document.getElementById("missingDepthOnly").checked = false;
  document.getElementById("minDepth").value = "";
  document.getElementById("maxDepth").value = "";
}

function exportTableToCSV() {
  const rows = Array.from(document.querySelectorAll("table tr"));
  const csv = rows.map(row =>
    Array.from(row.querySelectorAll("th, td"))
      .slice(0, 8)
      .map(cell => `"${cell.innerText.replace(/"/g, '""')}"`)
      .join(",")
  ).join("\n");

  const blob = new Blob([csv], { type: "text/csv" });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "filtered_records.csv";
  a.click();
  window.URL.revokeObjectURL(url);
}

async function applyAllData() {
  await loadStats();
  await loadCategoryChart();
  await loadWaterChart();
  await loadDepthChart();
  await loadQuality();
  await loadRecords(1);
}

async function initDashboard() {
  let progress = 0;
  const bar = document.getElementById("progressBar");
  const ship = document.querySelector(".ship");

  const timer = setInterval(() => {
    progress += 10;
    if (progress <= 90) {
      bar.style.width = `${progress}%`;
    }
  }, 180);

  await loadFilterOptions();
  await applyAllData();

  clearInterval(timer);
  bar.style.width = "100%";
  ship.classList.add("sink");

  setTimeout(() => {
    document.getElementById("loaderOverlay").classList.add("hidden");
  }, 1000);
}

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".nav-btn").forEach(btn => {
    btn.addEventListener("click", () => switchView(btn.dataset.view));
  });

  document.getElementById("applyFiltersBtn").addEventListener("click", applyAllData);
  document.getElementById("resetFiltersBtn").addEventListener("click", async () => {
    resetFilters();
    await applyAllData();
  });

  document.getElementById("refreshBtn").addEventListener("click", applyAllData);
  document.getElementById("exportBtn").addEventListener("click", exportTableToCSV);
  document.getElementById("closeDrawer").addEventListener("click", () => {
    document.getElementById("detailDrawer").classList.remove("open");
  });

  initDashboard();
});