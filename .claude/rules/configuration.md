---
name: configuration
description: Configuration files and settings
paths:
  - config.py
  - config.yaml
  - governance.yaml
  - governance_config.py
---

## Configuration Files

**config.yaml** — User-edited settings:
- `server_url` — Tableau Server URL
- `sites` — List of sites to sync
- `default_site` — Initial site to display
- `host`, `port` — Web server binding
- `refresh_interval_minutes` — Cache refresh frequency
- `stale_threshold_days` — Staleness threshold for workbooks
- `smtp_host`, `smtp_port` — Email configuration (optional)

**governance.yaml** — Tunable weights/thresholds for scoring:
- Factor weights (staleness, refresh reliability, etc.)
- Inactive user thresholds
- Service account name patterns
- High-risk capabilities
- Per-project `approved_baseline` (if defined)

## Loading Config

From code:
```python
from config import settings
url = settings.server_url
site = settings.default_site

from governance_config import weights, config as gov_config
score = health_scoring.compute_health(workbook, weights)
```

## Modifying Config

- Edit YAML files directly (not created via code)
- Restart app to pick up changes
- No runtime reload; fully immutable after load

## Config Storage

Secrets are NOT in YAML:
- PAT token: stored in SQLite after validation (encrypted)
- Flask secret: generated once, stored in `instance/flask_secret.key`
- BigQuery credentials: external JSON file (in .gitignore)

## Validation

On app startup:
- config.yaml is validated (all required keys present, valid types)
- governance.yaml is optional; defaults are used if not present
- Invalid config prevents app start (fail-fast)

## Common Issues

- Forgetting to restart app after config changes
- Using string keys from config directly (use `settings.key` instead)
- Hardcoding values that should be in governance.yaml
