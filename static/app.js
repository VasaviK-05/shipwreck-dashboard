let categoryChart;
let dangerChart;

let currentPage = 1;
const limit = 100;
let totalRecords = 0;

async function loadOverview() {
    const res = await fetch('/api/overview');
    const data = await res.json();

    document.getElementById('totalWrecks').textContent = data.total_wrecks;
    document.getElementById('dangerousWrecks').textContent = data.dangerous_wrecks;
    document.getElementById('visibleWrecks').textContent = data.visible_wrecks;
    document.getElementById('avgDepth').textContent = data.avg_depth;
    document.getElementById('overviewQueryTime').textContent =
        `Overview query time: ${data.query_time_ms} ms`;
}

async function loadCategoryFilter() {
    const res = await fetch('/api/categories-list');
    const categories = await res.json();

    const select = document.getElementById('categoryFilter');
    select.innerHTML = '<option value="">All Categories</option>';

    categories.forEach(cat => {
        const option = document.createElement('option');
        option.value = cat;
        option.textContent = cat;
        select.appendChild(option);
    });
}

async function loadCategoryChart() {
    const res = await fetch('/api/categories');
    const result = await res.json();

    document.getElementById('categoryQueryTime').textContent =
        `${result.query_time_ms} ms`;

    const labels = result.data.map(item => item.category || 'Unknown');
    const counts = result.data.map(item => item.count);

    const ctx = document.getElementById('categoryChart').getContext('2d');

    if (categoryChart) {
        categoryChart.destroy();
    }

    categoryChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Wreck Count',
                data: counts
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    labels: {
                        color: '#ffffff'
                    }
                }
            },
            scales: {
                x: {
                    ticks: {
                        color: '#ffffff'
                    }
                },
                y: {
                    ticks: {
                        color: '#ffffff'
                    }
                }
            }
        }
    });
}

async function loadDangerChart() {
    const res = await fetch('/api/danger-status');
    const result = await res.json();

    document.getElementById('dangerQueryTime').textContent =
        `${result.query_time_ms} ms`;

    const labels = result.data.map(item =>
        item.dangerous === 'True' || item.dangerous === 'true' ? 'Dangerous' : 'Safe'
    );
    const counts = result.data.map(item => item.count);

    const ctx = document.getElementById('dangerChart').getContext('2d');

    if (dangerChart) {
        dangerChart.destroy();
    }

    dangerChart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                label: 'Danger Status',
                data: counts
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    labels: {
                        color: '#ffffff'
                    }
                }
            }
        }
    });
}

async function loadTopDepths() {
    const res = await fetch('/api/top-depths');
    const result = await res.json();

    document.getElementById('topDepthQueryTime').textContent =
        `${result.query_time_ms} ms`;

    const container = document.getElementById('topDepthList');
    container.innerHTML = '';

    result.data.forEach(item => {
        const div = document.createElement('div');
        div.className = 'depth-item';
        div.innerHTML = `
            <strong>Wreck ID:</strong> ${item.wreck_id}
            <span>|</span>
            <strong>Category:</strong> ${item.category_name || 'Unknown'}
            <span>|</span>
            <strong>Depth:</strong> ${item.depth ?? 'N/A'}
        `;
        container.appendChild(div);
    });
}

async function loadWrecks(page = 1) {
    const dangerous = document.getElementById('dangerousFilter').value;
    const visible = document.getElementById('visibleFilter').value;
    const category = document.getElementById('categoryFilter').value;
    const search = document.getElementById('searchInput').value.trim();

    const offset = (page - 1) * limit;

    const params = new URLSearchParams({
        limit: limit,
        offset: offset
    });

    if (dangerous) params.append('dangerous', dangerous);
    if (visible) params.append('visible', visible);
    if (category) params.append('category', category);
    if (search) params.append('search', search);

    const res = await fetch(`/api/wrecks?${params.toString()}`);
    const result = await res.json();

    totalRecords = result.total_count;
    currentPage = page;

    document.getElementById('tableQueryTime').textContent =
        `Filtered query time: ${result.query_time_ms} ms`;

    document.getElementById('recordCount').textContent =
        `Showing ${result.records.length} of ${result.total_count} matching records`;

    document.getElementById('pageInfo').textContent =
        `Page ${currentPage} of ${Math.max(1, Math.ceil(totalRecords / limit))}`;

    const tbody = document.getElementById('wreckTableBody');
    tbody.innerHTML = '';

    result.records.forEach(wreck => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${wreck.wreck_id}</td>
            <td>${wreck.category_name ?? ''}</td>
            <td>${wreck.water_level ?? ''}</td>
            <td>${wreck.chart_name ?? ''}</td>
            <td>${wreck.depth ?? ''}</td>
            <td>${wreck.dangerous}</td>
            <td>${wreck.visible}</td>
        `;
        tbody.appendChild(tr);
    });
}

document.getElementById('applyFilters').addEventListener('click', () => {
    loadWrecks(1);
});

document.getElementById('prevPage').addEventListener('click', () => {
    if (currentPage > 1) {
        loadWrecks(currentPage - 1);
    }
});

document.getElementById('nextPage').addEventListener('click', () => {
    const totalPages = Math.ceil(totalRecords / limit);
    if (currentPage < totalPages) {
        loadWrecks(currentPage + 1);
    }
});

async function init() {
    await loadOverview();
    await loadCategoryFilter();
    await loadCategoryChart();
    await loadDangerChart();
    await loadTopDepths();
    await loadWrecks(1);
}

init();