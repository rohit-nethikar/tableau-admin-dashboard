"""Thin wrapper around `tableauserverclient` (TSC) for everything the REST API needs
to supply: projects, workbooks, data sources, users/groups, extract-refresh job
history, and permissions.

NOTE: exact attribute names on TSC's job/permission objects can shift slightly
between Tableau Server versions and TSC releases. The extraction helpers below are
written defensively (getattr with fallbacks) and are the most likely spot to need a
small tweak against your real server - see README.md.
"""
import contextlib
import json
import time
import urllib.request
from datetime import datetime, timezone

import tableauserverclient as TSC

VERSION_PROBE_ATTEMPTS = 3
VERSION_PROBE_RETRY_DELAY_SECONDS = 1.5


class ServerUnreachableError(Exception):
    """Raised when TSC can't determine the server's REST API version - usually a
    transient proxy/VPN/load-balancer hiccup on the unauthenticated /api/serverinfo
    probe TSC makes before sign-in. Without this check, that failure surfaces later as
    a cryptic `packaging.version.InvalidVersion: Invalid version: 'Unknown'` with no
    context. We retry a few times first since this has been observed to be
    intermittent (e.g. an F5 BIG-IP pool occasionally routing to a bad node)."""


def _connect_with_known_version(server_url: str) -> TSC.Server:
    last_seen_version = None
    for attempt in range(1, VERSION_PROBE_ATTEMPTS + 1):
        server = TSC.Server(server_url, use_server_version=True)
        if server.version and server.version != "Unknown":
            return server
        last_seen_version = server.version
        if attempt < VERSION_PROBE_ATTEMPTS:
            time.sleep(VERSION_PROBE_RETRY_DELAY_SECONDS)

    raise ServerUnreachableError(
        f"Could not determine the Tableau REST API version from {server_url}/api/2.4/serverinfo "
        f"after {VERSION_PROBE_ATTEMPTS} attempts (got {last_seen_version!r} each time). This usually "
        "means a proxy, VPN, or load balancer is intermittently returning something other than the "
        "expected XML rather than a bad token - try again shortly, or run "
        f"'curl {server_url}/api/2.4/serverinfo' repeatedly from the same machine to see how often it "
        "happens outside this app too."
    )


@contextlib.contextmanager
def signed_in_server(server_url: str, site_name: str, pat_name: str, pat_secret: str):
    """Yields a signed-in TSC Server object. Also exposes `server.auth_token` and
    `server.site_id` for reuse by metadata_client.py's raw GraphQL calls."""
    server = _connect_with_known_version(server_url)
    auth = TSC.PersonalAccessTokenAuth(pat_name, pat_secret, site_id=site_name)
    with server.auth.sign_in(auth):
        yield server


def list_users_full(server) -> list:
    """Returns (id, name, email, site_role, last_login_at, fetched_at) tuples for the
    full user roster - needed for orphaned-content detection (inactive/deleted owner,
    service account) which list_users_by_id()'s bare id->name map can't support."""
    fetched_at = datetime.now(timezone.utc).isoformat()
    rows = []
    for user in TSC.Pager(server.users):
        last_login = getattr(user, "last_login", None)
        rows.append(
            (
                user.id,
                user.name,
                getattr(user, "email", None),
                getattr(user, "site_role", None),
                last_login.isoformat() if last_login else None,
                fetched_at,
            )
        )
    return rows


def list_projects(server) -> list:
    rows = []
    projects_by_id = {}
    for project in TSC.Pager(server.projects):
        projects_by_id[project.id] = project
        rows.append((project.id, project.name, project.parent_id))
    return rows, projects_by_id


def list_workbooks(server, users_by_id: dict, projects_by_id: dict) -> list:
    """Returns WorkbookItem objects (not yet flattened) so the caller can also use
    them for lineage name-matching."""
    return list(TSC.Pager(server.workbooks))


def list_datasources(server) -> list:
    return list(TSC.Pager(server.datasources))


def _summarize_connection_types(connections) -> str:
    """TSC's ConnectionItem.connection_type is the underlying DB driver name (e.g.
    "postgres", "hyper"), not a literal live/extract flag - "hyper" is the value used
    for the extract engine, everything else is a live connection. A resource can have
    both (e.g. a live connection alongside an extract), hence "Mixed"."""
    if not connections:
        return None
    types = {"Extract" if getattr(c, "connection_type", None) == "hyper" else "Live" for c in connections}
    return "Mixed (Live + Extract)" if len(types) > 1 else types.pop()


def enrich_workbooks(server, workbooks: list) -> tuple:
    """Returns ({workbook_id: {...}}, [(workbook_id, workbook_name, view_name, total_views), ...])
    tuple. The first element is the detail dict as before: {workbook_id: {"view_count",
    "sheet_count", "connection_count", "connection_type", "revision_count"}}. The second
    element is a list of per-sheet tuples for populating the workbook_views table.

    view_count/sheet_count come from the includeUsageStatistics=true view listing - a
    real REST endpoint that works even while the Metadata API is disabled/unreachable,
    see README.md. connection_count/connection_type/revision_count come from the same
    populate_connections call; revision_count is capped by the server's configured
    revision-retention setting, not true unlimited history. Each of the three calls is
    independently try/except-wrapped so one failing call for one workbook (e.g. a
    permissions edge case) doesn't lose the other two, and a workbook that fails all
    three simply gets all-None values rather than being dropped or failing the whole
    sync."""
    detail = {}
    view_rows = []
    for wb in workbooks:
        entry = {
            "view_count": None,
            "sheet_count": None,
            "connection_count": None,
            "connection_type": None,
            "revision_count": None,
        }
        try:
            server.workbooks.populate_views(wb, usage=True)
            entry["view_count"] = sum((v.total_views or 0) for v in wb.views)
            entry["sheet_count"] = len(wb.views)
            for v in wb.views:
                view_rows.append((wb.id, wb.name, v.name, v.total_views or 0))
        except Exception:
            pass
        try:
            server.workbooks.populate_connections(wb)
            entry["connection_count"] = len(wb.connections)
            entry["connection_type"] = _summarize_connection_types(wb.connections)
        except Exception:
            pass
        try:
            server.workbooks.populate_revisions(wb)
            entry["revision_count"] = len(wb.revisions)
        except Exception:
            pass
        detail[wb.id] = entry
    return detail, view_rows


def _summarize_underlying_sources(connections) -> str:
    """Per-connection detail beyond the coarse Live/Extract/Mixed summary: what
    driver/server each connection actually points at, or - when a connection's
    target is itself another published data source rather than a raw DB/file (TSC's
    ConnectionItem.datasource_name is only populated in that case) - that chained
    data source's name."""
    if not connections:
        return None
    parts = []
    for c in connections:
        if getattr(c, "datasource_name", None):
            parts.append(f"Published Data Source: {c.datasource_name}")
        else:
            ctype = getattr(c, "connection_type", None) or "unknown"
            addr = getattr(c, "server_address", None)
            parts.append(f"{ctype} ({addr})" if addr else ctype)
    seen = []
    for p in parts:
        if p not in seen:
            seen.append(p)
    return ", ".join(seen)


def enrich_datasources(server, datasources: list) -> dict:
    """Returns {datasource_id: {"connection_count", "connection_type",
    "underlying_sources", "revision_count"}} via two extra per-datasource REST
    calls - no usage/views equivalent exists for data sources (see
    metadata_client.py's docstring), so those keys aren't included here. Same
    independent try/except pattern as enrich_workbooks."""
    detail = {}
    for ds in datasources:
        entry = {
            "connection_count": None,
            "connection_type": None,
            "underlying_sources": None,
            "revision_count": None,
        }
        try:
            server.datasources.populate_connections(ds)
            entry["connection_count"] = len(ds.connections)
            entry["connection_type"] = _summarize_connection_types(ds.connections)
            entry["underlying_sources"] = _summarize_underlying_sources(ds.connections)
        except Exception:
            pass
        try:
            server.datasources.populate_revisions(ds)
            entry["revision_count"] = len(ds.revisions)
        except Exception:
            pass
        detail[ds.id] = entry
    return detail


def list_custom_views(server) -> list:
    """Returns (id, name, workbook_name, view_name, owner_name, shared, created_at,
    updated_at, last_accessed_at) tuples for every Custom View (Tableau's
    saved-view-per-user feature) the signed-in account can see. Non-admin PATs may
    only see custom views they own or that are marked shared (a Tableau Server-side
    restriction, not something this app controls).

    Uses a raw REST call with `includeUsageStatistics=true` instead of TSC's
    `server.custom_views.get()`/`TSC.Pager`, because TSC (as of 0.32) doesn't expose
    that query parameter for the custom-views endpoint even though the underlying
    Tableau REST API (3.21+) supports it and returns `lastAccessedAt` per view. Each
    item is independently try/except-wrapped so one malformed entry doesn't drop the
    rest."""
    rows = []
    page_number = 1
    page_size = 100
    while True:
        url = (
            f"{server.custom_views.baseurl}"
            f"?includeUsageStatistics=true&pageSize={page_size}&pageNumber={page_number}"
        )
        request = urllib.request.Request(
            url,
            headers={"X-Tableau-Auth": server.auth_token, "Accept": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))

        items = payload.get("customViews", {}).get("customView") or []
        if isinstance(items, dict):
            # Tableau's JSON API collapses a single-item page to a dict instead of a list.
            items = [items]

        for cv in items:
            try:
                workbook = cv.get("workbook") or {}
                view = cv.get("view") or {}
                owner = cv.get("owner") or {}
                rows.append(
                    (
                        cv.get("id"),
                        cv.get("name"),
                        workbook.get("name"),
                        view.get("name"),
                        owner.get("name"),
                        1 if cv.get("shared") else 0,
                        cv.get("createdAt"),
                        cv.get("updatedAt"),
                        cv.get("lastAccessedAt"),
                    )
                )
            except Exception:
                continue

        pagination = payload.get("pagination", {})
        total_available = int(pagination.get("totalAvailable", 0))
        if page_number * page_size >= total_available:
            break
        page_number += 1

    return rows


def list_subscriptions(server, users_by_id: dict, workbook_names_by_id: dict) -> list:
    """Returns (id, subscriber_name, subject, target_type, target_name, suspended)
    tuples for every subscription (a user receiving emailed snapshots of a workbook or
    view on a schedule) site-wide. target_type is "Workbook" or "View" - workbook
    names are resolved from the already-cached workbook list (workbook_names_by_id);
    view names need one extra bulk TSC.Pager(server.views) call (same cost class as
    the other bulk listings - no per-item REST calls). Each item is independently
    try/except-wrapped so one malformed entry doesn't drop the rest."""
    view_names_by_id = {}
    try:
        for view in TSC.Pager(server.views):
            view_names_by_id[view.id] = view.name
    except Exception:
        pass

    rows = []
    for sub in TSC.Pager(server.subscriptions):
        try:
            target = getattr(sub, "target", None)
            target_type = getattr(target, "type", None) if target else None
            target_id = getattr(target, "id", None) if target else None
            if target_type == "Workbook":
                target_name = workbook_names_by_id.get(target_id)
            elif target_type == "View":
                target_name = view_names_by_id.get(target_id)
            else:
                target_name = None
            rows.append(
                (
                    sub.id,
                    users_by_id.get(sub.user_id, sub.user_id),
                    getattr(sub, "subject", None),
                    target_type,
                    target_name,
                    1 if getattr(sub, "suspended", False) else 0,
                )
            )
        except Exception:
            continue
    return rows


def list_groups_with_members(server) -> list:
    """Returns (group_name, user_name) tuples, flattening group -> member users."""
    rows = []
    for group in TSC.Pager(server.groups):
        try:
            server.groups.populate_users(group)
            for user in group.users:
                rows.append((group.name, user.name))
        except Exception:
            # some groups (e.g. "All Users") may not support enumeration on older
            # server versions - skip rather than fail the whole sync
            continue
    return rows


def _job_finish_status(finish_code) -> str:
    mapping = {0: "Success", 1: "Failed", 2: "Cancelled"}
    try:
        return mapping.get(int(finish_code), "Unknown")
    except (TypeError, ValueError):
        return "Unknown"


EXTRACT_JOB_DETAIL_LOOKUP_LIMIT = 150


def list_extract_refresh_status(server) -> dict:
    """Returns {resource_id: {'status': ..., 'last_run_at': iso_string,
    'consecutive_failures': int, 'notes': str or None,
    'last_run_duration_seconds': int or None}} built from every extract-refresh
    job per workbook/datasource, via the Jobs REST endpoint.

    last_run_duration_seconds is completed_at - started_at for the most recent job,
    rounded to whole seconds. It's None whenever either timestamp is missing (e.g. a
    job that was cancelled before starting, or one that's still running).

    TSC.Pager(server.jobs) (the Jobs LIST endpoint) only returns BackgroundJobItem
    objects - status/type/timestamps, but no workbook_id/datasource_id/notes at all.
    That resource association and the job notes only exist on the richer JobItem
    returned by a *separate*, per-job call (server.jobs.get_by_id(job_id)). So for
    every list-returned job that looks like an extract/refresh (by .type), we make one
    extra detail call to resolve which resource it belongs to. To bound the added
    per-sync latency as job history grows, we only do this for the most recently
    created EXTRACT_JOB_DETAIL_LOOKUP_LIMIT matching jobs - in practice recent history
    is all that's needed for current status and a consecutive-failure streak anyway.
    Each detail call is independently try/except-wrapped so one bad job id can't lose
    the rest.

    consecutive_failures counts back from the most recent job until the first
    non-Failed one - bounded both by the above lookup cap and by however much job
    history Tableau Server currently retains, not true unlimited history, same caveat
    as refresh_health.py's site-wide consecutive-failure count."""
    try:
        background_jobs = list(TSC.Pager(server.jobs))
    except Exception:
        return {}

    def _sort_key(j):
        created_at = getattr(j, "created_at", None)
        return created_at or datetime.min.replace(tzinfo=timezone.utc)

    candidate_jobs = [
        j for j in background_jobs
        if "extract" in (getattr(j, "type", "") or "").lower()
        or "refresh" in (getattr(j, "type", "") or "").lower()
    ]
    candidate_jobs.sort(key=_sort_key, reverse=True)
    candidate_jobs = candidate_jobs[:EXTRACT_JOB_DETAIL_LOOKUP_LIMIT]

    jobs_by_resource = {}
    for bg_job in candidate_jobs:
        try:
            job = server.jobs.get_by_id(bg_job.id)
        except Exception:
            continue

        resource_id = getattr(job, "workbook_id", None) or getattr(job, "datasource_id", None)
        if resource_id is None:
            continue

        started_at = getattr(job, "started_at", None)
        completed_at = getattr(job, "completed_at", None)
        sort_dt = completed_at or started_at
        status = _job_finish_status(getattr(job, "finish_code", None))
        notes = getattr(job, "notes", None)
        jobs_by_resource.setdefault(resource_id, []).append(
            (sort_dt or datetime.min.replace(tzinfo=timezone.utc), status, notes, started_at, completed_at)
        )

    result = {}
    for resource_id, entries in jobs_by_resource.items():
        entries.sort(key=lambda e: e[0], reverse=True)
        latest_dt, latest_status, latest_notes, latest_started_at, latest_completed_at = entries[0]
        consecutive_failures = 0
        for _, status, _notes, _started_at, _completed_at in entries:
            if status == "Failed":
                consecutive_failures += 1
            else:
                break
        duration_seconds = None
        if latest_started_at and latest_completed_at:
            duration_seconds = round((latest_completed_at - latest_started_at).total_seconds())
        result[resource_id] = {
            "status": latest_status,
            "last_run_at": latest_dt.isoformat() if latest_dt > datetime.min.replace(tzinfo=timezone.utc) else None,
            "consecutive_failures": consecutive_failures,
            "notes": "; ".join(latest_notes) if latest_notes else None,
            "last_run_duration_seconds": duration_seconds,
        }
    return result


_INTERVAL_TYPE_TO_FREQUENCY = {
    "HourlyInterval": "Hourly",
    "DailyInterval": "Daily",
    "WeeklyInterval": "Weekly",
    "MonthlyInterval": "Monthly",
}


def list_extract_refresh_schedules(server) -> dict:
    """Returns {target_id: {"schedule_name", "next_run_at" (ISO string),
    "frequency", "schedule_state"}} - the *next scheduled* extract-refresh run per
    workbook/data source, distinct from list_extract_refresh_status()'s *last run*
    history. Built from TSC's site-scoped Tasks endpoint (server.tasks), which is
    already reachable with the same site-admin PAT this app requires for everything
    else - no elevated permission needed. If a target has more than one extract
    task (uncommon but possible), the one with the soonest next_run_at wins. A
    target with no schedule (e.g. all-live-connection content, or one only ever
    refreshed on demand) simply has no entry."""
    result = {}
    for task in TSC.Pager(server.tasks):
        target = getattr(task, "target", None)
        schedule = getattr(task, "schedule_item", None)
        if target is None or schedule is None:
            continue
        next_run_at = getattr(schedule, "next_run_at", None)
        interval_item = getattr(schedule, "interval_item", None)
        frequency = _INTERVAL_TYPE_TO_FREQUENCY.get(type(interval_item).__name__) if interval_item else None
        entry = {
            "schedule_name": getattr(schedule, "name", None),
            "next_run_at": next_run_at.isoformat() if next_run_at else None,
            "frequency": frequency,
            "schedule_state": getattr(schedule, "state", None),
        }
        existing = result.get(target.id)
        if existing is None or (
            entry["next_run_at"] and (not existing["next_run_at"] or entry["next_run_at"] < existing["next_run_at"])
        ):
            result[target.id] = entry
    return result


def list_connected_apps(server) -> list:
    """Returns (client_id, name, enabled, project_scope, domain_safelist,
    unrestricted_embedding, created_at) tuples for the site's Connected Apps
    (OAuth/JWT direct-trust relationships used for embedding and external REST API
    access). TSC (as of 0.32) has no wrapper for this endpoint at all, so this uses
    the same raw-REST/JSON approach as list_custom_views() above. Requires the
    signed-in PAT to belong to a server or site admin, and Tableau Server 2022.3+
    (REST API 3.17+) - on an older server or non-admin PAT this call raises, which
    the caller (sync_service.py) treats as an independent, non-fatal sync error like
    every other optional section."""
    url = f"{server.baseurl}/sites/{server.site_id}/connected-apps/direct-trust"
    request = urllib.request.Request(
        url,
        headers={"X-Tableau-Auth": server.auth_token, "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))

    # Tableau's connected-apps response wraps the list under "connectedApplications" ->
    # "connectedApplication" (the shared type name with the older, deprecated
    # connected-applications endpoint). Falls back to a "connectedApps" wrapper
    # defensively in case a given server version names it differently - this is a
    # newer, less-documented endpoint TSC itself doesn't wrap yet.
    wrapper = payload.get("connectedApplications") or payload.get("connectedApps") or {}
    apps = wrapper.get("connectedApplication") or wrapper.get("connectedApp") or []
    if isinstance(apps, dict):
        # Tableau's JSON API collapses a single-item collection to a dict instead of a list.
        apps = [apps]

    rows = []
    for app in apps:
        try:
            project_ids = app.get("projectIds") or []
            if isinstance(project_ids, dict):
                project_ids = [project_ids]
            project_scope = "All Projects" if not project_ids else ", ".join(str(p) for p in project_ids)
            rows.append(
                (
                    app.get("clientId"),
                    app.get("name"),
                    1 if app.get("enabled") else 0,
                    project_scope,
                    app.get("domainSafelist") or "",
                    1 if app.get("unrestrictedEmbedding") else 0,
                    app.get("createdAt"),
                )
            )
        except Exception:
            continue
    return rows


_JOB_STATUS_LABELS = {
    "Pending": "Pending",
    "InProgress": "In Progress",
    "Success": "Success",
    "Failed": "Failed",
    "Cancelled": "Cancelled",
}


def list_background_jobs(server) -> list:
    """All current/recent background jobs on the site (extract refreshes,
    subscriptions, flow runs, etc.) via the site-scoped Jobs LIST endpoint
    (TSC.Pager(server.jobs) -> BackgroundJobItem). No per-job detail call needed."""
    jobs = []
    for job in TSC.Pager(server.jobs):
        status = getattr(job, "status", None)
        jobs.append({
            "id": job.id,
            "type": getattr(job, "type", None),
            "status": status,
            "status_label": _JOB_STATUS_LABELS.get(status, status),
            "title": getattr(job, "title", None),
            "subtitle": getattr(job, "subtitle", None),
            "priority": getattr(job, "priority", None),
            "created_at": job.created_at.isoformat() if getattr(job, "created_at", None) else None,
            "started_at": job.started_at.isoformat() if getattr(job, "started_at", None) else None,
            "ended_at": job.ended_at.isoformat() if getattr(job, "ended_at", None) else None,
            "cancellable": status in ("Pending", "InProgress"),
        })
    return jobs


def cancel_job(server, job_id: str):
    """Cancels a Pending/InProgress job. Raises on failure (already completed,
    insufficient permission) - the caller flashes the error rather than
    swallowing it, since this is a direct user-initiated write action."""
    server.jobs.cancel(job_id)


def _capabilities_to_str(capabilities: dict) -> str:
    allowed = [name for name, mode in (capabilities or {}).items() if str(mode).lower() == "allow"]
    return ", ".join(sorted(allowed))


def _grantee_row(rule, resource_type, resource_name, project_name, source):
    grantee = rule.grantee
    grantee_type = getattr(grantee, "tag_name", None) or type(grantee).__name__.replace("Item", "").lower()
    grantee_name = getattr(grantee, "name", None) or getattr(grantee, "id", "unknown")
    return (
        resource_type,
        resource_name,
        project_name,
        grantee_type,
        grantee_name,
        _capabilities_to_str(rule.capabilities),
        # Full Allow/Deny map (not just the allow-only comma string above) - permission_risk.py
        # needs Deny entries too, to flag same-resource Allow-vs-Deny conflicts across grantees.
        json.dumps(rule.capabilities or {}),
        source,
    )


def list_permissions(server, projects_by_id: dict, workbooks: list) -> list:
    """Flattened permission grants: explicit project/workbook rules plus each
    project's default-permission templates (what new content inherits at creation)."""
    rows = []

    for project in projects_by_id.values():
        try:
            server.projects.populate_permissions(project)
            for rule in project.permissions:
                rows.append(_grantee_row(rule, "project", project.name, project.name, "explicit"))
        except Exception:
            pass

        try:
            server.projects.populate_workbook_default_permissions(project)
            for rule in project.default_workbook_permissions:
                rows.append(
                    _grantee_row(rule, "project_default_workbook", project.name, project.name, "project_default")
                )
        except Exception:
            pass

    for workbook in workbooks:
        try:
            server.workbooks.populate_permissions(workbook)
            for rule in workbook.permissions:
                rows.append(
                    _grantee_row(rule, "workbook", workbook.name, workbook.project_name, "explicit")
                )
        except Exception:
            continue

    return rows


def list_data_alerts(server, users_by_id: dict) -> list:
    """Returns (id, subject, creator_id, creator_name, owner_id, owner_name,
    created_at, updated_at, frequency, public, view_id, view_name, workbook_id,
    workbook_name, project_id, project_name, recipients) tuples for every
    Data-Driven Alert on the site. Tableau's REST API never exposes the alert's
    threshold condition (only frequency/subject/recipients/public/target) - see
    README.md. frequency here is the check-frequency, not a threshold."""
    rows = []
    for alert in TSC.Pager(server.data_alerts):
        created_at = getattr(alert, "createdAt", None)
        updated_at = getattr(alert, "updatedAt", None)
        creator_id = getattr(alert, "creatorId", None)
        recipient_ids = getattr(alert, "recipients", None) or []
        recipient_names = ", ".join(sorted(users_by_id.get(r, r) for r in recipient_ids))
        rows.append(
            (
                alert.id,
                getattr(alert, "subject", None),
                creator_id,
                users_by_id.get(creator_id, creator_id),
                getattr(alert, "owner_id", None),
                getattr(alert, "owner_name", None),
                created_at.isoformat() if hasattr(created_at, "isoformat") else created_at,
                updated_at.isoformat() if hasattr(updated_at, "isoformat") else updated_at,
                getattr(alert, "frequency", None),
                1 if getattr(alert, "public", False) else 0,
                getattr(alert, "view_id", None),
                getattr(alert, "view_name", None),
                getattr(alert, "workbook_id", None),
                getattr(alert, "workbook_name", None),
                getattr(alert, "project_id", None),
                getattr(alert, "project_name", None),
                recipient_names,
            )
        )
    return rows


def list_webhooks(server, users_by_id: dict) -> list:
    """Returns (id, name, url, event, owner_id, owner_name) tuples. There is no
    enabled/disabled flag anywhere in the real Tableau REST API for webhooks - see
    README.md."""
    rows = []
    for hook in TSC.Pager(server.webhooks):
        owner_id = getattr(hook, "owner_id", None)
        rows.append(
            (
                hook.id,
                hook.name,
                getattr(hook, "url", None),
                getattr(hook, "event", None),
                owner_id,
                users_by_id.get(owner_id, owner_id),
            )
        )
    return rows


def list_site_settings(server) -> dict:
    """Returns a flat dict of site-level configuration/quota settings for the
    currently signed-in site (server.sites.get_by_id enforces client-side that you
    can only fetch the currently-authenticated site). Deliberately omits
    .user_quota, which raises a UserWarning and returns None whenever tier
    capacities are set."""
    site = server.sites.get_by_id(server.site_id)
    return {
        "extract_encryption_mode": getattr(site, "extract_encryption_mode", None),
        "storage_quota": getattr(site, "storage_quota", None),
        "storage_used": getattr(site, "storage", None),
        "tier_creator_capacity": getattr(site, "tier_creator_capacity", None),
        "tier_explorer_capacity": getattr(site, "tier_explorer_capacity", None),
        "tier_viewer_capacity": getattr(site, "tier_viewer_capacity", None),
        "ask_data_mode": getattr(site, "ask_data_mode", None),
        "guest_access_enabled": 1 if getattr(site, "guest_access_enabled", False) else 0,
        "disable_subscriptions": 1 if getattr(site, "disable_subscriptions", False) else 0,
        "revision_history_enabled": 1 if getattr(site, "revision_history_enabled", False) else 0,
        "revision_limit": getattr(site, "revision_limit", None),
    }


def get_server_info(server) -> dict:
    """Returns product_version/build_number/rest_api_version for the physical
    Tableau Server installation itself, not any one site - identical no matter
    which configured site is currently signed in. Backed by TSC's unauthenticated
    /serverInfo endpoint (server.server_info), which is already fetched as a side
    effect of _connect_with_known_version's use_server_version=True, so this read
    costs no extra REST call."""
    info = server.server_info.serverInfo
    return {
        "product_version": getattr(info, "product_version", None),
        "build_number": getattr(info, "build_number", None),
        "rest_api_version": getattr(info, "rest_api_version", None),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


def list_favorites_totals(server) -> dict:
    """Returns {resource_id: favorites_count} for workbooks and datasources
    combined, read from the raw REST list-endpoint JSON's favoritesTotal field.
    TSC's model classes (as of 0.32) don't expose this field even though the
    underlying endpoint returns it, and there is no site-wide favorites endpoint in
    the Tableau REST API at all (TSC.Favorites.get() is per-user only) - so this is
    the only way to get an aggregate count. Same raw-REST pattern as
    list_custom_views/list_connected_apps."""
    totals = {}
    for baseurl, wrapper_key, item_key in (
        (server.workbooks.baseurl, "workbooks", "workbook"),
        (server.datasources.baseurl, "datasources", "datasource"),
    ):
        page_number = 1
        page_size = 100
        while True:
            url = f"{baseurl}?pageSize={page_size}&pageNumber={page_number}"
            request = urllib.request.Request(
                url,
                headers={"X-Tableau-Auth": server.auth_token, "Accept": "application/json"},
            )
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))

            items = payload.get(wrapper_key, {}).get(item_key) or []
            if isinstance(items, dict):
                # Tableau's JSON API collapses a single-item page to a dict instead of a list.
                items = [items]

            for item in items:
                try:
                    favorites_total = item.get("favoritesTotal")
                    if favorites_total is not None:
                        totals[item.get("id")] = int(favorites_total)
                except Exception:
                    continue

            pagination = payload.get("pagination", {})
            total_available = int(pagination.get("totalAvailable", 0))
            if page_number * page_size >= total_available:
                break
            page_number += 1
    return totals


def list_data_quality_warnings(server, datasources: list) -> list:
    """Returns (resource_type, resource_id, resource_name, warning_type, severe,
    message, created_at) tuples. DQW only exists on datasource/database/table/flow
    in TSC 0.32 - not workbooks - so this is scoped to datasources only. Each
    datasource's populate_dqw call is independently try/except-wrapped so one
    failing lookup doesn't lose the rest."""
    rows = []
    for ds in datasources:
        try:
            server.datasources.populate_dqw(ds)
            for dqw in (ds.dqws or []):
                created_at = getattr(dqw, "created_at", None)
                rows.append(
                    (
                        "datasource",
                        ds.id,
                        ds.name,
                        getattr(dqw, "warning_type", None),
                        1 if getattr(dqw, "severe", False) else 0,
                        getattr(dqw, "message", None),
                        created_at.isoformat() if hasattr(created_at, "isoformat") else created_at,
                    )
                )
        except Exception:
            continue
    return rows
