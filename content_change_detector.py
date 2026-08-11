"""Diffs each sync's freshly-fetched projects/workbooks/datasources/schedules
against what was cached before this sync overwrites it, logging every add,
removal, and tracked-field change to content_change_log + the shared audit_log.
Mirrors config_audit.py's diff-before-overwrite pattern, generalized from
scalar site-settings fields to whole entities with add/remove semantics."""
import db
import audit

_WORKBOOK_FIELDS = ["name", "project_name", "owner_name", "sheet_count"]
_DATASOURCE_FIELDS = ["name", "project_name", "owner_name", "is_certified"]
_PROJECT_FIELDS = ["name", "parent_id"]


def diff_entities(site, entity_type, previous_rows, new_rows, now_iso, tracked_fields):
    """Detect added/removed/modified entities. Returns list of change dicts."""
    if not previous_rows:
        return []
    previous_by_id = {r["id"]: r for r in previous_rows}
    new_by_id = {r["id"]: r for r in new_rows}
    changes = []

    for id_, row in new_by_id.items():
        if id_ not in previous_by_id:
            changes.append(_log(site, entity_type, id_, row.get("name"), "added", now_iso,
                                 f"New {entity_type} detected"))
    for id_, row in previous_by_id.items():
        if id_ not in new_by_id:
            changes.append(_log(site, entity_type, id_, row.get("name"), "removed", now_iso,
                                 f"{entity_type.title()} no longer found on server"))
    for id_, new_row in new_by_id.items():
        old_row = previous_by_id.get(id_)
        if not old_row:
            continue
        diffs = [f"{f}: {old_row.get(f)!r} -> {new_row.get(f)!r}"
                 for f in tracked_fields if old_row.get(f) != new_row.get(f)]
        if diffs:
            changes.append(_log(site, entity_type, id_, new_row.get("name"), "modified", now_iso,
                                 "; ".join(diffs)))
    return changes


def diff_schedules(site, previous_rows, new_rows, now_iso, resource_type):
    """Detect schedule add/remove/modify. Only evaluates resources present in both
    snapshots - a schedule on a brand-new/just-removed resource is noise already
    covered by the resource's own added/removed entry."""
    if not previous_rows:
        return []
    previous_by_id = {r["id"]: r for r in previous_rows}
    changes = []
    for id_, new_row in {r["id"]: r for r in new_rows}.items():
        old_row = previous_by_id.get(id_)
        if not old_row:
            continue
        old_sched = old_row.get("refresh_schedule_name")
        new_sched = new_row.get("refresh_schedule_name")
        if (old_sched == new_sched and
            old_row.get("refresh_frequency") == new_row.get("refresh_frequency") and
            old_row.get("refresh_next_run_at") == new_row.get("refresh_next_run_at")):
            continue
        if not old_sched and new_sched:
            change_type, details = "added", f"Schedule '{new_sched}' ({new_row.get('refresh_frequency')}) added"
        elif old_sched and not new_sched:
            change_type, details = "removed", f"Schedule '{old_sched}' removed"
        else:
            change_type, details = "modified", (
                f"schedule_name: {old_sched!r} -> {new_sched!r}; "
                f"frequency: {old_row.get('refresh_frequency')!r} -> {new_row.get('refresh_frequency')!r}; "
                f"next_run_at: {old_row.get('refresh_next_run_at')!r} -> {new_row.get('refresh_next_run_at')!r}"
            )
        changes.append(_log(site, "schedule", id_, new_row.get("name"), change_type, now_iso,
                             f"[{resource_type}] {details}"))
    return changes


def _log(site, entity_type, entity_id, entity_name, change_type, now_iso, details):
    db.add_content_change(site, now_iso, entity_type, entity_id, entity_name, change_type, details)
    audit.log_action("system", f"content_{change_type}", resource_type=entity_type, resource_id=entity_id,
                      details=f"{entity_type} '{entity_name}' {change_type}: {details}")
    return {"entity_type": entity_type, "entity_name": entity_name, "change_type": change_type, "details": details}
