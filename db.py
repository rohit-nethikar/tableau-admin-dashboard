"""SQLite cache. Plain stdlib sqlite3 - the schema is small and this keeps the whole
data flow (what gets pulled from Tableau -> what gets shown) easy to read in one place.

Governance tables (users, health_scores, findings, audit_log, asset_owner_overrides)
were added on top of the original workbooks/permissions/lineage cache. Column
additions to pre-existing tables (workbooks, datasources, permission_grants) are
applied via ALTER TABLE in _run_migrations() so an existing cache.db from before this
change upgrades in place without deleting cached data.

Multi-site support: content tables carry a `site` column so one cache DB can hold
data for several Tableau sites at once. Tableau's resource IDs (workbook/datasource/
user LUIDs) are unique server-wide, not just per-site, so primary keys built on those
IDs don't need to change - only DELETE/SELECT statements need a `site` filter so a
refresh of one site can never touch another site's cached rows. Callers (sync_service,
routes) always pass `site` explicitly; nothing in this module reads Flask session
state, so it stays safe to call from the background scheduler thread.
"""
import sqlite3
from contextlib import contextmanager

from config import DB_PATH, settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS app_config (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    parent_id TEXT
);

CREATE TABLE IF NOT EXISTS workbooks (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    project_name TEXT,
    owner_name TEXT,
    updated_at TEXT,
    extract_status TEXT,
    extract_last_run_at TEXT,
    is_stale INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS datasources (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    project_name TEXT,
    owner_name TEXT
);

CREATE TABLE IF NOT EXISTS workbook_datasource_links (
    workbook_name TEXT NOT NULL,
    datasource_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS permission_grants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    resource_type TEXT NOT NULL,   -- 'project' or 'workbook'
    resource_name TEXT NOT NULL,
    project_name TEXT,
    grantee_type TEXT NOT NULL,    -- 'user' or 'group'
    grantee_name TEXT NOT NULL,
    capabilities TEXT NOT NULL,    -- comma-joined list of allowed capabilities
    source TEXT NOT NULL           -- 'explicit' or 'project_default'
);

CREATE TABLE IF NOT EXISTS group_members (
    group_name TEXT NOT NULL,
    user_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS refresh_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL,          -- 'running', 'success', 'partial', 'failed'
    detail TEXT
);

CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT,
    site_role TEXT,
    last_login_at TEXT,
    fetched_at TEXT
);

CREATE TABLE IF NOT EXISTS health_scores (
    resource_type TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    resource_name TEXT,
    project_name TEXT,
    owner_name TEXT,
    score REAL,
    computed_at TEXT,
    factors_json TEXT,
    PRIMARY KEY (resource_type, resource_id)
);

CREATE TABLE IF NOT EXISTS findings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    resource_type TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    resource_name TEXT,
    project_name TEXT,
    owner_name TEXT,
    category TEXT NOT NULL,
    severity TEXT NOT NULL,        -- 'critical', 'high', 'medium', 'low'
    title TEXT NOT NULL,
    description TEXT,
    evidence_json TEXT,
    recommended_action TEXT,
    first_detected_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',   -- 'open', 'acknowledged', 'resolved', 'dismissed'
    status_note TEXT,
    status_changed_by TEXT,
    status_changed_at TEXT,
    UNIQUE (resource_type, resource_id, category)
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    resource_type TEXT,
    resource_id TEXT,
    details TEXT
);

CREATE TABLE IF NOT EXISTS asset_owner_overrides (
    resource_type TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    business_owner TEXT,
    technical_owner TEXT,
    notes TEXT,
    updated_at TEXT,
    PRIMARY KEY (resource_type, resource_id)
);

CREATE TABLE IF NOT EXISTS custom_views (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    workbook_name TEXT,
    view_name TEXT,
    owner_name TEXT,
    shared INTEGER NOT NULL DEFAULT 0,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS workbook_views (
    workbook_id TEXT NOT NULL,
    workbook_name TEXT,
    view_name TEXT NOT NULL,
    total_views INTEGER,
    PRIMARY KEY (workbook_id, view_name)
);

CREATE TABLE IF NOT EXISTS subscriptions (
    id TEXT PRIMARY KEY,
    subscriber_name TEXT,
    subject TEXT,
    target_type TEXT,
    target_name TEXT,
    suspended INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS connected_apps (
    client_id TEXT PRIMARY KEY,
    name TEXT,
    enabled INTEGER NOT NULL DEFAULT 0,
    project_scope TEXT,
    domain_safelist TEXT,
    unrestricted_embedding INTEGER NOT NULL DEFAULT 0,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS data_alerts (
    id TEXT PRIMARY KEY,
    subject TEXT,
    creator_id TEXT,
    creator_name TEXT,
    owner_id TEXT,
    owner_name TEXT,
    created_at TEXT,
    updated_at TEXT,
    frequency TEXT,
    public INTEGER NOT NULL DEFAULT 0,
    view_id TEXT,
    view_name TEXT,
    workbook_id TEXT,
    workbook_name TEXT,
    project_id TEXT,
    project_name TEXT,
    recipients TEXT
);

CREATE TABLE IF NOT EXISTS webhooks (
    id TEXT PRIMARY KEY,
    name TEXT,
    url TEXT,
    event TEXT,
    owner_id TEXT,
    owner_name TEXT
);

CREATE TABLE IF NOT EXISTS site_settings (
    site TEXT PRIMARY KEY,
    extract_encryption_mode TEXT,
    storage_quota INTEGER,
    storage_used TEXT,
    tier_creator_capacity INTEGER,
    tier_explorer_capacity INTEGER,
    tier_viewer_capacity INTEGER,
    ask_data_mode TEXT,
    guest_access_enabled INTEGER NOT NULL DEFAULT 0,
    disable_subscriptions INTEGER NOT NULL DEFAULT 0,
    revision_history_enabled INTEGER NOT NULL DEFAULT 0,
    revision_limit INTEGER
);

CREATE TABLE IF NOT EXISTS server_info (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    product_version TEXT,
    build_number TEXT,
    rest_api_version TEXT,
    fetched_at TEXT
);

CREATE TABLE IF NOT EXISTS dqw_warnings (
    resource_type TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    resource_name TEXT,
    warning_type TEXT,
    severe INTEGER NOT NULL DEFAULT 0,
    message TEXT,
    created_at TEXT
);
"""

# Tables that hold per-site content. Each gets a `site` column (see
# _COLUMN_MIGRATIONS below) and every DELETE/SELECT against it is scoped by site.
_SITE_SCOPED_TABLES = [
    "projects", "workbooks", "datasources", "workbook_datasource_links",
    "permission_grants", "group_members", "refresh_log", "users",
    "health_scores", "findings", "asset_owner_overrides", "custom_views",
    "subscriptions", "connected_apps", "data_alerts",
    "webhooks", "dqw_warnings", "workbook_views",
]

# (table, column, type declaration) - applied via ALTER TABLE if the column is missing,
# so an existing cache.db from before Phase 1 upgrades in place.
_COLUMN_MIGRATIONS = [
    ("workbooks", "owner_id", "TEXT"),
    ("workbooks", "description", "TEXT"),
    ("workbooks", "lifetime_view_count", "INTEGER"),
    ("workbooks", "webpage_url", "TEXT"),
    ("workbooks", "created_at", "TEXT"),
    ("workbooks", "size_mb", "INTEGER"),
    ("workbooks", "sheet_count", "INTEGER"),
    ("workbooks", "connection_count", "INTEGER"),
    ("workbooks", "revision_count", "INTEGER"),
    ("workbooks", "consecutive_extract_failures", "INTEGER"),
    ("workbooks", "connection_type", "TEXT"),
    ("workbooks", "refresh_schedule_name", "TEXT"),
    ("workbooks", "refresh_frequency", "TEXT"),
    ("workbooks", "refresh_next_run_at", "TEXT"),
    ("workbooks", "extract_last_run_duration_seconds", "INTEGER"),
    ("datasources", "owner_id", "TEXT"),
    ("datasources", "description", "TEXT"),
    ("datasources", "is_certified", "INTEGER NOT NULL DEFAULT 0"),
    ("datasources", "certification_note", "TEXT"),
    ("datasources", "lifetime_view_count", "INTEGER"),
    ("datasources", "extract_status", "TEXT"),
    ("datasources", "extract_last_run_at", "TEXT"),
    ("datasources", "updated_at", "TEXT"),
    ("datasources", "is_stale", "INTEGER NOT NULL DEFAULT 0"),
    ("datasources", "webpage_url", "TEXT"),
    ("datasources", "has_extracts", "INTEGER"),
    ("datasources", "created_at", "TEXT"),
    ("datasources", "size_mb", "INTEGER"),
    ("datasources", "connection_count", "INTEGER"),
    ("datasources", "revision_count", "INTEGER"),
    ("datasources", "consecutive_extract_failures", "INTEGER"),
    ("datasources", "connection_type", "TEXT"),
    ("datasources", "datasource_type", "TEXT"),
    ("datasources", "encrypt_extracts", "INTEGER"),
    ("datasources", "refresh_schedule_name", "TEXT"),
    ("datasources", "refresh_frequency", "TEXT"),
    ("datasources", "refresh_next_run_at", "TEXT"),
    ("datasources", "extract_last_run_duration_seconds", "INTEGER"),
    ("permission_grants", "capabilities_json", "TEXT"),
    ("custom_views", "last_accessed_at", "TEXT"),
    ("workbooks", "tags", "TEXT"),
    ("workbooks", "favorites_count", "INTEGER"),
    ("datasources", "tags", "TEXT"),
    ("datasources", "favorites_count", "INTEGER"),
    ("datasources", "underlying_sources", "TEXT"),
    ("users", "account_number", "TEXT"),
] + [(table, "site", "TEXT NOT NULL DEFAULT ''") for table in _SITE_SCOPED_TABLES]


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _run_migrations(conn):
    for table, column, decl in _COLUMN_MIGRATIONS:
        existing_cols = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
        if column not in existing_cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")
    # Backfill: rows cached before the `site` column existed carry '' - stamp them
    # with the configured default site so they stay visible instead of becoming
    # orphaned. No-op on every run after the first (WHERE site = '' matches nothing).
    for table in _SITE_SCOPED_TABLES:
        conn.execute(f"UPDATE {table} SET site = ? WHERE site = ''", (settings.default_site,))


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        _run_migrations(conn)


# --- app_config -------------------------------------------------------------

def set_config(key: str, value: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO app_config(key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )


def get_config(key: str, default=None):
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM app_config WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default


def is_setup_complete() -> bool:
    return get_config("pat_encrypted") is not None and get_config("passcode_hash") is not None


# --- bulk replace helpers (a site's cache is fully rebuilt each sync) --------

def replace_projects(site, rows):
    with get_conn() as conn:
        conn.execute("DELETE FROM projects WHERE site = ?", (site,))
        conn.executemany(
            "INSERT INTO projects(site, id, name, parent_id) VALUES (?, ?, ?, ?)",
            [(site,) + tuple(r) for r in rows],
        )


def replace_workbooks(site, rows):
    """rows: (id, name, project_name, owner_name, owner_id, description, updated_at,
    extract_status, extract_last_run_at, is_stale, lifetime_view_count, webpage_url,
    created_at, size_mb, sheet_count, connection_count, revision_count,
    consecutive_extract_failures, connection_type, refresh_schedule_name,
    refresh_frequency, refresh_next_run_at, extract_last_run_duration_seconds, tags,
    favorites_count) tuples."""
    with get_conn() as conn:
        conn.execute("DELETE FROM workbooks WHERE site = ?", (site,))
        conn.executemany(
            """INSERT INTO workbooks
               (site, id, name, project_name, owner_name, owner_id, description, updated_at,
                extract_status, extract_last_run_at, is_stale, lifetime_view_count, webpage_url,
                created_at, size_mb, sheet_count, connection_count, revision_count,
                consecutive_extract_failures, connection_type, refresh_schedule_name,
                refresh_frequency, refresh_next_run_at, extract_last_run_duration_seconds,
                tags, favorites_count)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [(site,) + tuple(r) for r in rows],
        )


def replace_datasources(site, rows):
    """rows: (id, name, project_name, owner_name, owner_id, description, is_certified,
    certification_note, lifetime_view_count, extract_status, extract_last_run_at,
    updated_at, is_stale, webpage_url, has_extracts, created_at, size_mb,
    connection_count, revision_count, consecutive_extract_failures, connection_type,
    datasource_type, encrypt_extracts, refresh_schedule_name, refresh_frequency,
    refresh_next_run_at, extract_last_run_duration_seconds, tags, favorites_count,
    underlying_sources) tuples."""
    with get_conn() as conn:
        conn.execute("DELETE FROM datasources WHERE site = ?", (site,))
        conn.executemany(
            """INSERT INTO datasources
               (site, id, name, project_name, owner_name, owner_id, description, is_certified,
                certification_note, lifetime_view_count, extract_status, extract_last_run_at,
                updated_at, is_stale, webpage_url, has_extracts, created_at, size_mb,
                connection_count, revision_count, consecutive_extract_failures, connection_type,
                datasource_type, encrypt_extracts, refresh_schedule_name, refresh_frequency,
                refresh_next_run_at, extract_last_run_duration_seconds, tags, favorites_count,
                underlying_sources)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [(site,) + tuple(r) for r in rows],
        )


def replace_custom_views(site, rows):
    """rows: (id, name, workbook_name, view_name, owner_name, shared, created_at,
    updated_at, last_accessed_at) tuples."""
    with get_conn() as conn:
        conn.execute("DELETE FROM custom_views WHERE site = ?", (site,))
        conn.executemany(
            """INSERT INTO custom_views
               (site, id, name, workbook_name, view_name, owner_name, shared, created_at, updated_at, last_accessed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [(site,) + tuple(r) for r in rows],
        )


def replace_subscriptions(site, rows):
    """rows: (id, subscriber_name, subject, target_type, target_name, suspended) tuples."""
    with get_conn() as conn:
        conn.execute("DELETE FROM subscriptions WHERE site = ?", (site,))
        conn.executemany(
            """INSERT INTO subscriptions
               (site, id, subscriber_name, subject, target_type, target_name, suspended)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            [(site,) + tuple(r) for r in rows],
        )


def replace_connected_apps(site, rows):
    """rows: (client_id, name, enabled, project_scope, domain_safelist,
    unrestricted_embedding, created_at) tuples."""
    with get_conn() as conn:
        conn.execute("DELETE FROM connected_apps WHERE site = ?", (site,))
        conn.executemany(
            """INSERT INTO connected_apps
               (site, client_id, name, enabled, project_scope, domain_safelist,
                unrestricted_embedding, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            [(site,) + tuple(r) for r in rows],
        )


def replace_data_alerts(site, rows):
    """rows: (id, subject, creator_id, creator_name, owner_id, owner_name, created_at,
    updated_at, frequency, public, view_id, view_name, workbook_id, workbook_name,
    project_id, project_name, recipients) tuples."""
    with get_conn() as conn:
        conn.execute("DELETE FROM data_alerts WHERE site = ?", (site,))
        conn.executemany(
            """INSERT INTO data_alerts
               (site, id, subject, creator_id, creator_name, owner_id, owner_name, created_at,
                updated_at, frequency, public, view_id, view_name, workbook_id, workbook_name,
                project_id, project_name, recipients)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [(site,) + tuple(r) for r in rows],
        )


def replace_webhooks(site, rows):
    """rows: (id, name, url, event, owner_id, owner_name) tuples."""
    with get_conn() as conn:
        conn.execute("DELETE FROM webhooks WHERE site = ?", (site,))
        conn.executemany(
            """INSERT INTO webhooks (site, id, name, url, event, owner_id, owner_name)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            [(site,) + tuple(r) for r in rows],
        )


def replace_dqw_warnings(site, rows):
    """rows: (resource_type, resource_id, resource_name, warning_type, severe, message,
    created_at) tuples."""
    with get_conn() as conn:
        conn.execute("DELETE FROM dqw_warnings WHERE site = ?", (site,))
        conn.executemany(
            """INSERT INTO dqw_warnings
               (site, resource_type, resource_id, resource_name, warning_type, severe,
                message, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            [(site,) + tuple(r) for r in rows],
        )


def replace_site_settings(site, settings_dict: dict):
    """settings_dict keys match the site_settings table columns exactly (see
    tableau_client.list_site_settings). One row per site, replaced whole each sync."""
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO site_settings
               (site, extract_encryption_mode, storage_quota, storage_used,
                tier_creator_capacity, tier_explorer_capacity, tier_viewer_capacity,
                ask_data_mode, guest_access_enabled, disable_subscriptions,
                revision_history_enabled, revision_limit)
               VALUES (:site, :extract_encryption_mode, :storage_quota, :storage_used,
                :tier_creator_capacity, :tier_explorer_capacity, :tier_viewer_capacity,
                :ask_data_mode, :guest_access_enabled, :disable_subscriptions,
                :revision_history_enabled, :revision_limit)
               ON CONFLICT(site) DO UPDATE SET
                   extract_encryption_mode = excluded.extract_encryption_mode,
                   storage_quota = excluded.storage_quota,
                   storage_used = excluded.storage_used,
                   tier_creator_capacity = excluded.tier_creator_capacity,
                   tier_explorer_capacity = excluded.tier_explorer_capacity,
                   tier_viewer_capacity = excluded.tier_viewer_capacity,
                   ask_data_mode = excluded.ask_data_mode,
                   guest_access_enabled = excluded.guest_access_enabled,
                   disable_subscriptions = excluded.disable_subscriptions,
                   revision_history_enabled = excluded.revision_history_enabled,
                   revision_limit = excluded.revision_limit""",
            {"site": site, **settings_dict},
        )


def fetch_site_settings(site: str):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM site_settings WHERE site = ?", (site,)).fetchone()
        return dict(row) if row else None


def replace_server_info(info: dict):
    """info keys match the server_info table columns exactly (see
    tableau_client.get_server_info). Single row, server-wide (not site-scoped) -
    every configured site lives on the same physical Tableau Server, so this is
    replaced whole on every sync regardless of which site triggered it."""
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO server_info (id, product_version, build_number, rest_api_version, fetched_at)
               VALUES (1, :product_version, :build_number, :rest_api_version, :fetched_at)
               ON CONFLICT(id) DO UPDATE SET
                   product_version = excluded.product_version,
                   build_number = excluded.build_number,
                   rest_api_version = excluded.rest_api_version,
                   fetched_at = excluded.fetched_at""",
            info,
        )


def fetch_server_info():
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM server_info WHERE id = 1").fetchone()
        return dict(row) if row else None


def replace_links(site, rows):
    with get_conn() as conn:
        conn.execute("DELETE FROM workbook_datasource_links WHERE site = ?", (site,))
        conn.executemany(
            "INSERT INTO workbook_datasource_links(site, workbook_name, datasource_name) VALUES (?, ?, ?)",
            [(site,) + tuple(r) for r in rows],
        )


def replace_group_members(site, rows):
    with get_conn() as conn:
        conn.execute("DELETE FROM group_members WHERE site = ?", (site,))
        conn.executemany(
            "INSERT INTO group_members(site, group_name, user_name) VALUES (?, ?, ?)",
            [(site,) + tuple(r) for r in rows],
        )


def replace_permissions(site, rows):
    """rows: (resource_type, resource_name, project_name, grantee_type, grantee_name,
    capabilities, capabilities_json, source) tuples."""
    with get_conn() as conn:
        conn.execute("DELETE FROM permission_grants WHERE site = ?", (site,))
        conn.executemany(
            """INSERT INTO permission_grants
               (site, resource_type, resource_name, project_name, grantee_type, grantee_name,
                capabilities, capabilities_json, source)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [(site,) + tuple(r) for r in rows],
        )


def replace_users(site, rows):
    """rows: (id, name, email, site_role, last_login_at, fetched_at) tuples.

    Uses UPSERT to preserve existing account_number values during refresh.
    IMPORTANT: Preserves users with account_number set (BigQuery-synced custom view owners)
    even if they're no longer in Tableau's user list.
    """
    with get_conn() as conn:
        # Use UPSERT pattern: UPDATE if exists, INSERT if new
        # Preserves account_number column during refresh
        conn.executemany(
            """INSERT INTO users(site, id, name, email, site_role, last_login_at, fetched_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                   name = excluded.name,
                   email = excluded.email,
                   site_role = excluded.site_role,
                   last_login_at = excluded.last_login_at,
                   fetched_at = excluded.fetched_at
               -- Note: account_number is NOT updated, preserving BigQuery-synced data
            """,
            [(site,) + tuple(r) for r in rows],
        )
        # Clean up: delete users for this site that are no longer in rows
        # BUT: PRESERVE users with account_number (BigQuery-synced custom view owners)
        row_ids = {r[0] for r in rows}
        existing = conn.execute(
            "SELECT id, account_number FROM users WHERE site = ?", (site,)
        ).fetchall()
        # Only delete users that:
        # 1. Are not in the latest Tableau sync, AND
        # 2. Don't have an account_number (i.e., not BigQuery-synced)
        to_delete = [row[0] for row in existing if row[0] not in row_ids and not row[1]]
        if to_delete:
            placeholders = ",".join("?" * len(to_delete))
            conn.execute(
                f"DELETE FROM users WHERE site = ? AND id IN ({placeholders})",
                [site] + to_delete,
            )


def update_datasource_view_counts(site, counts_by_name: dict):
    with get_conn() as conn:
        conn.executemany(
            "UPDATE datasources SET lifetime_view_count = ? WHERE name = ? AND site = ?",
            [(count, name, site) for name, count in counts_by_name.items()],
        )


def replace_health_scores(site, rows):
    """rows: (resource_type, resource_id, resource_name, project_name, owner_name,
    score, computed_at, factors_json) tuples."""
    with get_conn() as conn:
        conn.execute("DELETE FROM health_scores WHERE site = ?", (site,))
        conn.executemany(
            """INSERT INTO health_scores
               (site, resource_type, resource_id, resource_name, project_name, owner_name,
                score, computed_at, factors_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [(site,) + tuple(r) for r in rows],
        )


# --- refresh_log --------------------------------------------------------------

def start_refresh(site: str, started_at: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO refresh_log(site, started_at, status) VALUES (?, ?, 'running')",
            (site, started_at),
        )
        return cur.lastrowid


def finish_refresh(run_id: int, finished_at: str, status: str, detail: str):
    with get_conn() as conn:
        conn.execute(
            "UPDATE refresh_log SET finished_at = ?, status = ?, detail = ? WHERE id = ?",
            (finished_at, status, detail, run_id),
        )


def latest_refresh(site: str):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM refresh_log WHERE site = ? ORDER BY id DESC LIMIT 1", (site,)
        ).fetchone()
        return dict(row) if row else None


def fetch_refresh_log(site: str, limit: int = 30):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM refresh_log WHERE site = ? ORDER BY id DESC LIMIT ?", (site, limit)
        ).fetchall()
        return [dict(r) for r in rows]


# --- read helpers for the UI ---------------------------------------------------

def fetch_projects(site: str):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM projects WHERE site = ? ORDER BY name", (site,)
        ).fetchall()
        return [dict(r) for r in rows]


def fetch_workbooks(site: str):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM workbooks WHERE site = ? ORDER BY project_name, name", (site,)
        ).fetchall()
        return [dict(r) for r in rows]


def fetch_datasources(site: str):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM datasources WHERE site = ? ORDER BY project_name, name", (site,)
        ).fetchall()
        return [dict(r) for r in rows]


def fetch_permissions(site: str):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM permission_grants WHERE site = ? "
            "ORDER BY project_name, resource_type, resource_name",
            (site,),
        ).fetchall()
        return [dict(r) for r in rows]


def fetch_group_members(site: str):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT group_name, user_name FROM group_members WHERE site = ? "
            "ORDER BY group_name, user_name",
            (site,),
        ).fetchall()
        return [dict(r) for r in rows]


_CUSTOM_VIEW_FILTER_COLUMNS = {"workbook_name", "owner_name", "view_name", "shared"}


def fetch_custom_views(site: str, filters: dict = None):
    filters = filters or {}
    clauses = ["cv.site = ?"]
    params = [site]
    for key, value in filters.items():
        if key in _CUSTOM_VIEW_FILTER_COLUMNS and value not in (None, ""):
            clauses.append(f"cv.{key} = ?")
            params.append(value)
    where = f"WHERE {' AND '.join(clauses)}"
    with get_conn() as conn:
        rows = conn.execute(
            f"""SELECT cv.*,
                      COALESCE(u.email, '') as owner_email,
                      COALESCE(u.account_number, '') as owner_account_number
               FROM custom_views cv
               LEFT JOIN users u ON LOWER(cv.owner_name) = LOWER(u.email) AND u.site = cv.site
               {where}
               ORDER BY cv.workbook_name, cv.name""",
            params,
        ).fetchall()
        return [dict(r) for r in rows]


def replace_workbook_views(site: str, rows):
    """rows: (workbook_id, workbook_name, view_name, total_views) tuples."""
    with get_conn() as conn:
        conn.execute("DELETE FROM workbook_views WHERE site = ?", (site,))
        conn.executemany(
            """INSERT INTO workbook_views (site, workbook_id, workbook_name, view_name, total_views)
               VALUES (?, ?, ?, ?, ?)""",
            [(site,) + tuple(r) for r in rows],
        )


def fetch_workbook_views(site: str):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM workbook_views WHERE site = ? ORDER BY total_views DESC", (site,)
        ).fetchall()
        return [dict(r) for r in rows]


def fetch_subscriptions(site: str):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM subscriptions WHERE site = ? ORDER BY target_name, subscriber_name",
            (site,),
        ).fetchall()
        return [dict(r) for r in rows]


def fetch_connected_apps(site: str):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM connected_apps WHERE site = ? ORDER BY name", (site,)
        ).fetchall()
        return [dict(r) for r in rows]


def fetch_data_alerts(site: str):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM data_alerts WHERE site = ? ORDER BY subject", (site,)
        ).fetchall()
        return [dict(r) for r in rows]


def fetch_webhooks(site: str):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM webhooks WHERE site = ? ORDER BY name", (site,)
        ).fetchall()
        return [dict(r) for r in rows]


def fetch_dqw_warnings(site: str):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM dqw_warnings WHERE site = ? ORDER BY resource_name", (site,)
        ).fetchall()
        return [dict(r) for r in rows]


def fetch_lineage(site: str):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT datasource_name, workbook_name FROM workbook_datasource_links "
            "WHERE site = ? ORDER BY datasource_name, workbook_name",
            (site,),
        ).fetchall()
        return [dict(r) for r in rows]


def fetch_users(site: str):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM users WHERE site = ? ORDER BY name", (site,)
        ).fetchall()
        return [dict(r) for r in rows]


def fetch_users_by_id(site: str) -> dict:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM users WHERE site = ?", (site,)).fetchall()
        return {r["id"]: dict(r) for r in rows}


def fetch_health_scores(site: str):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM health_scores WHERE site = ? ORDER BY score ASC", (site,)
        ).fetchall()
        return [dict(r) for r in rows]


# --- asset owner overrides (admin-assignable, since Tableau has no native concept
# of a "business owner" separate from the content's technical/platform owner) ------

def upsert_owner_override(site, resource_type, resource_id, business_owner, technical_owner, notes, updated_at):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO asset_owner_overrides
               (site, resource_type, resource_id, business_owner, technical_owner, notes, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(resource_type, resource_id) DO UPDATE SET
                   site = excluded.site,
                   business_owner = excluded.business_owner,
                   technical_owner = excluded.technical_owner,
                   notes = excluded.notes,
                   updated_at = excluded.updated_at""",
            (site, resource_type, resource_id, business_owner, technical_owner, notes, updated_at),
        )


def fetch_owner_overrides(site: str) -> dict:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM asset_owner_overrides WHERE site = ?", (site,)
        ).fetchall()
        return {(r["resource_type"], r["resource_id"]): dict(r) for r in rows}


# --- findings -------------------------------------------------------------------

def reconcile_findings(site: str, rows, now_iso: str):
    """Upserts freshly computed findings against the natural key
    (resource_type, resource_id, category), preserving any existing status /
    status_note / status_changed_by / status_changed_at / first_detected_at.
    Any previously open/acknowledged finding for this site NOT present in `rows`
    this run is auto-resolved (status='resolved', actor 'system') since the
    underlying condition cleared. Dismissed findings are left alone either way.
    Scoped to `site` throughout so refreshing one site can never resolve another
    site's still-valid findings that simply weren't recomputed this run.

    `rows`: iterable of dicts with keys resource_type, resource_id, resource_name,
    project_name, owner_name, category, severity, title, description,
    evidence_json (already-serialized JSON string), recommended_action.
    """
    with get_conn() as conn:
        computed_keys = set()
        for r in rows:
            key = (r["resource_type"], r["resource_id"], r["category"])
            computed_keys.add(key)
            conn.execute(
                """INSERT INTO findings
                   (site, resource_type, resource_id, resource_name, project_name, owner_name,
                    category, severity, title, description, evidence_json,
                    recommended_action, first_detected_at, last_seen_at, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open')
                   ON CONFLICT(resource_type, resource_id, category) DO UPDATE SET
                       site = excluded.site,
                       resource_name = excluded.resource_name,
                       project_name = excluded.project_name,
                       owner_name = excluded.owner_name,
                       severity = excluded.severity,
                       title = excluded.title,
                       description = excluded.description,
                       evidence_json = excluded.evidence_json,
                       recommended_action = excluded.recommended_action,
                       last_seen_at = excluded.last_seen_at""",
                (
                    site, r["resource_type"], r["resource_id"], r["resource_name"],
                    r["project_name"], r["owner_name"], r["category"], r["severity"],
                    r["title"], r["description"], r["evidence_json"],
                    r["recommended_action"], now_iso, now_iso,
                ),
            )

        stale_rows = conn.execute(
            "SELECT id, resource_type, resource_id, category FROM findings "
            "WHERE status IN ('open', 'acknowledged') AND site = ?",
            (site,),
        ).fetchall()
        for row in stale_rows:
            key = (row["resource_type"], row["resource_id"], row["category"])
            if key not in computed_keys:
                conn.execute(
                    """UPDATE findings SET status = 'resolved',
                       status_note = 'Condition no longer detected on automated scan',
                       status_changed_by = 'system', status_changed_at = ?
                       WHERE id = ?""",
                    (now_iso, row["id"]),
                )


_FINDING_FILTER_COLUMNS = {"severity", "category", "project_name", "owner_name", "status"}


def fetch_findings(site: str, filters: dict = None):
    filters = filters or {}
    clauses = ["site = ?"]
    params = [site]
    for key, value in filters.items():
        if key in _FINDING_FILTER_COLUMNS and value:
            clauses.append(f"{key} = ?")
            params.append(value)
    where = f"WHERE {' AND '.join(clauses)}"
    with get_conn() as conn:
        rows = conn.execute(
            f"""SELECT * FROM findings {where}
                ORDER BY CASE severity
                    WHEN 'critical' THEN 0 WHEN 'high' THEN 1
                    WHEN 'medium' THEN 2 WHEN 'low' THEN 3 ELSE 4 END,
                    last_seen_at DESC""",
            params,
        ).fetchall()
        return [dict(r) for r in rows]


def get_finding(finding_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM findings WHERE id = ?", (finding_id,)).fetchone()
        return dict(row) if row else None


def set_finding_status(finding_id: int, status: str, note: str, actor: str, now_iso: str):
    with get_conn() as conn:
        conn.execute(
            """UPDATE findings SET status = ?, status_note = ?, status_changed_by = ?,
               status_changed_at = ? WHERE id = ?""",
            (status, note, actor, now_iso, finding_id),
        )


# --- audit log --------------------------------------------------------------

def add_audit_log(timestamp: str, actor: str, action: str, resource_type: str, resource_id: str, details: str):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO audit_log(timestamp, actor, action, resource_type, resource_id, details)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (timestamp, actor, action, resource_type, resource_id, details),
        )


def fetch_audit_log(limit: int = 200):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


def update_user_account_number(site: str, user_id: str, account_number: str):
    """Update the account_number for a user."""
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET account_number = ? WHERE site = ? AND id = ?",
            (account_number, site, user_id)
        )


# --- User Preferences -------------------------------------------------------

def get_user_preferences(user_id: str):
    """Get user preferences (dark_mode, filters, notification settings)"""
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM user_preferences WHERE user_id = ?", (user_id,)).fetchone()
        return dict(row) if row else None


def upsert_user_preferences(user_id: str, **kwargs):
    """Save or update user preferences"""
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO user_preferences(user_id, dark_mode, default_filters, layout_settings,
               notification_email, notifications_enabled)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET
               dark_mode = COALESCE(excluded.dark_mode, dark_mode),
               default_filters = COALESCE(excluded.default_filters, default_filters),
               layout_settings = COALESCE(excluded.layout_settings, layout_settings),
               notification_email = COALESCE(excluded.notification_email, notification_email),
               notifications_enabled = COALESCE(excluded.notifications_enabled, notifications_enabled),
               updated_at = CURRENT_TIMESTAMP""",
            (user_id, kwargs.get('dark_mode'), kwargs.get('default_filters'),
             kwargs.get('layout_settings'), kwargs.get('notification_email'),
             kwargs.get('notifications_enabled', 1))
        )


def set_dark_mode(user_id: str, enabled: bool):
    """Set dark mode preference for user"""
    upsert_user_preferences(user_id, dark_mode=1 if enabled else 0)


def set_notification_email(user_id: str, email: str):
    """Set notification email for user"""
    upsert_user_preferences(user_id, notification_email=email)


def set_default_filters(user_id: str, filters_json: str):
    """Set default filters for user"""
    upsert_user_preferences(user_id, default_filters=filters_json)


# --- Dashboard Configs -------------------------------------------------------

def create_dashboard_config(config_id: str, user_id: str, name: str,
                            filters_json: str, metric_selection_json: str,
                            layout_json: str, is_shared: bool = False):
    """Create a new dashboard configuration"""
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO dashboard_configs(config_id, user_id, name, filters,
               metric_selection, layout, is_shared, is_default)
               VALUES (?, ?, ?, ?, ?, ?, ?, 0)""",
            (config_id, user_id, name, filters_json, metric_selection_json, layout_json, 1 if is_shared else 0)
        )


def get_dashboard_config(config_id: str):
    """Get a specific dashboard configuration"""
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM dashboard_configs WHERE config_id = ?", (config_id,)).fetchone()
        return dict(row) if row else None


def get_user_dashboards(user_id: str):
    """Get all dashboard configurations for a user"""
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM dashboard_configs WHERE user_id = ? ORDER BY updated_at DESC",
                           (user_id,)).fetchall()
        return [dict(r) for r in rows]


def update_dashboard_config(config_id: str, **kwargs):
    """Update a dashboard configuration"""
    with get_conn() as conn:
        updates = []
        params = []
        for key, value in kwargs.items():
            if key in ['name', 'filters', 'metric_selection', 'layout', 'is_shared', 'is_default']:
                updates.append(f"{key} = ?")
                params.append(value)

        if updates:
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(config_id)
            query = f"UPDATE dashboard_configs SET {', '.join(updates)} WHERE config_id = ?"
            conn.execute(query, params)


def delete_dashboard_config(config_id: str):
    """Delete a dashboard configuration"""
    with get_conn() as conn:
        conn.execute("DELETE FROM dashboard_configs WHERE config_id = ?", (config_id,))


def set_default_dashboard(user_id: str, config_id: str):
    """Set a dashboard as the default for a user"""
    with get_conn() as conn:
        # Clear other defaults
        conn.execute("UPDATE dashboard_configs SET is_default = 0 WHERE user_id = ?", (user_id,))
        # Set the specified one as default
        conn.execute("UPDATE dashboard_configs SET is_default = 1 WHERE config_id = ?", (config_id,))


# --- Alert Rules -------------------------------------------------------

def insert_alert_rule(rule_id: str, user_id: str, name: str, metric: str,
                     condition: str, threshold: float, action: str):
    """Create a new alert rule"""
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO alert_rules(rule_id, user_id, name, metric, condition, threshold, action)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (rule_id, user_id, name, metric, condition, threshold, action)
        )


def get_alert_rules(user_id: str = None, enabled_only: bool = False):
    """Get alert rules, optionally filtered by user and enabled status"""
    with get_conn() as conn:
        query = "SELECT * FROM alert_rules WHERE 1=1"
        params = []

        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)

        if enabled_only:
            query += " AND enabled = 1"

        query += " ORDER BY updated_at DESC"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def update_alert_rule(rule_id: str, **kwargs):
    """Update an alert rule"""
    with get_conn() as conn:
        updates = []
        params = []
        for key, value in kwargs.items():
            if key in ['name', 'metric', 'condition', 'threshold', 'action', 'action_target', 'enabled']:
                updates.append(f"{key} = ?")
                params.append(value)

        if updates:
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(rule_id)
            query = f"UPDATE alert_rules SET {', '.join(updates)} WHERE rule_id = ?"
            conn.execute(query, params)


def delete_alert_rule(rule_id: str):
    """Delete an alert rule"""
    with get_conn() as conn:
        conn.execute("DELETE FROM alert_rules WHERE rule_id = ?", (rule_id,))


def enable_alert_rule(rule_id: str):
    """Enable an alert rule"""
    update_alert_rule(rule_id, enabled=True)


def disable_alert_rule(rule_id: str):
    """Disable an alert rule"""
    update_alert_rule(rule_id, enabled=False)


# --- Alert History -------------------------------------------------------

def log_alert_trigger(rule_id: str, metric_value: float, threshold: float, action_taken: str = None):
    """Log an alert trigger event"""
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO alert_history(rule_id, metric_value, threshold, action_taken)
               VALUES (?, ?, ?, ?)""",
            (rule_id, metric_value, threshold, action_taken)
        )


def get_alert_history(rule_id: str, limit: int = 50):
    """Get alert trigger history for a rule"""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM alert_history WHERE rule_id = ? ORDER BY triggered_at DESC LIMIT ?",
            (rule_id, limit)
        ).fetchall()
        return [dict(r) for r in rows]


def get_active_alerts(user_id: str):
    """Get recently triggered alerts for a user"""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT ah.* FROM alert_history ah
               JOIN alert_rules ar ON ah.rule_id = ar.rule_id
               WHERE ar.user_id = ? AND ah.triggered_at >= datetime('now', '-1 day')
               ORDER BY ah.triggered_at DESC""",
            (user_id,)
        ).fetchall()
        return [dict(r) for r in rows]


# --- Filter Presets -------------------------------------------------------

def create_filter_preset(preset_id: str, user_id: str, name: str, filters_json: str):
    """Create a named filter preset"""
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO filter_presets(preset_id, user_id, name, filters)
               VALUES (?, ?, ?, ?)""",
            (preset_id, user_id, name, filters_json)
        )


def get_filter_presets(user_id: str):
    """Get all filter presets for a user"""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM filter_presets WHERE user_id = ? ORDER BY name",
            (user_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_filter_preset(preset_id: str):
    """Get a specific filter preset"""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM filter_presets WHERE preset_id = ?",
            (preset_id,)
        ).fetchone()
        return dict(row) if row else None


def delete_filter_preset(preset_id: str):
    """Delete a filter preset"""
    with get_conn() as conn:
        conn.execute("DELETE FROM filter_presets WHERE preset_id = ?", (preset_id,))
