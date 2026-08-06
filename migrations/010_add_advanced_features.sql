-- Migration: Add tables for Phase 4 Advanced Features
-- Date: 2026-08-05
-- Purpose: Create schema for preferences, dashboards, and alerts

-- User Preferences Table
CREATE TABLE IF NOT EXISTS user_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT UNIQUE NOT NULL,
    dark_mode BOOLEAN DEFAULT 0,
    default_filters TEXT,  -- JSON: {"date_range": "30days", "severity": "all"}
    layout_settings TEXT,  -- JSON: {"chart_size": "medium", "card_layout": "grid"}
    notification_email TEXT,
    notifications_enabled BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Dashboard Configurations Table
CREATE TABLE IF NOT EXISTS dashboard_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    config_id TEXT UNIQUE NOT NULL,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,  -- e.g., "Executive Summary", "Daily Check"
    filters TEXT,  -- JSON: filters applied to this dashboard
    metric_selection TEXT,  -- JSON: which metrics to show
    layout TEXT,  -- JSON: layout preferences
    is_shared BOOLEAN DEFAULT 0,
    shared_with TEXT,  -- JSON: list of user emails
    is_default BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user_preferences(user_id)
);

-- Alert Rules Table
CREATE TABLE IF NOT EXISTS alert_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_id TEXT UNIQUE NOT NULL,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    metric TEXT NOT NULL,  -- workbook_count, stale_count, critical_issues, health_score
    condition TEXT NOT NULL,  -- '>', '<', '==', '!='
    threshold REAL NOT NULL,
    action TEXT NOT NULL,  -- 'email', 'notification', 'badge'
    action_target TEXT,  -- email address or notification type
    enabled BOOLEAN DEFAULT 1,
    last_triggered TIMESTAMP,
    trigger_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user_preferences(user_id)
);

-- Alert History Table (for logging triggered alerts)
CREATE TABLE IF NOT EXISTS alert_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_id TEXT NOT NULL,
    metric_value REAL NOT NULL,
    threshold REAL NOT NULL,
    triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    action_taken TEXT,  -- 'email_sent', 'notification_shown', etc.
    FOREIGN KEY (rule_id) REFERENCES alert_rules(rule_id)
);

-- Filter Presets Table
CREATE TABLE IF NOT EXISTS filter_presets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    preset_id TEXT UNIQUE NOT NULL,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,  -- e.g., "Critical Only", "Last 7 Days"
    filters TEXT NOT NULL,  -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user_preferences(user_id)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_user_preferences_user_id ON user_preferences(user_id);
CREATE INDEX IF NOT EXISTS idx_dashboard_configs_user_id ON dashboard_configs(user_id);
CREATE INDEX IF NOT EXISTS idx_alert_rules_user_id ON alert_rules(user_id);
CREATE INDEX IF NOT EXISTS idx_alert_rules_enabled ON alert_rules(enabled);
CREATE INDEX IF NOT EXISTS idx_filter_presets_user_id ON filter_presets(user_id);

-- Insert default preferences for existing users (if any)
INSERT OR IGNORE INTO user_preferences (user_id, dark_mode, notifications_enabled)
VALUES ('default_user', 0, 1);
