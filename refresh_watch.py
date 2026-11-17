"""Tracks, per browser session, whether a just-triggered refresh for a site is still
in flight - lets the UI auto-reload once it finishes instead of a static "reload in a
moment" message. Deliberately session-based (unlike site_context.py) since this is
purely about one browser's polling, not something the scheduler thread needs."""
from flask import session

import db


def start_watching(site: str):
    """Call right before triggering (or queuing) a refresh for `site`, so is_pending()
    can recognize the moment it actually completes."""
    baseline = db.latest_refresh(site)
    session["refresh_watch"] = {"site": site, "baseline_id": baseline["id"] if baseline else 0}


def is_pending(site: str) -> bool:
    watch = session.get("refresh_watch")
    if not watch or watch.get("site") != site:
        return False
    latest = db.latest_refresh(site)
    if latest and latest["status"] != "running" and latest["id"] > watch["baseline_id"]:
        session.pop("refresh_watch", None)
        return False
    return True
