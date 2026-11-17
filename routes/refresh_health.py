import re
from datetime import datetime

from flask import Blueprint, render_template

import crypto
import db
import scheduler
import site_context
import tableau_client
from auth import login_required
from config import settings

bp = Blueprint("refresh_health", __name__)

_DISPLAY_LIMIT = 30
_HISTORY_LIMIT = 100

# Lightweight redaction pass over refresh_log.detail for display only - the raw
# text (which may echo exception messages containing tokens/credentials) stays
# in the database for admin debugging via direct SQLite access.
_SECRET_PATTERNS = [
    re.compile(r"(?i)\b(token|password|secret|pat|authorization)\s*[:=]\s*\S+"),
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9\-._~+/]+=*"),
]


def _sanitize_detail(text):
    if not text:
        return text
    sanitized = text
    for pattern in _SECRET_PATTERNS:
        sanitized = pattern.sub("[redacted]", sanitized)
    return sanitized


def _duration_seconds(row):
    if not row.get("finished_at"):
        return None
    try:
        started = datetime.fromisoformat(row["started_at"])
        finished = datetime.fromisoformat(row["finished_at"])
        return (finished - started).total_seconds()
    except (TypeError, ValueError):
        return None


def _consecutive_failures(rows_desc):
    """Counts back from the most recent completed run. A run still 'running'
    doesn't count as a failure or break the streak; it's simply skipped."""
    count = 0
    for row in rows_desc:
        if row["status"] == "running":
            continue
        if row["status"] == "failed":
            count += 1
        else:
            break
    return count


def _last_successful(completed_rows_desc):
    for row in completed_rows_desc:
        if row["status"] == "success":
            return row
    return None


def _most_recent_extract_refresh(site):
    """Latest Tableau extract-refresh job timestamp seen across any workbook or
    data source - distinct from `last_successful`/`last_refresh` above, which
    describe this app's own cache sync, not Tableau's extract jobs. ISO8601
    strings sort correctly as plain text, so a max() over the raw values is enough."""
    timestamps = [
        row["extract_last_run_at"]
        for row in db.fetch_workbooks(site) + db.fetch_datasources(site)
        if row.get("extract_last_run_at")
    ]
    return max(timestamps) if timestamps else None


def _validate_all_sites():
    """Signs in to every configured site with the already-saved PAT and reports which
    ones fail - catches a typo'd/inaccessible site name without waiting for its next
    full refresh to fail."""
    pat_name = db.get_config("pat_name")
    pat_encrypted = db.get_config("pat_encrypted")
    if not pat_name or not pat_encrypted:
        return [{"site": s, "ok": False, "detail": "No PAT configured - complete /setup first."} for s in settings.sites]
    pat_secret = crypto.decrypt_value(pat_encrypted)

    results = []
    for site in settings.sites:
        try:
            with tableau_client.signed_in_server(settings.server_url, site, pat_name, pat_secret):
                results.append({"site": site, "ok": True, "detail": "Signed in OK"})
        except Exception as exc:
            results.append({"site": site, "ok": False, "detail": str(exc)})
    return results


def _render_refresh_health(site_validation=None):
    site = site_context.get_current_site()
    rows = db.fetch_refresh_log(site, limit=_HISTORY_LIMIT)
    for row in rows:
        row["duration_seconds"] = _duration_seconds(row)
        row["detail_sanitized"] = _sanitize_detail(row.get("detail"))

    completed = [r for r in rows if r["status"] != "running"]

    # Chronological (oldest to newest) so the trend chart reads left-to-right -
    # `completed` is newest-first, same order as `rows`/fetch_refresh_log.
    trend_series = [
        {"started_at": r["started_at"], "duration_seconds": round(r["duration_seconds"], 1)}
        for r in reversed(completed)
        if r["duration_seconds"] is not None
    ]

    return render_template(
        "refresh_health.html",
        rows=rows[:_DISPLAY_LIMIT],
        last_successful=_last_successful(completed),
        consecutive_failures=_consecutive_failures(rows),
        trend_series=trend_series,
        next_run=scheduler.get_next_run_time(),
        last_refresh=db.latest_refresh(site),
        most_recent_extract_refresh=_most_recent_extract_refresh(site),
        site_validation=site_validation,
    )


@bp.route("/refresh-health")
@login_required
def refresh_health():
    return _render_refresh_health()


@bp.route("/refresh-health/validate-sites", methods=["POST"])
@login_required
def validate_sites():
    return _render_refresh_health(site_validation=_validate_all_sites())
