/**
 * Advanced Filtering Module for Phase 4
 * Date ranges, severity filters, threshold sliders, filter presets
 */

class AdvancedFiltering {
    constructor() {
        this.currentFilters = {
            dateRange: '30days',
            severity: 'all',
            status: 'all',
            healthScoreMin: 0,
            healthScoreMax: 100,
            staleItemsMax: 100
        };
        this.presets = [];
        this.loadPresets();
    }

    async loadPresets() {
        try {
            const response = await fetch('/api/filters/presets');
            if (response.ok) {
                this.presets = await response.json();
            }
        } catch (error) {
            console.error('Error loading filter presets:', error);
        }
    }

    async savePreset(name, filters) {
        try {
            const response = await fetch('/api/filters/presets', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ name, filters })
            });
            if (response.ok) {
                await this.loadPresets();
                return true;
            }
        } catch (error) {
            console.error('Error saving filter preset:', error);
        }
        return false;
    }

    async deletePreset(presetId) {
        try {
            const response = await fetch(`/api/filters/presets/${presetId}`, {
                method: 'DELETE'
            });
            if (response.ok) {
                await this.loadPresets();
                return true;
            }
        } catch (error) {
            console.error('Error deleting filter preset:', error);
        }
        return false;
    }

    async applyPreset(presetId) {
        try {
            const response = await fetch(`/api/filters/presets/${presetId}`);
            if (response.ok) {
                const preset = await response.json();
                const filters = JSON.parse(preset.filters || '{}');
                this.currentFilters = {...this.currentFilters, ...filters};
                return true;
            }
        } catch (error) {
            console.error('Error applying filter preset:', error);
        }
        return false;
    }

    setDateRange(range) {
        this.currentFilters.dateRange = range;
    }

    setSeverityFilter(severity) {
        this.currentFilters.severity = severity;
    }

    setStatusFilter(status) {
        this.currentFilters.status = status;
    }

    setHealthScoreRange(min, max) {
        this.currentFilters.healthScoreMin = min;
        this.currentFilters.healthScoreMax = max;
    }

    setStaleItemsMax(max) {
        this.currentFilters.staleItemsMax = max;
    }

    clearAllFilters() {
        this.currentFilters = {
            dateRange: '30days',
            severity: 'all',
            status: 'all',
            healthScoreMin: 0,
            healthScoreMax: 100,
            staleItemsMax: 100
        };
    }

    getActiveFilterCount() {
        let count = 0;
        if (this.currentFilters.dateRange !== '30days') count++;
        if (this.currentFilters.severity !== 'all') count++;
        if (this.currentFilters.status !== 'all') count++;
        if (this.currentFilters.healthScoreMin > 0 || this.currentFilters.healthScoreMax < 100) count++;
        if (this.currentFilters.staleItemsMax < 100) count++;
        return count;
    }

    exportFiltersAsUrl() {
        const params = new URLSearchParams();
        Object.entries(this.currentFilters).forEach(([key, value]) => {
            params.append(key, value);
        });
        return window.location.origin + window.location.pathname + '?' + params.toString();
    }

    importFiltersFromUrl() {
        const params = new URLSearchParams(window.location.search);
        for (let [key, value] of params.entries()) {
            if (key in this.currentFilters) {
                this.currentFilters[key] = isNaN(value) ? value : parseFloat(value);
            }
        }
    }
}

// Global instance
const advancedFiltering = new AdvancedFiltering();


// ============================================================================
// ADVANCED FILTER UI
// ============================================================================

function openAdvancedFilterModal() {
    const bodyHtml = `
        <div class="advanced-filter-panel">
            <!-- Date Range Filter -->
            <div class="filter-section">
                <h5>📅 Date Range</h5>
                <div class="date-range-buttons">
                    <button class="filter-btn ${advancedFiltering.currentFilters.dateRange === '7days' ? 'active' : ''}"
                            onclick="setDateRange('7days')">Last 7 Days</button>
                    <button class="filter-btn ${advancedFiltering.currentFilters.dateRange === '30days' ? 'active' : ''}"
                            onclick="setDateRange('30days')">Last 30 Days</button>
                    <button class="filter-btn ${advancedFiltering.currentFilters.dateRange === '90days' ? 'active' : ''}"
                            onclick="setDateRange('90days')">Last 90 Days</button>
                    <button class="filter-btn ${advancedFiltering.currentFilters.dateRange === 'all' ? 'active' : ''}"
                            onclick="setDateRange('all')">All Time</button>
                </div>
            </div>

            <!-- Severity Filter -->
            <div class="filter-section">
                <h5>🚨 Severity Level</h5>
                <div class="severity-checkboxes">
                    <label class="filter-check">
                        <input type="checkbox" value="critical"
                               ${advancedFiltering.currentFilters.severity === 'all' || advancedFiltering.currentFilters.severity.includes('critical') ? 'checked' : ''}
                               onchange="updateSeverityFilter()">
                        <span class="severity-dot critical"></span> Critical
                    </label>
                    <label class="filter-check">
                        <input type="checkbox" value="high"
                               ${advancedFiltering.currentFilters.severity === 'all' || advancedFiltering.currentFilters.severity.includes('high') ? 'checked' : ''}
                               onchange="updateSeverityFilter()">
                        <span class="severity-dot high"></span> High
                    </label>
                    <label class="filter-check">
                        <input type="checkbox" value="medium"
                               ${advancedFiltering.currentFilters.severity === 'all' || advancedFiltering.currentFilters.severity.includes('medium') ? 'checked' : ''}
                               onchange="updateSeverityFilter()">
                        <span class="severity-dot medium"></span> Medium
                    </label>
                    <label class="filter-check">
                        <input type="checkbox" value="low"
                               ${advancedFiltering.currentFilters.severity === 'all' || advancedFiltering.currentFilters.severity.includes('low') ? 'checked' : ''}
                               onchange="updateSeverityFilter()">
                        <span class="severity-dot low"></span> Low
                    </label>
                </div>
            </div>

            <!-- Status Filter -->
            <div class="filter-section">
                <h5>📊 Status</h5>
                <select id="statusFilter" class="form-control" onchange="updateStatusFilter()">
                    <option value="all">All Statuses</option>
                    <option value="open" ${advancedFiltering.currentFilters.status === 'open' ? 'selected' : ''}>Open</option>
                    <option value="acknowledged" ${advancedFiltering.currentFilters.status === 'acknowledged' ? 'selected' : ''}>Acknowledged</option>
                    <option value="resolved" ${advancedFiltering.currentFilters.status === 'resolved' ? 'selected' : ''}>Resolved</option>
                </select>
            </div>

            <!-- Health Score Range -->
            <div class="filter-section">
                <h5>❤️ Health Score Range</h5>
                <div class="slider-container">
                    <input type="range" id="healthMin" class="range-slider"
                           min="0" max="100" value="${advancedFiltering.currentFilters.healthScoreMin}"
                           oninput="updateHealthScoreRange()">
                    <input type="range" id="healthMax" class="range-slider"
                           min="0" max="100" value="${advancedFiltering.currentFilters.healthScoreMax}"
                           oninput="updateHealthScoreRange()">
                    <div class="slider-values">
                        <span id="healthMinLabel">${advancedFiltering.currentFilters.healthScoreMin}</span>
                        <span> - </span>
                        <span id="healthMaxLabel">${advancedFiltering.currentFilters.healthScoreMax}</span>
                    </div>
                </div>
            </div>

            <!-- Stale Items Threshold -->
            <div class="filter-section">
                <h5>⏱️ Stale Items Max</h5>
                <div class="slider-container">
                    <input type="range" id="staleMax" class="range-slider"
                           min="0" max="500" step="10" value="${advancedFiltering.currentFilters.staleItemsMax}"
                           oninput="updateStaleItemsMax()">
                    <div class="slider-value">
                        <span id="staleMaxLabel">${advancedFiltering.currentFilters.staleItemsMax}</span>
                    </div>
                </div>
            </div>

            <!-- Filter Presets -->
            <div class="filter-section">
                <h5>⭐ Saved Presets</h5>
                <div class="preset-selector">
                    <select id="presetSelect" class="form-control" onchange="applyFilterPreset()">
                        <option value="">Select a preset...</option>
                        ${advancedFiltering.presets.map(p =>
                            `<option value="${p.preset_id}">${p.name}</option>`
                        ).join('')}
                    </select>
                    <button class="btn btn-sm btn-outline-primary" onclick="saveCurrentFilterAsPreset()">
                        💾 Save Current
                    </button>
                </div>
            </div>

            <!-- Filter Actions -->
            <div class="filter-actions">
                <button class="btn btn-primary" onclick="applyAllFilters()">
                    🔍 Apply Filters
                </button>
                <button class="btn btn-secondary" onclick="clearAllFilters()">
                    ✖️ Clear All
                </button>
                <button class="btn btn-outline-secondary" onclick="shareFilterUrl()">
                    🔗 Share URL
                </button>
                <span class="filter-count" id="filterCount">
                    ${advancedFiltering.getActiveFilterCount()} active filter${advancedFiltering.getActiveFilterCount() !== 1 ? 's' : ''}
                </span>
            </div>
        </div>
    `;

    createModal('Advanced Filtering', bodyHtml, applyAllFilters);
}

function setDateRange(range) {
    advancedFiltering.setDateRange(range);
    document.querySelectorAll('.date-range-buttons .filter-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.classList.add('active');
}

function updateSeverityFilter() {
    const checked = Array.from(document.querySelectorAll('.severity-checkboxes input:checked'))
        .map(cb => cb.value);
    advancedFiltering.setSeverityFilter(checked.length === 0 ? 'all' : checked.join(','));
}

function updateStatusFilter() {
    const status = document.getElementById('statusFilter').value;
    advancedFiltering.setStatusFilter(status);
}

function updateHealthScoreRange() {
    const min = parseInt(document.getElementById('healthMin').value);
    const max = parseInt(document.getElementById('healthMax').value);

    if (min > max) {
        document.getElementById('healthMin').value = max;
        document.getElementById('healthMax').value = min;
        advancedFiltering.setHealthScoreRange(max, min);
    } else {
        advancedFiltering.setHealthScoreRange(min, max);
    }

    document.getElementById('healthMinLabel').textContent = Math.min(min, max);
    document.getElementById('healthMaxLabel').textContent = Math.max(min, max);
}

function updateStaleItemsMax() {
    const max = parseInt(document.getElementById('staleMax').value);
    advancedFiltering.setStaleItemsMax(max);
    document.getElementById('staleMaxLabel').textContent = max;
}

function applyFilterPreset() {
    const presetId = document.getElementById('presetSelect').value;
    if (presetId) {
        advancedFiltering.applyPreset(presetId).then(() => {
            showToast('Filter preset applied!', 'success');
        });
    }
}

function saveCurrentFilterAsPreset() {
    const name = prompt('Enter preset name (e.g., "Critical Only", "Last 7 Days - High Priority"):');
    if (!name) return;

    advancedFiltering.savePreset(name, advancedFiltering.currentFilters).then(() => {
        showToast(`Preset "${name}" saved!`, 'success');
        // Reload the modal
        closePhase4Modal();
        setTimeout(openAdvancedFilterModal, 100);
    });
}

function applyAllFilters() {
    updateSeverityFilter();
    updateStatusFilter();
    updateHealthScoreRange();
    updateStaleItemsMax();

    closePhase4Modal();
    showToast('Filters applied! Results updated.', 'success');

    // Here you would filter the dashboard data
    // Example: filterDashboardData(advancedFiltering.currentFilters);

    document.getElementById('filterCount').textContent =
        `${advancedFiltering.getActiveFilterCount()} active filter${advancedFiltering.getActiveFilterCount() !== 1 ? 's' : ''}`;
}

function clearAllFilters() {
    if (!confirm('Clear all filters?')) return;

    advancedFiltering.clearAllFilters();
    closePhase4Modal();
    showToast('All filters cleared', 'success');

    // Reset dashboard to show all data
    // Example: filterDashboardData({});
}

function shareFilterUrl() {
    const url = advancedFiltering.exportFiltersAsUrl();
    const textarea = document.createElement('textarea');
    textarea.value = url;
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand('copy');
    document.body.removeChild(textarea);

    showToast('Filter URL copied to clipboard!', 'success');
}

function addAdvancedFilterButton() {
    const container = document.getElementById('advancedFilterContainer');
    if (!container) return;

    const html = `
        <button class="btn btn-sm btn-outline-primary" onclick="openAdvancedFilterModal()">
            🔍 Advanced Filters
            <span id="activeFilterBadge" class="badge badge-primary" style="display: none;">0</span>
        </button>
    `;

    container.innerHTML = html;
    updateFilterBadge();
}

function updateFilterBadge() {
    const badge = document.getElementById('activeFilterBadge');
    const count = advancedFiltering.getActiveFilterCount();
    if (count > 0) {
        badge.textContent = count;
        badge.style.display = 'inline-block';
    } else {
        badge.style.display = 'none';
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    addAdvancedFilterButton();
    advancedFiltering.importFiltersFromUrl();
    console.log('Advanced Filtering module loaded');
});
