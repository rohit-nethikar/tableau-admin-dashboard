/**
 * Phase 4 Advanced Features Frontend
 * Handles UI for preferences, dashboards, alerts, filtering, and exports
 */

// ============================================================================
// USER PREFERENCES
// ============================================================================

class UserPreferences {
    constructor() {
        this.preferences = {};
        this.loadPreferences();
    }

    async loadPreferences() {
        try {
            const response = await fetch('/api/preferences');
            if (response.ok) {
                this.preferences = await response.json();
            }
        } catch (error) {
            console.error('Error loading preferences:', error);
        }
    }

    async save() {
        try {
            const response = await fetch('/api/preferences', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(this.preferences)
            });
            if (response.ok) {
                console.log('Preferences saved');
            }
        } catch (error) {
            console.error('Error saving preferences:', error);
        }
    }

    async setDarkMode(enabled) {
        try {
            const response = await fetch('/api/preferences/dark-mode', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ enabled })
            });
            if (response.ok) {
                this.preferences.dark_mode = enabled ? 1 : 0;
            }
        } catch (error) {
            console.error('Error setting dark mode:', error);
        }
    }

    async setNotificationEmail(email) {
        try {
            await fetch('/api/preferences', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ notification_email: email })
            });
            this.preferences.notification_email = email;
        } catch (error) {
            console.error('Error setting notification email:', error);
        }
    }
}

// Global instance
const userPreferences = new UserPreferences();


// ============================================================================
// EXPORT FUNCTIONALITY
// ============================================================================

class ExportManager {
    static async exportToCSV(metrics, filters = null) {
        try {
            const response = await fetch('/api/export/csv', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ metrics, filters })
            });
            if (response.ok) {
                const blob = await response.blob();
                ExportManager.downloadFile(blob, 'metrics.csv', 'text/csv');
            }
        } catch (error) {
            console.error('Error exporting to CSV:', error);
            alert('Failed to export CSV');
        }
    }

    static async exportToExcel(metrics, findings = []) {
        try {
            const response = await fetch('/api/export/excel', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ metrics, findings })
            });
            if (response.ok) {
                const blob = await response.blob();
                ExportManager.downloadFile(blob, 'dashboard.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
            }
        } catch (error) {
            console.error('Error exporting to Excel:', error);
            alert('Failed to export Excel');
        }
    }

    static async exportFindings(findings) {
        try {
            const response = await fetch('/api/export/findings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ findings })
            });
            if (response.ok) {
                const blob = await response.blob();
                ExportManager.downloadFile(blob, 'findings.csv', 'text/csv');
            }
        } catch (error) {
            console.error('Error exporting findings:', error);
            alert('Failed to export findings');
        }
    }

    static downloadFile(blob, filename, mimeType) {
        const url = window.URL.createObjectURL(new Blob([blob], { type: mimeType }));
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
    }
}


// ============================================================================
// DASHBOARD CONFIGURATIONS
// ============================================================================

class DashboardManager {
    constructor() {
        this.dashboards = [];
        this.currentDashboard = null;
        this.loadDashboards();
    }

    async loadDashboards() {
        try {
            const response = await fetch('/api/dashboards');
            if (response.ok) {
                this.dashboards = await response.json();
            }
        } catch (error) {
            console.error('Error loading dashboards:', error);
        }
    }

    async createDashboard(name, filters = {}, metricSelection = []) {
        try {
            const response = await fetch('/api/dashboards', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, filters, metric_selection: metricSelection })
            });
            if (response.ok) {
                const { config_id } = await response.json();
                await this.loadDashboards();
                return config_id;
            }
        } catch (error) {
            console.error('Error creating dashboard:', error);
        }
    }

    async updateDashboard(configId, updates) {
        try {
            const response = await fetch(`/api/dashboards/${configId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(updates)
            });
            if (response.ok) {
                await this.loadDashboards();
            }
        } catch (error) {
            console.error('Error updating dashboard:', error);
        }
    }

    async deleteDashboard(configId) {
        try {
            const response = await fetch(`/api/dashboards/${configId}`, {
                method: 'DELETE'
            });
            if (response.ok) {
                await this.loadDashboards();
            }
        } catch (error) {
            console.error('Error deleting dashboard:', error);
        }
    }

    async setDefault(configId) {
        try {
            const response = await fetch(`/api/dashboards/${configId}/set-default`, {
                method: 'POST'
            });
            if (response.ok) {
                await this.loadDashboards();
            }
        } catch (error) {
            console.error('Error setting default dashboard:', error);
        }
    }

    getDashboardNames() {
        return this.dashboards.map(d => ({ id: d.config_id, name: d.name }));
    }
}

const dashboardManager = new DashboardManager();


// ============================================================================
// ALERT RULES
// ============================================================================

class AlertManager {
    constructor() {
        this.rules = [];
        this.history = {};
        this.loadRules();
    }

    async loadRules() {
        try {
            const response = await fetch('/api/alerts/rules');
            if (response.ok) {
                this.rules = await response.json();
            }
        } catch (error) {
            console.error('Error loading alert rules:', error);
        }
    }

    async createRule(name, metric, condition, threshold, action) {
        try {
            const response = await fetch('/api/alerts/rules', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, metric, condition, threshold, action })
            });
            if (response.ok) {
                await this.loadRules();
                return await response.json();
            }
        } catch (error) {
            console.error('Error creating alert rule:', error);
        }
    }

    async updateRule(ruleId, updates) {
        try {
            const response = await fetch(`/api/alerts/rules/${ruleId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(updates)
            });
            if (response.ok) {
                await this.loadRules();
            }
        } catch (error) {
            console.error('Error updating alert rule:', error);
        }
    }

    async deleteRule(ruleId) {
        try {
            const response = await fetch(`/api/alerts/rules/${ruleId}`, {
                method: 'DELETE'
            });
            if (response.ok) {
                await this.loadRules();
            }
        } catch (error) {
            console.error('Error deleting alert rule:', error);
        }
    }

    async enableRule(ruleId) {
        await fetch(`/api/alerts/rules/${ruleId}/enable`, { method: 'POST' });
        await this.loadRules();
    }

    async disableRule(ruleId) {
        await fetch(`/api/alerts/rules/${ruleId}/disable`, { method: 'POST' });
        await this.loadRules();
    }

    async getHistory(ruleId, limit = 50) {
        try {
            const response = await fetch(`/api/alerts/history/${ruleId}?limit=${limit}`);
            if (response.ok) {
                this.history[ruleId] = await response.json();
                return this.history[ruleId];
            }
        } catch (error) {
            console.error('Error loading alert history:', error);
        }
    }

    async getActiveAlerts() {
        try {
            const response = await fetch('/api/alerts/active');
            if (response.ok) {
                return await response.json();
            }
        } catch (error) {
            console.error('Error loading active alerts:', error);
        }
    }

    getRulesByMetric(metric) {
        return this.rules.filter(r => r.metric === metric && r.enabled);
    }
}

const alertManager = new AlertManager();


// ============================================================================
// FILTER PRESETS
// ============================================================================

class FilterPresetManager {
    constructor() {
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
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, filters })
            });
            if (response.ok) {
                await this.loadPresets();
                return await response.json();
            }
        } catch (error) {
            console.error('Error saving filter preset:', error);
        }
    }

    async deletePreset(presetId) {
        try {
            const response = await fetch(`/api/filters/presets/${presetId}`, {
                method: 'DELETE'
            });
            if (response.ok) {
                await this.loadPresets();
            }
        } catch (error) {
            console.error('Error deleting filter preset:', error);
        }
    }

    async applyPreset(presetId) {
        try {
            const response = await fetch(`/api/filters/presets/${presetId}`);
            if (response.ok) {
                const preset = await response.json();
                return JSON.parse(preset.filters || '{}');
            }
        } catch (error) {
            console.error('Error applying filter preset:', error);
        }
    }

    getPresetNames() {
        return this.presets.map(p => ({ id: p.preset_id, name: p.name }));
    }
}

const filterPresetManager = new FilterPresetManager();


// ============================================================================
// EXPORT BUTTONS - Add to dashboard
// ============================================================================

function addExportButtons() {
    const exportContainer = document.getElementById('exportButtonsContainer');
    if (!exportContainer) return;

    const csvBtn = document.createElement('button');
    csvBtn.className = 'btn primary small';
    csvBtn.textContent = '📥 Export CSV';
    csvBtn.onclick = async () => {
        const metrics = window.currentMetrics || {};
        await ExportManager.exportToCSV(metrics);
    };

    const excelBtn = document.createElement('button');
    excelBtn.className = 'btn primary small';
    excelBtn.textContent = '📥 Export Excel';
    excelBtn.onclick = async () => {
        const metrics = window.currentMetrics || {};
        const findings = window.currentFindings || [];
        await ExportManager.exportToExcel(metrics, findings);
    };

    exportContainer.appendChild(csvBtn);
    exportContainer.appendChild(excelBtn);
}


// ============================================================================
// PREFERENCES MODAL
// ============================================================================

function openPreferencesModal() {
    const modalHtml = `
        <div class="preferences-modal">
            <h3>Dashboard Preferences</h3>

            <div class="pref-section">
                <label>
                    <input type="checkbox" id="darkModeToggle"
                           ${userPreferences.preferences.dark_mode ? 'checked' : ''}>
                    Dark Mode
                </label>
            </div>

            <div class="pref-section">
                <label>Notification Email:</label>
                <input type="email" id="notificationEmail"
                       value="${userPreferences.preferences.notification_email || ''}"
                       placeholder="your@email.com">
            </div>

            <div class="pref-section">
                <label>
                    <input type="checkbox" id="notificationsEnabled"
                           ${userPreferences.preferences.notifications_enabled ? 'checked' : ''}>
                    Enable Notifications
                </label>
            </div>

            <div class="pref-actions">
                <button class="btn primary" onclick="savePreferences()">Save</button>
                <button class="btn" onclick="closeModal()">Cancel</button>
            </div>
        </div>
    `;

    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.innerHTML = modalHtml;
    document.body.appendChild(modal);

    document.getElementById('darkModeToggle').addEventListener('change', async (e) => {
        await userPreferences.setDarkMode(e.target.checked);
    });
}

async function savePreferences() {
    const email = document.getElementById('notificationEmail').value;
    const enabled = document.getElementById('notificationsEnabled').checked;

    if (email) {
        await userPreferences.setNotificationEmail(email);
    }

    await userPreferences.save();
    closeModal();
    alert('Preferences saved!');
}


// ============================================================================
// DASHBOARD SELECTOR
// ============================================================================

function renderDashboardSelector() {
    const selector = document.getElementById('dashboardSelector');
    if (!selector) return;

    selector.innerHTML = `
        <select id="dashboardDropdown" onchange="switchDashboard()">
            <option value="">-- Default Dashboard --</option>
            ${dashboardManager.dashboards.map(d =>
                `<option value="${d.config_id}">${d.name}</option>`
            ).join('')}
        </select>
        <button class="btn small" onclick="openDashboardEditor()">⚙️ Edit</button>
    `;
}

function switchDashboard() {
    const select = document.getElementById('dashboardDropdown');
    const configId = select.value;
    if (configId) {
        dashboardManager.currentDashboard = configId;
        console.log('Switched to dashboard:', configId);
        // Load dashboard-specific filters/metrics
    }
}

function openDashboardEditor() {
    // TODO: Implement dashboard editor modal
    alert('Dashboard editor coming soon!');
}


// ============================================================================
// INITIALIZATION
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    addExportButtons();
    renderDashboardSelector();
    console.log('Phase 4 modules loaded');
});
