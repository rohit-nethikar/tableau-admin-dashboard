# Tableau Admin Dashboard - Platform-Neutral Deployment Guide

## Goal

This package prepares the existing Flask application to run on an approved internal
Windows/Linux VM or a container platform without tying it to one cloud provider.

The first hosted version should run as **one application instance**.

Why: the application currently uses a local SQLite database and APScheduler inside
the web process. Multiple replicas can create separate SQLite state and duplicate
scheduled refreshes.

## Target architecture

    Internal browser
          |
          v
    Approved internal HTTPS endpoint / reverse proxy
          |
          v
    ONE Flask + Waitress application instance
          |
          +---- persistent application data
          |       cache.db
          |       generated secret/backup files
          |
          +---- Tableau APIs
          |
          +---- BigQuery

TLS/HTTPS should normally terminate at the approved internal reverse proxy or
platform ingress rather than inside Waitress.

## Files added by the patch

- `Dockerfile`
- `.dockerignore`
- `.env.example`
- `startup.ps1`
- `startup.sh`
- `validate-deployment.ps1`
- this `DEPLOYMENT.md`

The patch also updates `config.py` to support environment-variable overrides and
adds a lightweight deployment health route to `app.py` only when `/health` is not
already registered.

## Important security rule

Do not bake BigQuery credential JSON, Flask secret keys, `.env`, SQLite databases,
logs, or the `instance` directory into an image or source-control commit.

Prefer the hosting platform's workload/application identity for BigQuery. If your
approved platform requires a service-account file, mount it at runtime and set
`GOOGLE_APPLICATION_CREDENTIALS` to the mounted path.

## Environment variables

Required/recommended production values:

- `APP_HOST=0.0.0.0`
- `APP_PORT=5000` (or the port supplied by the hosting platform)
- `APP_DATA_DIR=<persistent writable path>`
- `FLASK_SECRET_KEY=<secret-store value>`

Optional overrides:

- `TABLEAU_SERVER_URL`
- `TABLEAU_SITES` - comma-separated site names
- `TABLEAU_DEFAULT_SITE`
- `REFRESH_INTERVAL_MINUTES`
- `SITE_SWITCH_STALENESS_MINUTES`
- `STALE_THRESHOLD_DAYS`
- `SMTP_HOST`
- `SMTP_PORT`
- `ALERT_EMAIL_FROM`
- `ALERT_EMAIL_TO`
- `GOOGLE_APPLICATION_CREDENTIALS`

If an optional override is absent, the existing `config.yaml` value remains active.

## Persistent storage

`APP_DATA_DIR` must survive application restarts if you need to preserve SQLite
cache/state and application-generated secret material.

For a VM, this can be a protected directory on a persistent disk.

For a container platform, mount a persistent volume at `/app/data` and set:

    APP_DATA_DIR=/app/data

Do not scale beyond one replica while SQLite and the in-process scheduler remain
part of the web process.

## Local validation

After applying the patch:

    .\validate-deployment.ps1

Then run:

    .\startup.ps1

Open:

    http://127.0.0.1:5000/health

Expected lightweight response:

    {"status":"ok"}

## Docker validation

Build:

    docker build -t tableau-admin-dashboard:local .

Run using local persistent storage:

PowerShell:

    docker run --rm -p 5000:5000 `
      -e APP_HOST=0.0.0.0 `
      -e APP_PORT=5000 `
      -e APP_DATA_DIR=/app/data `
      -e FLASK_SECRET_KEY="<temporary-local-test-secret>" `
      -v "${PWD}\docker-data:/app/data" `
      tableau-admin-dashboard:local

Do not pass real credentials on a shared command line. Use your approved secret
injection method for the real deployment.

Test:

    http://127.0.0.1:5000/health

## Production readiness checklist

1. Use one app instance.
2. Give the app persistent writable storage.
3. Inject `FLASK_SECRET_KEY` from a secret store.
4. Use approved BigQuery authentication.
5. Keep credential files and databases out of Git and images.
6. Put the app behind the approved internal HTTPS endpoint/reverse proxy.
7. Restrict network access to the intended internal audience.
8. Configure platform health probing against `/healthz`.
9. Confirm outbound connectivity to Tableau and BigQuery.
10. Confirm the scheduler runs only once.
11. Back up or otherwise protect application state if the SQLite data is important.
12. Keep stdout/stderr logs in the platform logging system.

## Scaling later

Before increasing replicas above one:

- move SQLite to a shared managed database,
- separate scheduled/background jobs from the web process,
- ensure account-number sync has cross-process locking/idempotency,
- then allow the web tier to scale horizontally.

## Rollback

The patch script creates `.deployment-backups/<timestamp>/` before changing source
files.

To restore the most recent pre-patch state:

    .\deployment-readiness-patch.ps1 -Rollback

Stop the application before rollback, then restart it after the restore completes.

