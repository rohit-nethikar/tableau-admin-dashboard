"""Raw HTTP client for Tableau's Metadata API (GraphQL) - TSC has no wrapper for this.

Prerequisite on self-managed Tableau Server: the Metadata API is disabled by default
and must be turned on by a server admin:
    tsm data-service enable
    tsm pending-changes apply
If it's disabled, requests here will fail (connection refused or 404) - that's
expected, not a bug in this app. See README.md.

`usage { totalViewCount }` is a lifetime total, not a windowed count - the Metadata
API doesn't expose per-day view history, so for data sources (which have no REST
usage endpoint - see tableau_client.list_workbook_view_counts's docstring) it's the
only usage signal available without direct access to Tableau's PostgreSQL
repository. health_scoring.py and orphan_detection.py treat it as "views since the
content was created," not as a recent-activity signal, and label it as such in the
UI. Workbooks don't need this query at all: their view counts come from the REST
API (tableau_client.list_workbook_view_counts), which also works while the Metadata
API is blocked, so this query only asks for workbook->datasource links, not usage.
"""
import requests

LINEAGE_QUERY = """
query WorkbookLineage {
  workbooks {
    name
    projectName
    upstreamDatasources {
      name
    }
  }
  publishedDatasources {
    name
    usage {
      totalViewCount
    }
  }
}
"""


class MetadataApiError(Exception):
    pass


def fetch_lineage_and_usage(server_url: str, auth_token: str) -> dict:
    """Returns {"links": [(workbook_name, datasource_name), ...],
    "datasource_views": {datasource_name: total_view_count}}.

    datasource_views only includes entries where the Metadata API actually returned a
    usage block - callers must treat a missing key as "unknown," not zero, since a
    server version without usage tracking enabled will omit the field entirely.
    """
    url = f"{server_url}/api/metadata/graphql"
    headers = {
        "X-Tableau-Auth": auth_token,
        "Content-Type": "application/json",
    }
    try:
        resp = requests.post(url, json={"query": LINEAGE_QUERY}, headers=headers, timeout=30)
    except requests.RequestException as exc:
        raise MetadataApiError(
            f"Could not reach Metadata API at {url}. Is it enabled? "
            f"(tsm data-service enable). Original error: {exc}"
        ) from exc

    if resp.status_code != 200:
        raise MetadataApiError(f"Metadata API returned HTTP {resp.status_code}: {resp.text[:500]}")

    payload = resp.json()
    if "errors" in payload and payload["errors"]:
        raise MetadataApiError(f"Metadata API returned errors: {payload['errors']}")

    data = payload.get("data", {}) or {}

    links = []
    for wb in data.get("workbooks", []) or []:
        wb_name = wb.get("name")
        if not wb_name:
            continue
        for ds in wb.get("upstreamDatasources", []) or []:
            ds_name = ds.get("name")
            if ds_name:
                links.append((wb_name, ds_name))

    datasource_views = {}
    for ds in data.get("publishedDatasources", []) or []:
        ds_name = ds.get("name")
        usage = ds.get("usage")
        if ds_name and usage and usage.get("totalViewCount") is not None:
            datasource_views[ds_name] = usage["totalViewCount"]

    return {
        "links": links,
        "datasource_views": datasource_views,
    }
