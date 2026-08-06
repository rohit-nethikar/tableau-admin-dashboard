# Phase 4 Advanced Features - API Documentation

## Overview
Complete REST API for Phase 4 advanced features including user preferences, dashboards, alerts, filtering, and data export.

---

## BASE URL
```
/api
```

All endpoints require authentication (Flask session with 'authed' key).

---

## USER PREFERENCES

### Get Current User's Preferences
```
GET /api/preferences
```
**Response:**
```json
{
  "id": 1,
  "user_id": "user123",
  "dark_mode": 1,
  "default_filters": "{\"date_range\": \"30days\"}",
  "layout_settings": "{\"chart_size\": \"medium\"}",
  "notification_email": "user@example.com",
  "notifications_enabled": 1,
  "created_at": "2026-08-05T10:00:00",
  "updated_at": "2026-08-05T10:00:00"
}
```

### Update User Preferences
```
POST /api/preferences
Content-Type: application/json

{
  "dark_mode": 1,
  "default_filters": {"date_range": "30days"},
  "layout_settings": {"chart_size": "medium"},
  "notification_email": "user@example.com",
  "notifications_enabled": 1
}
```
**Response:** `{ "status": "saved" }`

### Toggle Dark Mode
```
POST /api/preferences/dark-mode
Content-Type: application/json

{
  "enabled": true
}
```
**Response:** `{ "status": "updated" }`

---

## EXPORT FUNCTIONALITY

### Export Metrics to CSV
```
POST /api/export/csv
Content-Type: application/json

{
  "metrics": {
    "workbook_count": 50,
    "stale_count": 5,
    "user_count": 100,
    "avg_score": 75.5
  },
  "filters": {
    "date_range": "30days",
    "severity": "critical"
  }
}
```
**Response:** CSV file download

### Export to Excel
```
POST /api/export/excel
Content-Type: application/json

{
  "metrics": { ... },
  "findings": [
    {"id": "1", "title": "...", "severity": "high", ...}
  ]
}
```
**Response:** Excel file download with multiple sheets

### Export Findings to CSV
```
POST /api/export/findings
Content-Type: application/json

{
  "findings": [
    {
      "id": "1",
      "title": "Stale Workbook",
      "resource_name": "Sales Dashboard",
      "severity": "high",
      "status": "open"
    }
  ]
}
```
**Response:** CSV file download

---

## DASHBOARDS

### List User's Dashboards
```
GET /api/dashboards
```
**Response:**
```json
[
  {
    "id": 1,
    "config_id": "dashboard_user123_abc123",
    "user_id": "user123",
    "name": "Executive Summary",
    "filters": "{}",
    "metric_selection": "[\"workbook_count\", \"stale_count\"]",
    "layout": "{}",
    "is_shared": 0,
    "is_default": 1,
    "created_at": "2026-08-05T10:00:00"
  }
]
```

### Create Dashboard
```
POST /api/dashboards
Content-Type: application/json

{
  "name": "Daily Check",
  "filters": {
    "date_range": "7days",
    "severity": "critical"
  },
  "metric_selection": ["workbook_count", "datasource_count", "stale_count"],
  "is_shared": false
}
```
**Response:**
```json
{
  "config_id": "dashboard_user123_xyz789"
}
```

### Get Specific Dashboard
```
GET /api/dashboards/{config_id}
```

### Update Dashboard
```
PUT /api/dashboards/{config_id}
Content-Type: application/json

{
  "name": "Updated Name",
  "filters": {...},
  "metric_selection": [...],
  "layout": {...},
  "is_shared": true
}
```
**Response:** `{ "status": "updated" }`

### Delete Dashboard
```
DELETE /api/dashboards/{config_id}
```
**Response:** `{ "status": "deleted" }`

### Set as Default Dashboard
```
POST /api/dashboards/{config_id}/set-default
```
**Response:** `{ "status": "default set" }`

---

## ALERT RULES

### List Alert Rules
```
GET /api/alerts/rules
```
**Response:**
```json
[
  {
    "id": 1,
    "rule_id": "rule_user123_abc123",
    "user_id": "user123",
    "name": "Stale Items Alert",
    "metric": "stale_count",
    "condition": ">",
    "threshold": 10,
    "action": "email",
    "action_target": "user@example.com",
    "enabled": 1,
    "last_triggered": "2026-08-05T09:30:00",
    "trigger_count": 5,
    "created_at": "2026-08-05T10:00:00"
  }
]
```

### Create Alert Rule
```
POST /api/alerts/rules
Content-Type: application/json

{
  "name": "Critical Health Drop",
  "metric": "health_score",
  "condition": "<",
  "threshold": 50,
  "action": "email"
}
```
**Response:**
```json
{
  "rule_id": "rule_user123_xyz789"
}
```

### Update Alert Rule
```
PUT /api/alerts/rules/{rule_id}
Content-Type: application/json

{
  "name": "Updated Alert Name",
  "threshold": 20,
  "enabled": 1
}
```

### Delete Alert Rule
```
DELETE /api/alerts/rules/{rule_id}
```

### Enable Alert Rule
```
POST /api/alerts/rules/{rule_id}/enable
```

### Disable Alert Rule
```
POST /api/alerts/rules/{rule_id}/disable
```

### Get Alert History
```
GET /api/alerts/history/{rule_id}?limit=50
```
**Response:**
```json
[
  {
    "id": 1,
    "rule_id": "rule_user123_abc123",
    "metric_value": 15,
    "threshold": 10,
    "triggered_at": "2026-08-05T09:30:00",
    "action_taken": "email_sent"
  }
]
```

### Get Active Alerts
```
GET /api/alerts/active
```
**Response:** Array of recently triggered alerts from last 24 hours

---

## FILTER PRESETS

### List Filter Presets
```
GET /api/filters/presets
```
**Response:**
```json
[
  {
    "id": 1,
    "preset_id": "preset_user123_abc123",
    "user_id": "user123",
    "name": "Critical Issues Only",
    "filters": "{\"severity\": \"critical\"}",
    "created_at": "2026-08-05T10:00:00"
  }
]
```

### Create Filter Preset
```
POST /api/filters/presets
Content-Type: application/json

{
  "name": "Last 7 Days - High Priority",
  "filters": {
    "date_range": "7days",
    "severity": "high",
    "status": "open"
  }
}
```
**Response:**
```json
{
  "preset_id": "preset_user123_xyz789"
}
```

### Get Specific Preset
```
GET /api/filters/presets/{preset_id}
```

### Delete Preset
```
DELETE /api/filters/presets/{preset_id}
```

---

## ERROR RESPONSES

All endpoints return standard error responses:

### Unauthorized (401)
```json
{
  "error": "Unauthorized"
}
```

### Not Found (404)
```json
{
  "error": "Dashboard not found"
}
```

### Server Error (500)
```json
{
  "error": "Internal server error"
}
```

---

## JAVASCRIPT CLIENT LIBRARY

The `phase4.js` file provides convenient wrapper classes:

```javascript
// User Preferences
userPreferences.loadPreferences()
userPreferences.save()
userPreferences.setDarkMode(true)
userPreferences.setNotificationEmail('user@example.com')

// Export
ExportManager.exportToCSV(metrics, filters)
ExportManager.exportToExcel(metrics, findings)
ExportManager.exportFindings(findings)

// Dashboards
dashboardManager.loadDashboards()
dashboardManager.createDashboard(name, filters, metrics)
dashboardManager.updateDashboard(configId, updates)
dashboardManager.deleteDashboard(configId)
dashboardManager.setDefault(configId)

// Alerts
alertManager.loadRules()
alertManager.createRule(name, metric, condition, threshold, action)
alertManager.updateRule(ruleId, updates)
alertManager.deleteRule(ruleId)
alertManager.enableRule(ruleId)
alertManager.disableRule(ruleId)
alertManager.getHistory(ruleId, limit)
alertManager.getActiveAlerts()

// Filter Presets
filterPresetManager.loadPresets()
filterPresetManager.savePreset(name, filters)
filterPresetManager.deletePreset(presetId)
filterPresetManager.applyPreset(presetId)
```

---

## DATABASE SCHEMA

### user_preferences
- `id` INTEGER PRIMARY KEY
- `user_id` TEXT UNIQUE
- `dark_mode` BOOLEAN
- `default_filters` JSON
- `layout_settings` JSON
- `notification_email` TEXT
- `notifications_enabled` BOOLEAN
- `created_at` TIMESTAMP
- `updated_at` TIMESTAMP

### dashboard_configs
- `id` INTEGER PRIMARY KEY
- `config_id` TEXT UNIQUE
- `user_id` TEXT (FK)
- `name` TEXT
- `filters` JSON
- `metric_selection` JSON
- `layout` JSON
- `is_shared` BOOLEAN
- `shared_with` JSON
- `is_default` BOOLEAN
- `created_at` TIMESTAMP
- `updated_at` TIMESTAMP

### alert_rules
- `id` INTEGER PRIMARY KEY
- `rule_id` TEXT UNIQUE
- `user_id` TEXT (FK)
- `name` TEXT
- `metric` TEXT
- `condition` TEXT (>, <, ==, !=)
- `threshold` REAL
- `action` TEXT (email, notification, badge)
- `action_target` TEXT
- `enabled` BOOLEAN
- `last_triggered` TIMESTAMP
- `trigger_count` INTEGER
- `created_at` TIMESTAMP
- `updated_at` TIMESTAMP

### alert_history
- `id` INTEGER PRIMARY KEY
- `rule_id` TEXT (FK)
- `metric_value` REAL
- `threshold` REAL
- `triggered_at` TIMESTAMP
- `action_taken` TEXT

### filter_presets
- `id` INTEGER PRIMARY KEY
- `preset_id` TEXT UNIQUE
- `user_id` TEXT (FK)
- `name` TEXT
- `filters` JSON
- `created_at` TIMESTAMP

---

## TESTING

Example cURL commands:

```bash
# Get preferences
curl -X GET http://localhost:5000/api/preferences

# Create dashboard
curl -X POST http://localhost:5000/api/dashboards \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Dashboard",
    "filters": {},
    "metric_selection": ["workbook_count"]
  }'

# Create alert rule
curl -X POST http://localhost:5000/api/alerts/rules \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Alert",
    "metric": "stale_count",
    "condition": ">",
    "threshold": 5,
    "action": "email"
  }'

# Export to CSV
curl -X POST http://localhost:5000/api/export/csv \
  -H "Content-Type: application/json" \
  -d '{
    "metrics": {"workbook_count": 50, "stale_count": 5}
  }' \
  -o export.csv
```

---

## Implementation Status

**Completed:**
- ✅ Database schema with all 5 tables
- ✅ All CRUD functions in db.py
- ✅ All API endpoints
- ✅ JavaScript client library (phase4.js)
- ✅ CSS styling for components
- ✅ Alert evaluation engine

**In Progress:**
- UI components for preferences, dashboards, alerts
- Export button integration
- Filter presets UI

**TODO:**
- Email notification service
- Dashboard sharing & permissions
- Advanced filtering UI with date pickers
- Dashboard editor with drag-and-drop

---

*Last Updated: 2026-08-05*
