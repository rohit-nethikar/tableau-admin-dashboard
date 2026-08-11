"""Background cache refresh on an interval, plus a manual trigger reused by the
POST /refresh route. Also includes lightweight real-time poller (5-10 min) for
job failures and content changes, separate from the main sync cycle (60 min)."""
import threading

from apscheduler.schedulers.background import BackgroundScheduler

import db
import sync_service
import background_poller
import tableau_client
from config import settings

_scheduler = None
_refresh_lock = threading.Lock()
_pending_site_refresh = None
_pending_all_sites = False


def trigger_refresh_async(site: str):
    """Runs a refresh of `site` in a background thread so the HTTP request returns
    immediately. If a refresh is already running, this one is queued (via
    _pending_site_refresh) rather than dropped or silently merged with whatever
    site the in-flight run happens to be on - _run_pending() starts it once that
    run finishes."""
    global _pending_site_refresh
    if _refresh_lock.locked():
        _pending_site_refresh = site
        return False
    thread = threading.Thread(target=_run_locked, args=(site,), daemon=True)
    thread.start()
    return True


def _run_locked(site):
    with _refresh_lock:
        sync_service.refresh_all(site)
    _run_pending()


def trigger_refresh_all_sites_async():
    """Refreshes every configured site, one after another, in a background thread.
    Shares _refresh_lock with the per-site refresh so the two can never overlap - a
    switch/manual refresh requested mid-run just queues behind it as usual."""
    global _pending_all_sites
    if _refresh_lock.locked():
        _pending_all_sites = True
        return False
    thread = threading.Thread(target=_run_all_sites_locked, daemon=True)
    thread.start()
    return True


def _run_all_sites_locked():
    with _refresh_lock:
        for site in settings.sites:
            sync_service.refresh_all(site)
    _run_pending()


def _run_pending():
    """After a locked run finishes, start whichever refresh (if any) was requested
    while it was in flight. An all-sites request takes priority since it's a
    superset of any single-site one that was also queued."""
    global _pending_all_sites, _pending_site_refresh
    if _pending_all_sites:
        _pending_all_sites = False
        _pending_site_refresh = None
        trigger_refresh_all_sites_async()
    elif _pending_site_refresh:
        site = _pending_site_refresh
        _pending_site_refresh = None
        trigger_refresh_async(site)


def _poll_all_sites():
    """Lightweight poller that runs every 5-10 minutes. Checks for new background
    job failures and content changes without waiting for the full 60-minute sync.
    Sends immediate alerts on detection."""
    for site in settings.sites:
        try:
            server = tableau_client.get_server(site)
            background_poller.poll_site(site, server)
        except Exception as exc:
            print(f"[POLLER] Error polling {site}: {exc}")
            import traceback
            traceback.print_exc()


def start(run_immediately: bool = True):
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    if run_immediately and db.is_setup_complete():
        trigger_refresh_all_sites_async()

    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.add_job(
        _run_all_sites_locked,
        "interval",
        minutes=settings.refresh_interval_minutes,
        id="refresh_all",
        replace_existing=True,
    )
    _scheduler.add_job(
        _poll_all_sites,
        "interval",
        minutes=5,
        id="poll_realtime",
        replace_existing=True,
    )
    _scheduler.start()
    return _scheduler


def get_next_run_time():
    """Returns the next scheduled automatic refresh time (a datetime, or None if the
    scheduler hasn't started yet), for the refresh-reliability page."""
    if _scheduler is None:
        return None
    job = _scheduler.get_job("refresh_all")
    return job.next_run_time if job else None
