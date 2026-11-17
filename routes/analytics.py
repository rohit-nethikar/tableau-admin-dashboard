from datetime import datetime, timedelta, timezone
from flask import Blueprint, render_template, request

import db
import site_context
from auth import login_required

bp = Blueprint("analytics", __name__)

_RANGE_DAYS = {"7days": 7, "30days": 30, "90days": 90}


def _cutoff_datetime(date_range):
    """Returns a datetime cutoff for the given range, or None for 'all'."""
    if date_range not in _RANGE_DAYS:
        return None
    days = _RANGE_DAYS[date_range]
    return datetime.now(timezone.utc) - timedelta(days=days)


def _filter_by_recency(items, date_field, cutoff, workbooks_by_id=None):
    """Filter items by recency. If date_field is None, uses parent workbook's updated_at."""
    if cutoff is None:
        return items
    filtered = []
    for item in items:
        if date_field is None:
            # For views: get date from parent workbook
            wb = workbooks_by_id.get(item.get("workbook_id"))
            if not wb:
                continue
            date_str = wb.get("updated_at")
        else:
            date_str = item.get(date_field)
        if not date_str:
            continue
        try:
            item_date = datetime.fromisoformat(date_str)
            if item_date.tzinfo is None:
                item_date = item_date.replace(tzinfo=timezone.utc)
            if item_date >= cutoff:
                filtered.append(item)
        except ValueError:
            continue
    return filtered


def _top_avg_views_per_month(workbooks, top_n=10):
    """Calculate top workbooks by average views per month since creation."""
    data = []
    now = datetime.now(timezone.utc)
    for wb in workbooks:
        created_at_str = wb.get("created_at")
        total_views = wb.get("lifetime_view_count") or 0
        if not created_at_str:
            continue
        try:
            created_at = datetime.fromisoformat(created_at_str)
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            days_since_creation = max(1, (now - created_at).days)
            months_since_creation = max(1, days_since_creation / 30.0)
            avg_per_month = total_views / months_since_creation
            data.append({
                "id": wb["id"],
                "name": wb["name"],
                "lifetime_view_count": total_views,
                "avg_views_per_month": round(avg_per_month, 1),
            })
        except ValueError:
            continue
    return sorted(data, key=lambda x: x["avg_views_per_month"], reverse=True)[:top_n]


def _login_recency_buckets(users, cutoff):
    """Group users by last login recency into named buckets."""
    buckets = {
        "≤7 days": 0,
        "8-30 days": 0,
        "31-90 days": 0,
        "91-365 days": 0,
        ">1 year": 0,
        "Never": 0,
    }
    now = datetime.now(timezone.utc)
    for user in users:
        last_login_str = user.get("last_login_at")
        if not last_login_str:
            buckets["Never"] += 1
            continue
        try:
            last_login = datetime.fromisoformat(last_login_str)
            if last_login.tzinfo is None:
                last_login = last_login.replace(tzinfo=timezone.utc)
            days_since_login = (now - last_login).days
            # If cutoff is set, only count users who logged in on/after cutoff
            if cutoff and last_login < cutoff:
                continue
            if days_since_login <= 7:
                buckets["≤7 days"] += 1
            elif days_since_login <= 30:
                buckets["8-30 days"] += 1
            elif days_since_login <= 90:
                buckets["31-90 days"] += 1
            elif days_since_login <= 365:
                buckets["91-365 days"] += 1
            else:
                buckets[">1 year"] += 1
        except ValueError:
            buckets["Never"] += 1
    return buckets


@bp.route("/analytics")
@login_required
def show_analytics():
    site = site_context.get_current_site()
    date_range = request.args.get("range", "all")
    workbook_filter = request.args.get("workbook_id") or None
    cutoff = _cutoff_datetime(date_range)

    # Fetch limited datasets optimized for analytics
    workbooks = db.fetch_workbooks(site)[:500]  # Limit to top 500 by relevance
    all_views = db.fetch_workbook_views(site)[:1000]  # Limit to top 1000 views
    users = db.fetch_users(site)  # Still fetch all users for login recency calculation
    user_stats = db.get_user_activity_stats(site)
    custom_views = db.fetch_custom_views_summary(site, limit=500)

    # Summary stats: optimized with aggregated queries
    summary = {
        "total_view_hits": sum(wb.get("lifetime_view_count") or 0 for wb in workbooks[:100]),  # Use top 100 instead of all
        "workbook_count": db.count_workbooks(site),
        "view_count": len(all_views),
        "user_count": user_stats["total_users"],
        "active_users_30d": user_stats["active_30d"],
        "never_signed_in": user_stats["never_logged_in"],
        "custom_view_count": len(custom_views),
        "custom_view_owners": len({cv.get("owner_name") for cv in custom_views if cv.get("owner_name")}),
        "custom_view_domains": len(_get_unique_domains([cv.get("owner_name") for cv in custom_views if cv.get("owner_name")])),
    }

    # Top workbooks by hits - workbooks updated within the selected date range, sorted by popularity
    # Note: lifetime_view_count is all-time metric (API limitation), but we filter by updated_at within range
    filtered_workbooks = _filter_by_recency(workbooks, "updated_at", cutoff)
    if filtered_workbooks:
        top_by_hits = sorted(
            filtered_workbooks,
            key=lambda w: (w.get("lifetime_view_count") or 0, w.get("updated_at") or ""),
            reverse=True,
        )[:10]
    else:
        # If no workbooks updated in range, show most popular overall
        top_by_hits = sorted(
            workbooks,
            key=lambda w: w.get("lifetime_view_count") or 0,
            reverse=True,
        )[:10]

    # Top workbooks by avg views/month - shows engagement trend, also filtered by date range
    top_by_avg_month = _top_avg_views_per_month(filtered_workbooks if filtered_workbooks else workbooks, top_n=10)

    # Top views by hits (optionally filtered by workbook)
    workbooks_by_id = {wb["id"]: wb for wb in workbooks}
    views_scope = [v for v in all_views if not workbook_filter or v.get("workbook_id") == workbook_filter]
    views_scope = _filter_by_recency(views_scope, None, cutoff, workbooks_by_id)
    top_views = sorted(
        views_scope,
        key=lambda v: v.get("total_views") or 0,
        reverse=True,
    )[:10]

    # User login recency buckets (filtered by date range)
    login_buckets = _login_recency_buckets(users, cutoff)

    # Custom views aggregations (filtered by workbook and date range)
    filtered_custom_views = [cv for cv in custom_views if not workbook_filter or cv.get("workbook_id") == workbook_filter]
    filtered_custom_views = _filter_by_recency(filtered_custom_views, "created_at", cutoff)
    workbooks_with_custom_views = _workbooks_with_custom_views(filtered_custom_views, top_n=10)
    owner_domain_split = _owner_domain_split(filtered_custom_views)
    top_owners = _top_owners(filtered_custom_views, top_n=10)

    # Workbook names for dropdown
    workbook_names = sorted({wb["name"] for wb in workbooks if wb.get("name")})

    return render_template(
        "analytics.html",
        summary=summary,
        top_by_hits=top_by_hits,
        top_by_avg_month=top_by_avg_month,
        top_views=top_views,
        login_buckets=login_buckets,
        workbooks_with_custom_views=workbooks_with_custom_views,
        owner_domain_split=owner_domain_split,
        top_owners=top_owners,
        workbook_names=workbook_names,
        current_range=date_range,
        current_workbook_filter=workbook_filter,
        last_refresh=db.latest_refresh(site),
    )


def _get_unique_domains(owner_emails):
    """Extract unique domains from email addresses."""
    domains = set()
    for email in owner_emails:
        if email and "@" in email:
            domains.add(email.split("@")[1])
    return domains


def _workbooks_with_custom_views(custom_views, top_n=10):
    """Count custom views per workbook, sorted by count descending."""
    wb_counts = {}
    for cv in custom_views:
        wb_name = cv.get("workbook_name")
        if wb_name:
            wb_counts[wb_name] = wb_counts.get(wb_name, 0) + 1
    return sorted(
        [{"name": wb, "custom_view_count": count} for wb, count in wb_counts.items()],
        key=lambda x: x["custom_view_count"],
        reverse=True,
    )[:top_n]


def _owner_domain_split(custom_views):
    """Count custom views by owner domain (email domain)."""
    domain_counts = {}
    for cv in custom_views:
        owner = cv.get("owner_name")
        if owner and "@" in owner:
            domain = owner.split("@")[1]
            domain_counts[domain] = domain_counts.get(domain, 0) + 1
    return domain_counts


def _top_owners(custom_views, top_n=10):
    """Get top owners by custom view count."""
    owner_counts = {}
    for cv in custom_views:
        owner = cv.get("owner_name")
        if owner:
            owner_counts[owner] = owner_counts.get(owner, 0) + 1
    return sorted(
        [{"name": owner, "custom_view_count": count} for owner, count in owner_counts.items()],
        key=lambda x: x["custom_view_count"],
        reverse=True,
    )[:top_n]


def _days_since_login(user):
    """Helper to calculate days since last login, or None if never logged in."""
    last_login_str = user.get("last_login_at")
    if not last_login_str:
        return None
    try:
        last_login = datetime.fromisoformat(last_login_str)
        if last_login.tzinfo is None:
            last_login = last_login.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - last_login).days
    except ValueError:
        return None
