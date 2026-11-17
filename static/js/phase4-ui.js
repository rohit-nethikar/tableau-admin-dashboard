/**
 * Phase 4 UI Components
 * Modals, forms, and interactive elements for advanced features
 */

// ============================================================================
// MODAL HELPER
// ============================================================================

function createModal(title, bodyHtml, onSave = null, onCancel = null) {
    const overlay = document.createElement('div');
    overlay.className = 'phase4-modal-overlay';

    const modal = document.createElement('div');
    modal.className = 'phase4-modal';
    modal.innerHTML = `
        <div class="phase4-modal-header">
            <h3>${title}</h3>
            <button class="phase4-modal-close" onclick="closePhase4Modal(this)">&times;</button>
        </div>
        <div class="phase4-modal-body">
            ${bodyHtml}
        </div>
        <div class="phase4-modal-footer">
            ${onSave ? `<button class="btn btn-primary" onclick="handleModalSave()">Save</button>` : ''}
            <button class="btn btn-secondary" onclick="closePhase4Modal(this)">Cancel</button>
        </div>
    `;

    overlay.appendChild(modal);
    document.body.appendChild(overlay);

    // Store callbacks
    overlay.onSaveCallback = onSave;
    overlay.onCancelCallback = onCancel;

    // Close on overlay click
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
            closePhase4Modal();
        }
    });

    return overlay;
}

function closePhase4Modal(el) {
    const overlay = el ? el.closest('.phase4-modal-overlay') : document.querySelector('.phase4-modal-overlay');
    if (overlay) {
        const callback = overlay.onCancelCallback;
        overlay.remove();
        if (callback) callback();
    }
}

function handleModalSave() {
    const overlay = document.querySelector('.phase4-modal-overlay');
    if (overlay && overlay.onSaveCallback) {
        overlay.onSaveCallback();
    }
}


// ============================================================================
// PREFERENCES UI
// ============================================================================

function openPreferencesModal() {
    const bodyHtml = `
        <div class="phase4-preferences-form">
            <div class="form-group">
                <label class="form-check">
                    <input type="checkbox" id="darkModeToggle" class="form-check-input">
                    <span>Dark Mode</span>
                </label>
            </div>

            <div class="form-group">
                <label>Notification Email:</label>
                <input type="email" id="notificationEmail" class="form-control"
                       placeholder="your@email.com">
            </div>

            <div class="form-group">
                <label class="form-check">
                    <input type="checkbox" id="notificationsEnabled" class="form-check-input" checked>
                    <span>Enable Notifications</span>
                </label>
            </div>
        </div>
    `;

    const modal = createModal('Dashboard Preferences', bodyHtml, savePreferences);

    // Load current preferences
    userPreferences.loadPreferences().then(() => {
        const prefs = userPreferences.preferences;
        if (prefs.dark_mode) document.getElementById('darkModeToggle').checked = true;
        if (prefs.notification_email) document.getElementById('notificationEmail').value = prefs.notification_email;
        if (prefs.notifications_enabled === 0) document.getElementById('notificationsEnabled').checked = false;
    });
}

async function savePreferences() {
    const darkMode = document.getElementById('darkModeToggle').checked;
    const email = document.getElementById('notificationEmail').value;
    const notificationsEnabled = document.getElementById('notificationsEnabled').checked;

    await userPreferences.setDarkMode(darkMode);
    if (email) await userPreferences.setNotificationEmail(email);

    await fetch('/api/preferences', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            dark_mode: darkMode ? 1 : 0,
            notification_email: email,
            notifications_enabled: notificationsEnabled ? 1 : 0
        })
    });

    closePhase4Modal();
    showToast('Preferences saved!', 'success');
}


// ============================================================================
// EXPORT UI
// ============================================================================

function addExportButtons() {
    const container = document.getElementById('exportContainer');
    if (!container) return;

    const html = `
        <div class="export-button-group">
            <button class="btn btn-sm btn-outline-primary" onclick="handleExportCSV()" title="Export metrics to CSV">
                📥 Export CSV
            </button>
            <button class="btn btn-sm btn-outline-primary" onclick="handleExportExcel()" title="Export to Excel">
                📥 Export Excel
            </button>
            <button class="btn btn-sm btn-outline-primary" onclick="handleExportFindings()" title="Export findings">
                📥 Findings
            </button>
        </div>
    `;

    container.innerHTML = html;
}

async function handleExportCSV() {
    try {
        const metrics = window.currentMetrics || {};
        const filters = window.currentFilters || {};

        const response = await fetch('/api/export/csv', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ metrics, filters })
        });

        if (response.ok) {
            const blob = await response.blob();
            downloadFile(blob, 'tableau-metrics.csv', 'text/csv');
            showToast('CSV exported successfully', 'success');
        }
    } catch (error) {
        console.error('Export error:', error);
        showToast('Failed to export CSV', 'error');
    }
}

async function handleExportExcel() {
    try {
        const metrics = window.currentMetrics || {};
        const findings = window.currentFindings || [];

        const response = await fetch('/api/export/excel', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ metrics, findings })
        });

        if (response.ok) {
            const blob = await response.blob();
            downloadFile(blob, 'tableau-dashboard.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
            showToast('Excel exported successfully', 'success');
        }
    } catch (error) {
        console.error('Export error:', error);
        showToast('Failed to export Excel', 'error');
    }
}

async function handleExportFindings() {
    try {
        const findings = window.currentFindings || [];

        const response = await fetch('/api/export/findings', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ findings })
        });

        if (response.ok) {
            const blob = await response.blob();
            downloadFile(blob, 'findings.csv', 'text/csv');
            showToast('Findings exported successfully', 'success');
        }
    } catch (error) {
        console.error('Export error:', error);
        showToast('Failed to export findings', 'error');
    }
}

function downloadFile(blob, filename, mimeType) {
    const url = window.URL.createObjectURL(new Blob([blob], { type: mimeType }));
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
}


// ============================================================================
// DASHBOARD MANAGEMENT UI
// ============================================================================

function openDashboardSelector() {
    const container = document.getElementById('dashboardSelectorContainer');
    if (!container) return;

    const html = `
        <div class="dashboard-selector">
            <select id="dashboardSelect" onchange="switchDashboard()">
                <option value="">-- Default Dashboard --</option>
                ${dashboardManager.dashboards.map(d =>
                    `<option value="${d.config_id}">${d.name}</option>`
                ).join('')}
            </select>
            <button class="btn btn-sm btn-outline-secondary" onclick="openCreateDashboardModal()">
                ➕ New
            </button>
            <button class="btn btn-sm btn-outline-secondary" onclick="openEditDashboardModal()">
                ✏️ Edit
            </button>
        </div>
    `;

    container.innerHTML = html;
}

function switchDashboard() {
    const select = document.getElementById('dashboardSelect');
    const configId = select.value;
    if (configId) {
        dashboardManager.currentDashboard = configId;
        showToast(`Switched to dashboard`, 'success');
        // Could reload dashboard-specific data here
    }
}

function openCreateDashboardModal() {
    const bodyHtml = `
        <div class="phase4-form">
            <div class="form-group">
                <label>Dashboard Name:</label>
                <input type="text" id="dashboardName" class="form-control"
                       placeholder="e.g., Executive Summary">
            </div>

            <div class="form-group">
                <label>Metrics to Display:</label>
                <div class="metric-checkboxes">
                    <label><input type="checkbox" value="workbook_count" checked> Workbook Count</label>
                    <label><input type="checkbox" value="datasource_count" checked> Data Source Count</label>
                    <label><input type="checkbox" value="stale_count" checked> Stale Items</label>
                    <label><input type="checkbox" value="user_count"> User Count</label>
                    <label><input type="checkbox" value="health_score"> Health Score</label>
                </div>
            </div>

            <div class="form-group">
                <label><input type="checkbox" id="isShared"> Share with Team</label>
            </div>
        </div>
    `;

    createModal('Create Dashboard', bodyHtml, createDashboard);
}

async function createDashboard() {
    const name = document.getElementById('dashboardName').value;
    if (!name) {
        showToast('Please enter a dashboard name', 'error');
        return;
    }

    const metrics = Array.from(document.querySelectorAll('.metric-checkboxes input:checked'))
        .map(cb => cb.value);
    const isShared = document.getElementById('isShared').checked;

    try {
        const configId = await dashboardManager.createDashboard(name, {}, metrics);
        closePhase4Modal();
        openDashboardSelector();
        showToast(`Dashboard "${name}" created!`, 'success');
    } catch (error) {
        showToast('Failed to create dashboard', 'error');
    }
}

function openEditDashboardModal() {
    if (!dashboardManager.currentDashboard) {
        showToast('Please select a dashboard first', 'error');
        return;
    }

    const dashboard = dashboardManager.dashboards.find(d => d.config_id === dashboardManager.currentDashboard);
    if (!dashboard) return;

    const bodyHtml = `
        <div class="phase4-form">
            <div class="form-group">
                <label>Dashboard Name:</label>
                <input type="text" id="dashboardNameEdit" class="form-control"
                       value="${dashboard.name}">
            </div>

            <div class="alert alert-info">
                <small>Update dashboard settings and save changes</small>
            </div>
        </div>
    `;

    createModal('Edit Dashboard', bodyHtml, editDashboard);
}

async function editDashboard() {
    const newName = document.getElementById('dashboardNameEdit').value;

    try {
        await dashboardManager.updateDashboard(dashboardManager.currentDashboard, {
            name: newName
        });
        closePhase4Modal();
        openDashboardSelector();
        showToast('Dashboard updated!', 'success');
    } catch (error) {
        showToast('Failed to update dashboard', 'error');
    }
}


// ============================================================================
// ALERT RULES UI
// ============================================================================

function renderAlertRules() {
    const container = document.getElementById('alertRulesContainer');
    if (!container) return;

    if (alertManager.rules.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <p>No alert rules created yet</p>
                <button class="btn btn-sm btn-primary" onclick="openCreateAlertModal()">
                    Create Alert Rule
                </button>
            </div>
        `;
        return;
    }

    const html = `
        <div class="alert-rules-list">
            ${alertManager.rules.map(rule => `
                <div class="alert-rule ${rule.enabled ? '' : 'disabled'}">
                    <div class="rule-info">
                        <div class="rule-name">${rule.name}</div>
                        <div class="rule-condition">
                            ${rule.metric} ${rule.condition} ${rule.threshold}
                        </div>
                        <div class="rule-action">Action: ${rule.action}</div>
                    </div>
                    <div class="rule-controls">
                        <button class="btn btn-sm btn-outline-secondary"
                                onclick="openEditAlertModal('${rule.rule_id}')">
                            Edit
                        </button>
                        <button class="btn btn-sm ${rule.enabled ? 'btn-warning' : 'btn-success'}"
                                onclick="toggleAlert('${rule.rule_id}', ${!rule.enabled})">
                            ${rule.enabled ? 'Disable' : 'Enable'}
                        </button>
                        <button class="btn btn-sm btn-danger"
                                onclick="deleteAlert('${rule.rule_id}')">
                            Delete
                        </button>
                    </div>
                </div>
            `).join('')}

            <button class="btn btn-sm btn-primary mt-3" onclick="openCreateAlertModal()">
                ➕ New Alert Rule
            </button>
        </div>
    `;

    container.innerHTML = html;
}

function openCreateAlertModal() {
    const bodyHtml = `
        <div class="phase4-form">
            <div class="form-group">
                <label>Alert Name:</label>
                <input type="text" id="alertName" class="form-control"
                       placeholder="e.g., High Stale Count">
            </div>

            <div class="form-group">
                <label>Metric:</label>
                <select id="alertMetric" class="form-control">
                    <option value="workbook_count">Workbook Count</option>
                    <option value="datasource_count">Data Source Count</option>
                    <option value="stale_count">Stale Items</option>
                    <option value="user_count">User Count</option>
                    <option value="health_score">Health Score</option>
                </select>
            </div>

            <div class="form-row">
                <div class="form-group col">
                    <label>Condition:</label>
                    <select id="alertCondition" class="form-control">
                        <option value=">">&gt; (Greater than)</option>
                        <option value="<">&lt; (Less than)</option>
                        <option value="==">==(Equal)</option>
                        <option value="!=">!= (Not equal)</option>
                    </select>
                </div>
                <div class="form-group col">
                    <label>Threshold:</label>
                    <input type="number" id="alertThreshold" class="form-control"
                           placeholder="10" value="10">
                </div>
            </div>

            <div class="form-group">
                <label>Action:</label>
                <select id="alertAction" class="form-control">
                    <option value="email">Email Notification</option>
                    <option value="notification">Browser Notification</option>
                    <option value="badge">Dashboard Badge</option>
                </select>
            </div>
        </div>
    `;

    createModal('Create Alert Rule', bodyHtml, createAlert);
}

async function createAlert() {
    const name = document.getElementById('alertName').value;
    const metric = document.getElementById('alertMetric').value;
    const condition = document.getElementById('alertCondition').value;
    const threshold = parseFloat(document.getElementById('alertThreshold').value);
    const action = document.getElementById('alertAction').value;

    if (!name || !threshold) {
        showToast('Please fill in all required fields', 'error');
        return;
    }

    try {
        await alertManager.createRule(name, metric, condition, threshold, action);
        closePhase4Modal();
        await alertManager.loadRules();
        renderAlertRules();
        showToast(`Alert rule "${name}" created!`, 'success');
    } catch (error) {
        showToast('Failed to create alert rule', 'error');
    }
}

function openEditAlertModal(ruleId) {
    const rule = alertManager.rules.find(r => r.rule_id === ruleId);
    if (!rule) return;

    const bodyHtml = `
        <div class="phase4-form">
            <div class="form-group">
                <label>Alert Name:</label>
                <input type="text" id="alertNameEdit" class="form-control"
                       value="${rule.name}">
            </div>

            <div class="form-group">
                <label>Threshold:</label>
                <input type="number" id="alertThresholdEdit" class="form-control"
                       value="${rule.threshold}">
            </div>

            <div class="form-group">
                <label class="form-check">
                    <input type="checkbox" id="alertEnabledEdit" class="form-check-input"
                           ${rule.enabled ? 'checked' : ''}>
                    <span>Enabled</span>
                </label>
            </div>
        </div>
    `;

    createModal('Edit Alert Rule', bodyHtml, () => editAlert(ruleId));
}

async function editAlert(ruleId) {
    const name = document.getElementById('alertNameEdit').value;
    const threshold = parseFloat(document.getElementById('alertThresholdEdit').value);
    const enabled = document.getElementById('alertEnabledEdit').checked;

    try {
        await alertManager.updateRule(ruleId, { name, threshold, enabled });
        closePhase4Modal();
        await alertManager.loadRules();
        renderAlertRules();
        showToast('Alert rule updated!', 'success');
    } catch (error) {
        showToast('Failed to update alert rule', 'error');
    }
}

async function toggleAlert(ruleId, enable) {
    try {
        if (enable) {
            await alertManager.enableRule(ruleId);
        } else {
            await alertManager.disableRule(ruleId);
        }
        await alertManager.loadRules();
        renderAlertRules();
        showToast(enable ? 'Alert enabled' : 'Alert disabled', 'success');
    } catch (error) {
        showToast('Failed to update alert', 'error');
    }
}

async function deleteAlert(ruleId) {
    if (!confirm('Are you sure you want to delete this alert rule?')) return;

    try {
        await alertManager.deleteRule(ruleId);
        await alertManager.loadRules();
        renderAlertRules();
        showToast('Alert rule deleted', 'success');
    } catch (error) {
        showToast('Failed to delete alert rule', 'error');
    }
}


// ============================================================================
// INITIALIZATION
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    // Initialize all UI components
    addExportButtons();
    openDashboardSelector();
    alertManager.loadRules().then(() => renderAlertRules());

    console.log('Phase 4 UI module loaded');
});
