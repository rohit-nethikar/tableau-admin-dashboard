"""Tracks background-job status across syncs so we can detect a job that just
failed (vs. one we've already alerted on) - the job-level equivalent of
sync_service._escalated() for workbook/datasource extract failures, but covering
every job type Tableau's Jobs endpoint returns (extracts, subscriptions, flow
runs, etc.), not only extract refreshes."""
import db


def detect_new_failures(site: str, jobs: list, now_iso: str) -> list:
    """Detect jobs whose status is newly 'Failed'. Upsert every job so we track
    state across syncs. Returns list of dicts for jobs that are newly failing."""
    new_failures = []
    for job in jobs:
        existing = db.fetch_background_job(job["id"])
        already_notified = existing is not None and existing.get("last_notified_status") == "Failed"
        if job["status"] == "Failed" and not already_notified:
            new_failures.append(job)
        db.upsert_background_job(
            job_id=job["id"],
            site=site,
            type_=job.get("type"),
            job_name=job.get("job_name"),
            resource_name=job.get("resource_name"),
            status=job.get("status"),
            created_at=job.get("created_at"),
            started_at=job.get("started_at"),
            ended_at=job.get("ended_at"),
            last_notified_status=job.get("status") if job.get("status") in ("Failed", "Success", "Cancelled") else (existing or {}).get("last_notified_status"),
            last_seen_at=now_iso,
        )
    return new_failures
