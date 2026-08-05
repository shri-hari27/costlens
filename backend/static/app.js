const API_BASE = '';

let trendChart = null;
let rgChart = null;

function showToast(message) {
  const toast = document.getElementById('toast');
  toast.textContent = message;
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 3000);
}

function formatCurrency(n) {
  return '$' + Number(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

async function fetchSummary() {
  const res = await fetch(`${API_BASE}/api/summary`);
  if (!res.ok) throw new Error('Failed to fetch summary');
  return res.json();
}

async function fetchTrend() {
  const res = await fetch(`${API_BASE}/api/trend`);
  if (!res.ok) throw new Error('Failed to fetch trend');
  return res.json();
}

async function fetchWaste() {
  const res = await fetch(`${API_BASE}/api/waste`);
  if (!res.ok) throw new Error('Failed to fetch waste report');
  return res.json();
}

function renderSummary(data) {
  document.getElementById('totalCost').textContent = formatCurrency(data.totalCost || 0);
  document.getElementById('periodLabel').textContent =
    data.periodStart && data.periodEnd ? `${data.periodStart} to ${data.periodEnd}` : '';

  const trendText = document.getElementById('trendText');
  const trendArrow = document.getElementById('trendArrow');
  trendText.textContent = 'Tracking current spend';
  trendArrow.textContent = '↗';

  renderResourceGroupChart(data.byResourceGroup || []);
}

function renderResourceGroupChart(byRg) {
  const ctx = document.getElementById('rgChart').getContext('2d');
  const labels = byRg.map(r => r.resourceGroup);
  const values = byRg.map(r => r.cost);

  const palette = ['#6366f1', '#22d3ee', '#34d399', '#fbbf24', '#f87171', '#a78bfa', '#38bdf8'];

  if (rgChart) rgChart.destroy();
  rgChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: labels.length ? labels : ['No data'],
      datasets: [{
        data: values.length ? values : [1],
        backgroundColor: palette,
        borderColor: '#141a26',
        borderWidth: 3,
        hoverOffset: 8,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'right',
          labels: { color: '#8b93a7', boxWidth: 12, padding: 12, font: { size: 12 } },
        },
      },
    },
  });
}

function renderTrendChart(snapshots) {
  const ctx = document.getElementById('trendChart').getContext('2d');

  const sorted = [...snapshots].sort((a, b) =>
    (a.snapshotDate || '').localeCompare(b.snapshotDate || '')
  );

  const labels = sorted.map(s => s.snapshotDate || '');
  const values = sorted.map(s => s.totalCost || 0);

  const gradient = ctx.createLinearGradient(0, 0, 0, 260);
  gradient.addColorStop(0, 'rgba(99, 102, 241, 0.35)');
  gradient.addColorStop(1, 'rgba(99, 102, 241, 0)');

  if (trendChart) trendChart.destroy();
  trendChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels.length ? labels : ['No data yet'],
      datasets: [{
        label: 'Daily Spend',
        data: values.length ? values : [0],
        borderColor: '#6366f1',
        backgroundColor: gradient,
        fill: true,
        tension: 0.35,
        pointBackgroundColor: '#22d3ee',
        pointBorderColor: '#0a0e17',
        pointBorderWidth: 2,
        pointRadius: 4,
        pointHoverRadius: 6,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { color: '#1b2233' }, ticks: { color: '#8b93a7', font: { size: 11 } } },
        y: { grid: { color: '#1b2233' }, ticks: { color: '#8b93a7', font: { size: 11 } } },
      },
    },
  });
}

function renderWaste(data) {
  const findings = data.findings || [];
  const listEl = document.getElementById('wasteList');
  const countEl = document.getElementById('wasteCount');

  countEl.textContent = `${findings.length} finding${findings.length !== 1 ? 's' : ''}`;

  if (findings.length === 0) {
    listEl.innerHTML = '<div class="waste-empty">✓ No waste detected — everything looks clean!</div>';
    return;
  }

  listEl.innerHTML = findings.map(f => `
    <div class="waste-item">
      <div class="waste-item-left">
        <span class="waste-item-type">${(f.type || '').replace(/_/g, ' ')}</span>
        <span class="waste-item-name">${f.name || 'unknown'}</span>
        <span class="waste-item-meta">${f.resourceGroup || ''} · ${f.location || ''}</span>
      </div>
      <div class="waste-item-right">
        ${f.estimatedMonthlyCost != null ? `<span class="waste-item-cost">${formatCurrency(f.estimatedMonthlyCost)}/mo</span>` : ''}
        <code class="waste-item-cmd" title="Click to copy" data-cmd="${(f.fixCommand || '').replace(/"/g, '&quot;')}">${f.fixCommand || ''}</code>
      </div>
    </div>
  `).join('');

  listEl.querySelectorAll('.waste-item-cmd').forEach(el => {
    el.addEventListener('click', () => {
      navigator.clipboard.writeText(el.dataset.cmd).then(() => showToast('Command copied to clipboard'));
    });
  });
}

async function loadDashboard() {
  try {
    const [summary, trend, waste] = await Promise.all([fetchSummary(), fetchTrend(), fetchWaste()]);
    renderSummary(summary);
    renderTrendChart(trend);
    renderWaste(waste);
  } catch (err) {
    console.error('Dashboard load error:', err);
    showToast('Failed to load dashboard data');
  }
}

async function handleRefresh() {
  const btn = document.getElementById('refreshBtn');
  btn.classList.add('loading');
  btn.disabled = true;

  try {
    showToast('Triggering refresh...');
    await loadDashboard();
    showToast('Dashboard refreshed');
  } catch (err) {
    showToast('Refresh failed');
  } finally {
    btn.classList.remove('loading');
    btn.disabled = false;
  }
}

document.getElementById('refreshBtn').addEventListener('click', handleRefresh);

loadDashboard();
setInterval(loadDashboard, 60000);
