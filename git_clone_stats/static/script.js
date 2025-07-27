// Theme Management
const themeToggle = document.getElementById('theme-toggle');
const html = document.documentElement;

// Initialize theme
function initTheme() {
    const savedTheme = localStorage.getItem('theme') || 'light';
    html.setAttribute('data-theme', savedTheme);
    updateThemeIcon(savedTheme);
}

function updateThemeIcon(theme) {
    const icon = themeToggle.querySelector('i');
    icon.className = theme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
}

themeToggle.addEventListener('click', () => {
    const currentTheme = html.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';

    html.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    updateThemeIcon(newTheme);

    showToast('Theme updated!', 'success');
});

// Toast Notifications
function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    const icon = type === 'success' ? 'fas fa-check-circle' : 'fas fa-exclamation-circle';
    toast.innerHTML = `
        <i class="${icon}"></i>
        <span>${message}</span>
    `;

    container.appendChild(toast);

    setTimeout(() => toast.classList.add('show'), 100);
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => container.removeChild(toast), 300);
    }, 3000);
}

// State Management
let allRepos = [];
let filteredRepos = [];
let githubUsername = '';
let repoCardTemplate = '';

// Chart view state
let currentView = 'cards'; // 'cards' or 'charts'
let chartInstances = new Map(); // Store chart instances for cleanup

// Helper function to format dates
function formatDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diffTime = now - date;
    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) {
        return 'Today';
    } else if (diffDays === 1) {
        return 'Yesterday';
    } else if (diffDays < 7) {
        return `${diffDays} days ago`;
    } else if (diffDays < 30) {
        const weeks = Math.floor(diffDays / 7);
        return `${weeks} week${weeks > 1 ? 's' : ''} ago`;
    } else if (diffDays < 365) {
        const months = Math.floor(diffDays / 30);
        return `${months} month${months > 1 ? 's' : ''} ago`;
    } else {
        const years = Math.floor(diffDays / 365);
        return `${years} year${years > 1 ? 's' : ''} ago`;
    }
}

// Load repository card template
async function loadTemplate() {
    try {
        const response = await fetch('/static/repo-card-template.html');
        if (!response.ok) throw new Error('Failed to load template');
        repoCardTemplate = await response.text();
    } catch (error) {
        console.error('Error loading template:', error);
        // Fallback to inline template if loading fails
        repoCardTemplate = `
            <div class="repo-header">
                <div class="repo-icon">
                    <i class="fab fa-github"></i>
                </div>
                <h3 class="repo-name">{{repo.name}}</h3>
                <div class="repo-stars">
                    <i class="fas fa-star"></i>
                    <span class="star-count">{{repo.star_count}}</span>
                </div>
            </div>
            <div class="repo-stats">
                <div class="stat-item">
                    <div class="stat-number">{{repo.total_clones}}</div>
                    <div class="stat-label-small">Total Clones</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number">{{repo.total_uniques}}</div>
                    <div class="stat-label-small">Unique Cloners</div>
                </div>
            </div>
            <div class="repo-dates">
                <div class="date-item">
                    <div class="date-label">First Collected</div>
                    <div class="date-value">{{repo.first_collected_formatted}}</div>
                </div>
                <div class="date-item">
                    <div class="date-label">Last Sync</div>
                    <div class="date-value">{{repo.last_sync_formatted}}</div>
                </div>
            </div>
            <div class="badge-container">
                <div class="badge-title">
                    Add Stat Badge to GitHub
                </div>
                <div class="badge-preview">
                    <img src="{{badgeUrl}}" alt="Clone badge for {{repo.name}}" />
                </div>
                <button class="btn btn-primary copy-btn" onclick="copyToClipboard('{{markdownCode}}', this)">
                    <i class="fas fa-copy"></i>
                    Copy Markdown
                </button>
            </div>
        `;
    }
}

// Simple template engine
function renderTemplate(template, data) {
    return template.replace(/\{\{([^}]+)\}\}/g, (_, key) => {
        const keys = key.trim().split('.');
        let value = data;
        for (const k of keys) {
            value = value?.[k];
        }
        return value !== undefined ? value : '';
    });
}

// View Management
function switchView(view) {
    currentView = view;
    
    // Update button states
    cardViewBtn.classList.toggle('active', view === 'cards');
    chartViewBtn.classList.toggle('active', view === 'charts');
    
    // Update visibility
    chartControls.style.display = view === 'charts' ? 'block' : 'none';
    chartContainer.style.display = view === 'charts' ? 'block' : 'none';
    reposContainer.style.display = view === 'cards' ? 'grid' : 'none';
    
    // Update search/sort controls relevance
    searchInput.parentElement.style.display = view === 'cards' ? 'flex' : 'none';
    sortSelect.parentElement.style.display = view === 'cards' ? 'block' : 'none';
    
    if (view === 'charts') {
        updateRepoFilterOptions();
        fetchAndRenderCharts();
    }
}

// Chart Data Management
async function fetchChartData(days = 30, repo = null) {
    try {
        let url = `/chart-data?days=${days}`;
        if (repo) {
            url += `&repo=${encodeURIComponent(repo)}`;
        }
        return await api.get(url);
    } catch (error) {
        console.error('Error fetching chart data:', error);
        throw error;
    }
}

function updateRepoFilterOptions() {
    // Clear existing options except "All repositories"
    repoFilter.innerHTML = '<option value="">All repositories</option>';
    
    // Add options for each repository
    allRepos.forEach(repo => {
        const option = document.createElement('option');
        option.value = repo.name;
        option.textContent = repo.name;
        repoFilter.appendChild(option);
    });
}

// Chart Rendering
function createChart(container, data, repoName) {
    const canvas = document.createElement('canvas');
    container.appendChild(canvas);
    
    const ctx = canvas.getContext('2d');
    
    // Get theme colors
    const computedStyle = getComputedStyle(document.documentElement);
    const accentColor = computedStyle.getPropertyValue('--accent').trim();
    const uniquesColor = '#10b981';
    const textColor = computedStyle.getPropertyValue('--text-primary').trim();
    const gridColor = computedStyle.getPropertyValue('--border').trim();
    
    const chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.labels,
            datasets: [
                {
                    label: 'Total Clones',
                    data: data.clones,
                    borderColor: accentColor,
                    backgroundColor: accentColor + '20',
                    fill: false,
                    tension: 0.3,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                },
                {
                    label: 'Unique Clones',
                    data: data.uniques,
                    borderColor: uniquesColor,
                    backgroundColor: uniquesColor + '20',
                    fill: false,
                    tension: 0.3,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                intersect: false,
                mode: 'index'
            },
            plugins: {
                legend: {
                    display: false // We'll use custom legend in the header
                },
                tooltip: {
                    backgroundColor: computedStyle.getPropertyValue('--bg-primary').trim(),
                    titleColor: textColor,
                    bodyColor: textColor,
                    borderColor: gridColor,
                    borderWidth: 1,
                    cornerRadius: 8,
                    displayColors: true,
                    titleAlign: 'left',
                    bodyAlign: 'left'
                }
            },
            scales: {
                x: {
                    grid: {
                        color: gridColor,
                        borderColor: gridColor
                    },
                    ticks: {
                        color: textColor,
                        maxTicksLimit: 7
                    }
                },
                y: {
                    beginAtZero: true,
                    grid: {
                        color: gridColor,
                        borderColor: gridColor
                    },
                    ticks: {
                        color: textColor,
                        callback: function(value) {
                            return Number.isInteger(value) ? value : '';
                        }
                    }
                }
            }
        }
    });
    
    return chart;
}

async function fetchAndRenderCharts() {
    try {
        showChartLoading(true);
        
        const days = parseInt(timeFilter.value);
        const selectedRepo = repoFilter.value;
        
        const chartData = await fetchChartData(days, selectedRepo);
        renderCharts(chartData);
        
    } catch (error) {
        console.error('Error rendering charts:', error);
        showToast('Failed to load chart data', 'error');
    } finally {
        showChartLoading(false);
    }
}

function renderCharts(chartData) {
    // Clean up existing charts
    chartInstances.forEach(chart => chart.destroy());
    chartInstances.clear();
    
    // Clear wrapper
    chartsWrapper.innerHTML = '';
    
    const repos = chartData.chart_data;
    const repoNames = Object.keys(repos);
    
    if (repoNames.length === 0) {
        chartsWrapper.innerHTML = `
            <div class="empty-chart">
                <i class="fas fa-chart-line"></i>
                <h3>No chart data available</h3>
                <p>Try adjusting your time period or repository filter, or sync your data first.</p>
            </div>
        `;
        return;
    }
    
    repoNames.forEach(repoName => {
        const repoData = repos[repoName];
        
        if (repoData.labels.length === 0) {
            return; // Skip repositories with no data
        }
        
        // Calculate totals for this period
        const totalClones = repoData.clones.reduce((sum, count) => sum + count, 0);
        const totalUniques = repoData.uniques.reduce((sum, count) => sum + count, 0);
        
        // Create chart container
        const chartItem = document.createElement('div');
        chartItem.className = 'chart-item';
        
        chartItem.innerHTML = `
            <div class="chart-header">
                <h3 class="chart-title">
                    <i class="fab fa-github"></i>
                    ${repoName}
                </h3>
                <div class="chart-stats">
                    <div class="chart-stat">
                        <div class="chart-stat-dot clones"></div>
                        Total Clones: ${totalClones.toLocaleString()}
                    </div>
                    <div class="chart-stat">
                        <div class="chart-stat-dot uniques"></div>
                        Unique Clones: ${totalUniques.toLocaleString()}
                    </div>
                </div>
            </div>
            <div class="chart-canvas-container"></div>
        `;
        
        chartsWrapper.appendChild(chartItem);
        
        // Create and store chart
        const canvasContainer = chartItem.querySelector('.chart-canvas-container');
        const chart = createChart(canvasContainer, repoData, repoName);
        chartInstances.set(repoName, chart);
    });
}

function showChartLoading(show) {
    chartLoading.style.display = show ? 'flex' : 'none';
    chartsWrapper.style.display = show ? 'none' : 'grid';
}

// DOM Elements
const reposContainer = document.getElementById('repos-container');
const loadingContainer = document.getElementById('loading');
const searchInput = document.getElementById('search-input');
const sortSelect = document.getElementById('sort-select');
const syncButton = document.getElementById('sync-button');
const manageReposButton = document.getElementById('manage-repos-button');
const repoModal = document.getElementById('repo-modal');
const modalClose = document.getElementById('modal-close');
const newRepoInput = document.getElementById('new-repo-input');
const addRepoBtn = document.getElementById('add-repo-btn');
const trackedReposList = document.getElementById('tracked-repos-list');
const exportBtn = document.getElementById('export-btn');
const importBtn = document.getElementById('import-btn');
const importFile = document.getElementById('import-file');
const replaceExisting = document.getElementById('replace-existing');
const totalReposEl = document.getElementById('total-repos');
const totalClonesEl = document.getElementById('total-clones');
const totalUniquesEl = document.getElementById('total-uniques');

// Chart view elements
const cardViewBtn = document.getElementById('card-view-btn');
const chartViewBtn = document.getElementById('chart-view-btn');
const chartControls = document.getElementById('chart-controls');
const chartContainer = document.getElementById('chart-container');
const chartLoading = document.getElementById('chart-loading');
const chartsWrapper = document.getElementById('charts-wrapper');
const timeFilter = document.getElementById('time-filter');
const repoFilter = document.getElementById('repo-filter');
const refreshChartBtn = document.getElementById('refresh-chart-btn');

// API Helper Functions
const api = {
    async get(url) {
        const response = await fetch(url);
        if (!response.ok) {
            const error = await response.text();
            throw new Error(error || `Request failed: ${response.status}`);
        }
        return response.json();
    },

    async post(url, data = {}) {
        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (!response.ok) {
            const error = await response.text();
            throw new Error(error || `Request failed: ${response.status}`);
        }
        return response.json();
    },

    async delete(url) {
        const response = await fetch(url, { method: 'DELETE' });
        if (!response.ok) {
            const error = await response.text();
            throw new Error(error || `Request failed: ${response.status}`);
        }
        return response.json();
    }
};

// Fetch Statistics
async function fetchStats() {
    try {
        showLoading(true);
        const data = await api.get('/stats');
        githubUsername = data.github_username || '';
        processStats(data.stats);
        updateHeroStats();
        renderRepos();
    } catch (error) {
        console.error('Error fetching stats:', error);
        showToast('Failed to load repository data', 'error');
    } finally {
        showLoading(false);
    }
}

function processStats(stats) {
    // Aggregate stats by repo
    const repos = stats.reduce((acc, record) => {
        if (!acc[record.repo]) {
            acc[record.repo] = {
                name: record.repo,
                total_clones: 0,
                total_uniques: 0,
                star_count: record.star_count || 0,
                history: []
            };
        }
        acc[record.repo].total_clones += record.count;
        acc[record.repo].total_uniques += record.uniques;
        acc[record.repo].history.push({
            timestamp: record.timestamp,
            clones: record.count,
            uniques: record.uniques
        });
        return acc;
    }, {});

    // Calculate date ranges for each repo
    Object.values(repos).forEach(repo => {
        if (repo.history.length > 0) {
            // Sort history by timestamp to ensure correct order
            repo.history.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
            
            repo.first_collected = repo.history[0].timestamp;
            repo.last_sync = repo.history[repo.history.length - 1].timestamp;
        }
    });

    allRepos = Object.values(repos);
    filteredRepos = [...allRepos];
}

function updateHeroStats() {
    const totalRepos = allRepos.length;
    const totalClones = allRepos.reduce((sum, repo) => sum + repo.total_clones, 0);
    const totalUniques = allRepos.reduce((sum, repo) => sum + repo.total_uniques, 0);

    animateNumber(totalReposEl, totalRepos);
    animateNumber(totalClonesEl, totalClones);
    animateNumber(totalUniquesEl, totalUniques);
}

function animateNumber(element, target) {
    const start = 0;
    const duration = 1000;
    const startTime = performance.now();

    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const current = Math.floor(start + (target - start) * easeOutQuart(progress));

        element.textContent = current.toLocaleString();

        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }

    requestAnimationFrame(update);
}

function easeOutQuart(t) {
    return 1 - (--t) * t * t * t;
}

// Render Repositories
function renderRepos() {
    reposContainer.innerHTML = '';

    if (filteredRepos.length === 0) {
        reposContainer.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-search" style="font-size: 3rem; color: var(--text-muted); margin-bottom: 1rem;"></i>
                <h3>No repositories found</h3>
                <p>Try adjusting your search or filters</p>
            </div>
        `;
        return;
    }

    filteredRepos.forEach((repo, index) => {
        const card = createRepoCard(repo, index);
        reposContainer.appendChild(card);
    });
}

function createRepoCard(repo, index) {
    const card = document.createElement('div');
    card.className = 'repo-card';
    card.style.animationDelay = `${index * 0.1}s`;

    const badgeUrl = `/badge/${repo.name}`;
    const markdownCode = `[![Clones](${window.location.origin}${badgeUrl})](https://github.com/${githubUsername}/${repo.name}/graphs/traffic)`;

    // Prepare template data
    const templateData = {
        repo: {
            name: repo.name,
            total_clones: repo.total_clones.toLocaleString(),
            total_uniques: repo.total_uniques.toLocaleString(),
            star_count: repo.star_count.toLocaleString(),
            first_collected_formatted: repo.first_collected ? formatDate(repo.first_collected) : 'N/A',
            last_sync_formatted: repo.last_sync ? formatDate(repo.last_sync) : 'N/A'
        },
        badgeUrl: badgeUrl,
        markdownCode: markdownCode
    };

    // Render template
    card.innerHTML = renderTemplate(repoCardTemplate, templateData);

    return card;
}

// Search and Filter
function filterRepos() {
    const searchTerm = searchInput.value.toLowerCase();

    filteredRepos = allRepos.filter(repo =>
        repo.name.toLowerCase().includes(searchTerm)
    );

    sortRepos();
}

function sortRepos() {
    const sortValue = sortSelect.value;

    filteredRepos.sort((a, b) => {
        switch (sortValue) {
            case 'name':
                return a.name.localeCompare(b.name);
            case 'clones-desc':
                return b.total_clones - a.total_clones;
            case 'clones-asc':
                return a.total_clones - b.total_clones;
            case 'uniques-desc':
                return b.total_uniques - a.total_uniques;
            case 'uniques-asc':
                return a.total_uniques - b.total_uniques;
            default:
                return 0;
        }
    });

    renderRepos();
}

// Copy to Clipboard
async function copyToClipboard(text, button) {
    try {
        await navigator.clipboard.writeText(text);

        const originalText = button.innerHTML;
        button.innerHTML = '<i class="fas fa-check"></i><span>Copied!</span>';
        button.style.background = 'var(--success)';
        button.style.color = 'white';

        setTimeout(() => {
            button.innerHTML = originalText;
            button.style.background = '';
            button.style.color = '';
        }, 2000);

        showToast('Markdown copied to clipboard!', 'success');
    } catch (err) {
        console.error('Failed to copy:', err);
        showToast('Failed to copy to clipboard', 'error');
    }
}

// Button Loading State Helper
async function withButtonLoading(button, loadingText, action) {
    const originalContent = button.innerHTML;
    button.disabled = true;
    button.innerHTML = `<i class="fas fa-spinner fa-spin"></i>${loadingText ? `<span>${loadingText}</span>` : ''}`;
    
    try {
        return await action();
    } finally {
        button.disabled = false;
        button.innerHTML = originalContent;
    }
}

// Sync Functionality
async function runSync() {
    await withButtonLoading(syncButton, 'Syncing...', async () => {
        try {
            const result = await api.post('/sync');
            showToast('Sync completed successfully!', 'success');
            await fetchStats();
        } catch (error) {
            console.error('Sync error:', error);
            showToast(error.message || 'Sync failed', 'error');
        }
    });
}

// Loading State
function showLoading(show) {
    loadingContainer.style.display = show ? 'flex' : 'none';
    reposContainer.style.display = show ? 'none' : 'grid';
}

// Repository Management Functions
async function fetchTrackedRepos() {
    try {
        const data = await api.get('/tracked-repos');
        return data.tracked_repos;
    } catch (error) {
        console.error('Error fetching tracked repos:', error);
        showToast('Failed to load tracked repositories', 'error');
        return [];
    }
}

async function addTrackedRepo(repoName) {
    try {
        const result = await api.post('/tracked-repos', { repo_name: repoName });
        showToast(result.message, 'success');
        return true;
    } catch (error) {
        console.error('Error adding repo:', error);
        showToast(`Failed to add repository: ${error.message}`, 'error');
        return false;
    }
}

async function removeTrackedRepo(repoName) {
    try {
        const result = await api.delete(`/tracked-repos/${repoName}`);
        showToast(result.message, 'success');
        return true;
    } catch (error) {
        console.error('Error removing repo:', error);
        showToast(`Failed to remove repository: ${error.message}`, 'error');
        return false;
    }
}

function renderTrackedRepos(repos) {
    if (repos.length === 0) {
        trackedReposList.innerHTML = `
            <div class="empty-repos">
                <i class="fas fa-inbox" style="font-size: 2rem; margin-bottom: 1rem; color: var(--text-muted);"></i>
                <p>No repositories are currently being tracked.</p>
                <p style="font-size: 0.9rem; color: var(--text-muted);">Add a repository above to start tracking its clone statistics.</p>
            </div>
        `;
        return;
    }

    trackedReposList.innerHTML = repos.map(repo => `
        <div class="tracked-repo-item">
            <span class="repo-name">${repo}</span>
            <button class="btn btn-danger btn-sm remove-btn" onclick="handleRemoveRepo('${repo}')">
                <i class="fas fa-trash"></i>
                Remove
            </button>
        </div>
    `).join('');
}

async function loadTrackedRepos() {
    trackedReposList.innerHTML = `
        <div class="loading-repos">
            <i class="fas fa-spinner fa-spin"></i>
            Loading tracked repositories...
        </div>
    `;
    
    const repos = await fetchTrackedRepos();
    renderTrackedRepos(repos);
}

async function handleAddRepo() {
    const repoName = newRepoInput.value.trim();
    if (!repoName) {
        showToast('Please enter a repository name', 'error');
        return;
    }

    // Validate repository name format
    if (!/^[a-zA-Z0-9\-_\.]+$/.test(repoName)) {
        showToast('Repository name can only contain letters, numbers, hyphens, underscores, and dots', 'error');
        return;
    }

    await withButtonLoading(addRepoBtn, ' Adding...', async () => {
        const success = await addTrackedRepo(repoName);
        if (success) {
            newRepoInput.value = '';
            await loadTrackedRepos();
        }
    });
}

async function handleRemoveRepo(repoName) {
    if (!confirm(`Are you sure you want to stop tracking "${repoName}"? This will not delete existing data.`)) {
        return;
    }

    const success = await removeTrackedRepo(repoName);
    if (success) {
        await loadTrackedRepos();
    }
}

function showModal() {
    repoModal.classList.add('show');
    loadTrackedRepos();
    document.body.style.overflow = 'hidden';
}

function hideModal() {
    repoModal.classList.remove('show');
    document.body.style.overflow = '';
}

// Export/Import Functions
async function exportDatabase() {
    await withButtonLoading(exportBtn, ' Exporting...', async () => {
        try {
            const response = await fetch('/export');
            if (!response.ok) throw new Error('Export failed');

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            
            // Get filename from response headers or use default
            const contentDisposition = response.headers.get('Content-Disposition');
            const filename = contentDisposition 
                ? contentDisposition.split('filename=')[1].replace(/"/g, '')
                : `github_stats_backup_${new Date().toISOString().split('T')[0]}.json`;
            
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);

            showToast('Database exported successfully!', 'success');
        } catch (error) {
            console.error('Export error:', error);
            showToast('Failed to export database', 'error');
        }
    });
}

async function importDatabase(file, replaceExisting) {
    try {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('replace_existing', replaceExisting.toString());

        const response = await fetch('/import', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();
        
        if (response.ok) {
            showToast('Database imported successfully!', 'success');
            // Refresh the UI
            await fetchStats();
            await loadTrackedRepos();
        } else {
            throw new Error(result.message || 'Import failed');
        }
    } catch (error) {
        console.error('Import error:', error);
        showToast(`Failed to import database: ${error.message}`, 'error');
    }
}

function handleImportClick() {
    importFile.click();
}

async function handleFileSelect(event) {
    const file = event.target.files[0];
    if (!file) return;

    if (!file.name.endsWith('.json')) {
        showToast('Please select a JSON file', 'error');
        return;
    }

    const shouldReplace = replaceExisting.checked;
    
    if (shouldReplace) {
        const confirmed = confirm(
            'Warning: This will replace ALL existing data in the database. ' +
            'This action cannot be undone. Are you sure you want to continue?'
        );
        if (!confirmed) {
            importFile.value = '';
            return;
        }
    }

    await withButtonLoading(importBtn, ' Importing...', async () => {
        try {
            await importDatabase(file, shouldReplace);
        } finally {
            importFile.value = '';
        }
    });
}

// Event Listeners
searchInput.addEventListener('input', filterRepos);
sortSelect.addEventListener('change', sortRepos);
syncButton.addEventListener('click', runSync);
manageReposButton.addEventListener('click', showModal);
modalClose.addEventListener('click', hideModal);
addRepoBtn.addEventListener('click', handleAddRepo);
exportBtn.addEventListener('click', exportDatabase);
importBtn.addEventListener('click', handleImportClick);
importFile.addEventListener('change', handleFileSelect);

// Chart view event listeners
cardViewBtn.addEventListener('click', () => switchView('cards'));
chartViewBtn.addEventListener('click', () => switchView('charts'));
timeFilter.addEventListener('change', fetchAndRenderCharts);
repoFilter.addEventListener('change', fetchAndRenderCharts);
refreshChartBtn.addEventListener('click', fetchAndRenderCharts);

// Close modal when clicking outside
repoModal.addEventListener('click', (e) => {
    if (e.target === repoModal) {
        hideModal();
    }
});

// Handle Enter key in repo input
newRepoInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        handleAddRepo();
    }
});

// Close modal with Escape key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && repoModal.classList.contains('show')) {
        hideModal();
    }
});

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    initTheme();
    await loadTemplate();
    fetchStats();
});

// Auto-refresh every 5 minutes
setInterval(() => {
    fetchStats();
}, 5 * 60 * 1000);

// Handle visibility change for performance
document.addEventListener('visibilitychange', () => {
    if (!document.hidden) {
        fetchStats();
    }
});
