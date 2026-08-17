# Tableau Admin Dashboard

<img src="static/img/mayo-clinic-logo.png" alt="Mayo Clinic" height="80"> <img src="static/img/tableau-logo.png" alt="Tableau" height="48">

**Developed by:** Rohit Nethikar &middot; **Organization:** Mayo Clinic

Local single-admin web app for Tableau Server governance: content health scoring,
a findings/remediation queue, orphaned-content and permission-risk detection, refresh
reliability tracking, a permissions audit view, and a data-source/workbook lineage
view. Backed by a scheduled SQLite cache so pages load fast.

**Nothing is ever auto-remediated.** This app never deletes content, changes
permissions, downgrades licenses, or reassigns ownership on its own. It only
computes scores and findings and presents them for human review; the only writes it
makes to Tableau-adjacent state are local (owner overrides, finding status), and
every one of those is recorded in the audit log (queryable via `db.fetch_audit_log`
directly against `instance/cache.db` for now — no UI for it yet).

## Latest Updates — August 2026

✅ **Comprehensive Test Suite**
- 67 passing tests across 4 critical modules
- Email alerting, deduplication, BigQuery sync, account sync covered
- All tests pass in 3.52s
- See [Project Status](../sql-optimizer-bq/docs/00-PROJECT-STATUS.md) for full details

📊 **Upcoming Features**
- Slack integration (Week 1)
- License forecasting (Week 1-2)
- Extract refresh health monitoring (Week 3-5)
- Cluster health & capacity planning (Q2)

📚 **Documentation**
- [Project Status Overview](../sql-optimizer-bq/docs/00-PROJECT-STATUS.md) — Current state & roadmap
- [Implementation Guide](../sql-optimizer-bq/docs/OPTION_D_PROJECT_IMPLEMENTATION_GUIDES.md) — Week-by-week plans
- [Comprehensive Assessment](../sql-optimizer-bq/docs/COMPREHENSIVE_PROJECT_ASSESSMENT.md) — All findings

## Prerequisites

1. Python 3.10+.
2. A Tableau Server Personal Access Token (Server → your account menu → My Account Settings → Personal Access Tokens).
3. **For the Lineage view only:** the Metadata API must be enabled on your Tableau Server
   (it's off by default on self-managed Server). As a server admin, run:
   ```
   tsm data-service enable
   tsm pending-changes apply
   ```
   The Workbooks and Permissions views work without this.

## Setup

```
cd tableau-admin-dashboard
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Edit `config.yaml` and set `server_url` (and `site_name` if you're not using the Default site):

```yaml
server_url: "https://your-tableau-server.example.com"
site_name: ""
refresh_interval_minutes: 60
stale_threshold_days: 90
```

Also review `governance.yaml` — it holds the tunable weights/thresholds for health
scoring and permission-risk detection (factor weights, inactive-user-days threshold,
service-account name patterns, high-risk capabilities, and an optional per-project
`approved_baseline` for permission grants). Defaults are reasonable but were not
tuned against your server; edit and restart, same workflow as `config.yaml`.

Run it:

```
python app.py
```

This serves the app with [Waitress](https://docs.pylonsproject.org/projects/waitress/)
(a real, multi-threaded WSGI server, not Flask's single-threaded dev server) on
whatever `host`/`port` are set in `config.yaml` — defaults to `0.0.0.0:5000`, i.e.
reachable from other machines on your network, not just this one. Open
`http://<this-machine's-address>:5000` — you'll be redirected to `/setup` the first
time. Enter your PAT name/secret and choose a passcode (this passcode just locks the
local UI, and is shared by everyone who uses the app — it's separate from the Tableau
PAT). The app validates the PAT against your server before saving anything.

After setup, log in with the shared passcode. A cache refresh of every configured
site kicks off in the background immediately, then repeats every
`refresh_interval_minutes`. Use the **Refresh Now** button in the nav bar to force a
refresh of whichever site you're currently viewing, or **Refresh all sites** on
Refresh Health to force all of them.

### Making this available to your team

- Share the URL (`http://<host-machine-address>:5000`) and the passcode you set
  during setup. Anyone with both can use the app — there are no separate per-person
  accounts, by design (see Security notes).
- Each browser/tab has its **own** selected site (stored in that browser's session,
  not shared) — one person switching sites doesn't change what anyone else is
  looking at. The background refresh keeps every configured site's cache warm
  regardless of who's looking at what.
- If teammates can't reach the URL, check: (1) Windows Firewall — you may need an
  inbound rule allowing TCP on the configured port; (2) that `host` in `config.yaml`
  is actually `0.0.0.0` (not `127.0.0.1`, which only accepts local connections) and
  the app was restarted after changing it; (3) that they're on the same network/VPN
  as the host machine.
- To restrict access instead (e.g. only your own machine), set `host: "127.0.0.1"`
  in `config.yaml` and restart.

## What each view shows, and known limitations

- **Workbooks** — inventory with owner, project, and a staleness flag. The "stale"
  signal is based on the workbook's **last-updated (content modified)** date, not true
  view counts — the Tableau REST/Metadata APIs don't expose per-workbook last-viewed
  timestamps; that data only lives in the Postgres workgroup repository. If you have
  read-only access to that repository and want true view-based staleness, ask and it's
  a straightforward addition (there's a `repository.py` extension point noted in
  `sync_service.py`). A workbook with no project shown (tagged **Personal Space**) lives
  in that owner's private Tableau Personal Space rather than a shared project. The
  site-admin PAT this app requires can see and inventory these (Tableau surfaces
  Personal Space content to site/server admins), but it can't read or show permissions
  on them — Personal Space content has no permissions to grant, by Tableau's design —
  so they never appear on the Permissions page and are excluded from permission-risk
  findings. The same badge appears on the Findings and Health pages for workbook rows.
- **Extract refresh status** comes from the REST API Jobs endpoint, matched back to
  workbooks/data sources by ID. **Extract Run Duration** is how long the most recent
  extract-refresh job took to run (completed-at minus started-at, from that same Jobs
  detail call) &mdash; blank if that job never completed or Tableau didn't report a
  start time (e.g. a cancelled-before-starting job). **Next Scheduled Refresh** is a separate signal from the
  Tasks endpoint (`server.tasks` in `tableauserverclient`) showing when the *next* extract
  refresh is due to run, alongside the schedule's name and frequency (Hourly/Daily/Weekly/
  Monthly). It's blank for a resource with no server-managed schedule (e.g. all-live-connection
  content, or something only ever refreshed on demand via `tabcmd`/API) &mdash; a blank cell
  does not mean anything is broken.
- **Data Sources** — the published-datasource counterpart to Workbooks: owner,
  project, certification, description, staleness, extract status, and lifetime view
  count. "Underlying Source(s)" adds per-connection detail on top of the coarse
  Connection Type (Live/Extract/Mixed) summary &mdash; what database/file driver and
  server each connection actually points at, or, when a connection is itself built on
  top of another published data source, that chained data source's name. This comes
  from the same `populate_connections` REST call `enrich_datasources` already makes;
  no extra call is needed. Data sources with an active Data Quality Warning (sensitive data, stale,
  deprecated, etc.) surface that warning as a Findings entry under the
  `data_quality_warning` category, severity-mapped via `dqw_severity_map` in
  `governance.yaml`; DQWs are a datasource-only Tableau feature (not available on
  workbooks in the REST API), so workbook visibility into a warning stays indirect
  via the existing data-source lineage join.
- Both **Workbooks** and **Data Sources** also show **Tags** (as set in Tableau) and
  **Favorites** (how many users have favorited that item). Favorites has no
  dedicated site-wide REST endpoint in Tableau — `tableauserverclient`'s
  `Favorites.get()` is scoped per-user — so this app reads the `favoritesTotal`
  field directly off the raw list-endpoint JSON response instead (the same
  "raw REST call" pattern used for Connected Apps and Custom Views usage stats).
  In practice, `favoritesTotal` was not present at all in the workbook/datasource
  list response on the real Tableau Server this app was verified against (REST API
  3.21) despite being read this way in code, so the Favorites column shows **n/a**
  rather than a count on that kind of deployment — the column only populates on a
  Tableau Server/Cloud version that actually returns the field.
- **Permissions** — explicit grants on projects/workbooks plus each project's
  default-permission templates, with group membership flattened to individual users
  in a separate table below. This mirrors Tableau's real permission model rather than
  simulating dynamic inheritance across locked/unlocked nested projects. The **Risk**
  column links into Findings filtered to `permission_risk` — see below for what it
  flags.
- **Lineage** — workbook → upstream published data source, from the Metadata API.
- **Custom Views** — Tableau's saved-view-per-user feature: name, owning workbook/
  view, owner, shared/private, created/updated dates. A non-admin PAT may only see
  custom views it owns or that are marked shared — a Tableau Server-side
  restriction, not something this app controls.
- **Subscriptions** — who's receiving emailed snapshots of a workbook or view, on
  what schedule, and whether the subscription is currently suspended.
- **Connected Apps** — Tableau Server's OAuth/JWT direct-trust configuration, used to let
  embedded dashboards or external applications call the REST API on a user's behalf without
  a login prompt: name, client ID, enabled/disabled, which projects it's scoped to embed
  content from (or "All Projects" if unrestricted), domain restriction, and unrestricted-
  embedding flag. This requires the configured PAT to belong to a server or site admin, and
  Tableau Server 2022.3+ (REST API 3.17+) — `tableauserverclient` (as of 0.32) has no wrapper
  for this endpoint at all, so `tableau_client.list_connected_apps` makes a raw REST/JSON call
  instead (the same pattern already used for Custom Views' usage-statistics lookup). On an
  older server or a non-admin PAT, this section fails independently and shows as a sync error
  on Refresh Health rather than populating or crashing the rest of the sync.
- **Health** — a 0-100 score per workbook/data source from seven weighted signals:
  usage (lifetime view count), ownership, refresh status, certification (data sources
  only — Tableau workbooks can't be certified), documentation (non-empty description),
  permission risk, and lineage presence. A signal that isn't available for a given
  asset (e.g. certification on a workbook, or usage/lineage while the Metadata API is
  unreachable) is excluded and its weight redistributed across the signals that are
  available — it is **never** silently scored as zero. Click "Factors" on any row for
  the full breakdown, including exactly which signals were skipped and why. Tableau
  has no native "designated owner" concept beyond whoever created the content, so this
  page also lets you record an admin-assigned business/technical owner per asset —
  purely local bookkeeping that feeds orphaned-content detection and never touches
  Tableau itself.
- **Findings** — a queue of detected issues (orphaned content, permission risk, stale
  content, refresh failures) with severity, evidence, and a recommended action.
  Findings are recomputed on every sync, but a human-set status (acknowledged /
  resolved / dismissed) is preserved across resyncs; the system only auto-resolves a
  finding if the underlying condition disappears on its own. Every status change is
  written to the audit log. Filter by severity/category/project/owner/status, or
  export the current filtered view as CSV.
- **Refresh Health** — reliability stats computed from the existing sync run history:
  last successful refresh, consecutive sync failures, a line chart of sync duration
  across recent runs, and next scheduled run. Failure details shown here are redacted
  (raw text is kept in the database for admin debugging).
- **Data-Driven Alerts** — subject, creator, owner, frequency, public/private, and
  the target view/workbook/project, plus recipients. Tableau's REST API does not
  expose the alert's actual threshold condition (the value/comparison that
  triggers it) — only the metadata shown here.
- **Webhooks** — site-level webhooks: name, target URL, triggering event, and
  owner. Tableau's REST API has no enabled/disabled flag for webhooks at all, so
  that column doesn't exist here (not an oversight).
- **Site Settings** — a snapshot of site-wide configuration: storage used/quota,
  extract encryption mode, guest access, subscriptions, revision history and its
  limit, Ask Data mode, and a table comparing each license tier's configured
  capacity (Creator/Explorer/Viewer) against actual current user counts by role.
  It also shows the physical Tableau Server's product version, build number, and
  REST API version — a `server_info` card that's identical no matter which
  configured site you're currently viewing, since all your sites live on the same
  server.
- **Users** — the full user roster for the current site (name, email, site role,
  last login), with an "Inactive?" flag for anyone who has never logged in or
  hasn't logged in within the last `stale_threshold_days` (config.yaml, defaults
  to 90) days — the same threshold already used for the "Stale" flag on Workbooks/
  Data Sources, just applied to login recency instead of content freshness. This
  only reflects login activity; Tableau's REST API doesn't expose a separate
  "last active"/in-app-usage signal beyond last login.

### Known limitations of the new signals

- **Usage is lifetime-only.** The Metadata API exposes a lifetime total view count,
  not a windowed/recent-activity signal — there's no "views in the last 30 days"
  without diffing daily snapshots over time, which this app doesn't do yet. Treat the
  usage factor as a coarse "has this ever been used at all" signal.
- **Permission conflict detection is intentionally conservative.** It flags a same-
  resource Allow-vs-Deny disagreement between different grantees for human review —
  it does not attempt to compute Tableau's actual effective-permission precedence,
  which depends on group membership and role in ways too complex to fully replicate
  here.
- **"Inactive" and "service account" are heuristics**, configurable in
  `governance.yaml` (`inactive_user_days`, `service_account_patterns`) — tune them to
  match your organization's actual account-naming and offboarding conventions.
- **Revision counts are capped by server retention, not unlimited history.** Both
  workbook and data source "Revisions" reflect however many revisions the server's
  configured revision-retention setting currently keeps, not a true full history.
- **Consecutive extract-failure counts are capped by job retention.** Each resource's
  "Extract Failures" is computed by counting back from the most recent extract-refresh
  job until a non-failure, bounded by however much job history Tableau Server
  currently retains — the same caveat that already applies to Refresh Health's
  "Consecutive Sync Failures" (a distinct metric: this app's own sync runs, not
  Tableau's extract jobs).
- **Connection Type (Live/Extract/Mixed) reflects the driver of each connection**,
  not a single resource-level flag. TSC exposes a connection's underlying DB driver
  name (e.g. "postgres", "hyper") rather than a literal live/extract label; "hyper"
  is treated as the extract connection, everything else as live. "Mixed" means the
  workbook/data source has both.
- **The "Data Source(s)" column on Workbooks depends on the Metadata API**, same as
  the Lineage page — it will be blank while that API is unreachable (see the
  Metadata API note in Prerequisites).
- **Extract status/last-run/duration/notes are resolved from only the most recent 150
  extract-refresh jobs.** The Jobs list endpoint doesn't include which workbook/data
  source a job belongs to or its notes — resolving that takes one extra REST call per
  job (`server.jobs.get_by_id`). To keep sync time bounded as job history grows,
  `tableau_client.list_extract_refresh_status` only resolves the 150 most-recently-
  created extract/refresh jobs (`EXTRACT_JOB_DETAIL_LOOKUP_LIMIT`); a resource whose
  last refresh attempt falls outside that window will show no extract status until it
  runs again.
- **The Refresh Health trend chart is site-wide sync duration, not per-resource
  extract duration.** No time-series of past per-resource extract durations is
  stored anywhere — the Workbooks/Data Sources tables only ever hold the latest
  known run, overwritten each sync. The chart instead plots this app's own
  end-to-end sync duration across recent runs, which is the one place real
  historical timing data already exists.
- **Data Quality Warnings, Data-Driven Alerts, and Webhooks all reflect Tableau
  REST API limitations, not gaps in this app**: DQWs only exist on
  datasources/databases/tables/flows in `tableauserverclient` 0.32 (not
  workbooks); alerts never expose their threshold condition; webhooks have no
  enabled/disabled flag anywhere in the API.

### Extract-failure email alerts

If a workbook or data source's extract-refresh job newly fails, or an existing
failure's consecutive-failure count climbs, `sync_service.py` emails a summary
(status, last run time, consecutive-failure count, Tableau's job notes if any, and a
link to the asset) via `email_notifier.py`. It deliberately does **not** re-send
every sync cycle for an already-known, unchanged failure — only on a fresh failure
or a worsening one — so a long-standing broken extract doesn't spam the inbox.

Configure it in `config.yaml`:
```yaml
smtp_host: "smtprelay.mayo.edu"
smtp_port: 25
alert_email_from: "you@mayo.edu"
alert_email_to: "you@mayo.edu"
```
Leave `smtp_host` blank/absent to disable alerting entirely — nothing else in the
sync depends on it. This assumes an internal relay that accepts anonymous mail from
this app's host (no username/password); if your relay requires auth, `email_notifier.py`
will need a small update to call `smtplib.SMTP.login(...)` before sending. A failed
send is recorded as a sync error (visible on Refresh Health) but never fails the
whole sync or drops cached data. A successful send is recorded in the audit log.

## Interface notes

- **Dark mode** — toggle button in the nav bar; the choice persists in
  `localStorage` per browser (not per-user server-side) and is applied before
  first paint to avoid a flash of the wrong theme.
- **Every table** has a CSV export button and a column-visibility toggle
  (top-left above each table), plus a sticky header while scrolling — a shared
  config in `static/js/datatables-common.js` used by every page, not a
  one-off on Findings.
- **Refresh Now** and finding status updates run over `fetch()` in the
  background and confirm via a toast notification (bottom-right) instead of a
  full page reload — the underlying data updates on your next normal page
  load/navigation, or automatically once a still-running "Refresh Now" you
  triggered finishes (you'll get a second toast when it does; the page itself
  won't auto-reload out from under you).
- Below the desktop breakpoint, the nav collapses behind a hamburger toggle
  (standard Bootstrap `navbar-collapse`).

## Known rough edges to expect on first real run

Tableau's REST API/`tableauserverclient` object field names (particularly on Jobs and
Permissions objects) can vary slightly by Tableau Server version. `tableau_client.py`
extracts these defensively (falls back gracefully rather than crashing the whole
sync), and each data section fails independently — one broken section won't take down
the rest. If a section comes up empty and shouldn't, check the status line at the top
of any page (last refresh status/detail) for the specific error, which will point at
exactly what needs adjusting.

## Security notes

- The PAT is encrypted at rest (Fernet) using a key in `instance/secret.key`.
- The passcode is stored as a hash (`werkzeug.security.generate_password_hash`), never plaintext.
- `instance/` (DB, keys) is gitignored — don't commit it.
- **There's one shared passcode, not per-person accounts.** Anyone who has it can see
  everything the app can see and make the same local-only writes (owner overrides,
  finding status) — those are attributed to "system" in the audit log, not to an
  individual, since the app has no concept of who's currently logged in beyond
  "someone with the passcode." That's an intentional simplification for a small
  trusted team; if you need per-person accountability, that would require adding
  real user accounts, which this app does not have today.
- **No built-in HTTPS.** Traffic (including the passcode and PAT-derived session
  data) is unencrypted between browser and server. `host: "0.0.0.0"` in
  `config.yaml` makes the app reachable from your network, which is fine on a
  trusted internal subnet/VLAN, but if it needs to be reachable more broadly than
  that, put a reverse proxy (IIS, nginx, Caddy) with TLS in front of it rather than
  exposing it directly.
