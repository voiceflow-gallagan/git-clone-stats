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

// DOM Elements
const reposContainer = document.getElementById('repos-container');
const loadingContainer = document.getElementById('loading');
const searchInput = document.getElementById('search-input');
const sortSelect = document.getElementById('sort-select');
const syncButton = document.getElementById('sync-button');
const totalReposEl = document.getElementById('total-repos');
const totalClonesEl = document.getElementById('total-clones');
const totalUniquesEl = document.getElementById('total-uniques');

// Fetch Statistics
async function fetchStats() {
    try {
        showLoading(true);
        const response = await fetch('/stats');
        if (!response.ok) throw new Error('Failed to fetch stats');

        const data = await response.json();
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

    card.innerHTML = `
        <div class="repo-header">
            <div class="repo-icon">
                <i class="fab fa-github"></i>
            </div>
            <h3 class="repo-name">${repo.name}</h3>
        </div>

        <div class="repo-stats">
            <div class="stat-item">
                <div class="stat-number">${repo.total_clones.toLocaleString()}</div>
                <div class="stat-label-small">Total Clones</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">${repo.total_uniques.toLocaleString()}</div>
                <div class="stat-label-small">Unique Cloners</div>
            </div>
        </div>

        <div class="badge-container">
            <img src="${badgeUrl}" alt="Clone badge for ${repo.name}" style="max-width: 100%;">
        </div>

        <button class="copy-btn" onclick="copyToClipboard('${markdownCode}', this)">
            <i class="fas fa-copy"></i>
            <span>Copy Markdown</span>
        </button>
    `;

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

// Sync Functionality
async function runSync() {
    const button = syncButton;
    const originalText = button.innerHTML;

    button.disabled = true;
    button.innerHTML = '<i class="fas fa-spinner fa-spin"></i><span>Syncing...</span>';

    try {
        const response = await fetch('/sync', { method: 'POST' });
        const result = await response.json();

        if (response.ok) {
            showToast('Sync completed successfully!', 'success');
            await fetchStats();
        } else {
            throw new Error(result.message || 'Sync failed');
        }
    } catch (error) {
        console.error('Sync error:', error);
        showToast(error.message || 'Sync failed', 'error');
    } finally {
        button.disabled = false;
        button.innerHTML = originalText;
    }
}

// Loading State
function showLoading(show) {
    loadingContainer.style.display = show ? 'flex' : 'none';
    reposContainer.style.display = show ? 'none' : 'grid';
}

// Event Listeners
searchInput.addEventListener('input', filterRepos);
sortSelect.addEventListener('change', sortRepos);
syncButton.addEventListener('click', runSync);

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initTheme();
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
