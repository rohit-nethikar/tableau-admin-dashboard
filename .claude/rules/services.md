---
name: services
description: Business logic services layer
paths:
  - tableau_client.py
  - email_service.py
  - caching_service.py
  - sync_service.py
  - export_service.py
  - health_scoring.py
  - permission_risk.py
  - orphan_detection.py
  - findings_engine.py
  - alerts_engine.py
  - bigquery_sync.py
---

## Service Layer Architecture

Services are stateless functions that handle business logic:
- **tableau_client.py** — Wraps Tableau Server Client (TSC); authenticates and queries Tableau API
- **email_service.py** — Sends emails via SMTP; handles templates and alerts
- **caching_service.py** — Populates SQLite cache from Tableau; runs on schedule
- **sync_service.py** — Master sync orchestrator; runs all cache-population jobs
- **export_service.py** — Exports findings/data to CSV or reports
- **health_scoring.py** — Computes workbook/datasource health scores
- **permission_risk.py** — Risk assessment for permissions (high-risk capabilities)
- **orphan_detection.py** — Identifies orphaned/unused content
- **findings_engine.py** — Generates findings (issues to remediate)
- **alerts_engine.py** — Processes alerts for data quality issues
- **bigquery_sync.py** — Syncs cache data to BigQuery (optional)

## Calling Services

From routes or scheduler:
```python
from email_service import send_alert_email
send_alert_email(email_to, subject, body)
```

Services are pure functions; initialize clients at module load, call functions.

## Configuration Access

Services access config via:
```python
from config import settings
url = settings.server_url
```

And governance weights via:
```python
from governance_config import weights
factor = weights["workbook_staleness"]
```

## Database Access in Services

Services call `db.fetch_*()` or `db.update_*()` directly:
```python
from db import fetch_workbooks, fetch_findings
workbooks = fetch_workbooks(site_name)
findings = fetch_findings(site_name, status="open")
```

## Error Handling

Services should:
- Log errors with context
- Raise exceptions (let caller decide to catch/recover)
- Not silently fail on API/database errors
- Return None or empty list on expected failures (missing data)

## Testing Services

If tests are added, services should be testable independently:
- Mock Tableau client / database access
- Pass dependencies as parameters if possible
- Use `conftest.py` fixtures for setup

## Common Issues

- Calling sync_service from routes (no; use scheduler.py instead)
- Forgetting to initialize Tableau client with proper auth
- Not handling rate limits on API calls
- Assuming fresh data without checking cache timestamp
