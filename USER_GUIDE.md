# Tableau Admin Dashboard — Team Guide

A quick reference for using the app day-to-day. For setup/installation, see `README.md` instead — this guide assumes it's already running and you just need a passcode.

## What this app is for

It's a governance dashboard that sits on top of your Tableau Server/Site and answers questions Tableau's own UI doesn't make easy:

- Which workbooks and data sources are stale, unowned, or have broken extract refreshes?
- Who has access to what, and does any of it look risky (e.g. conflicting Allow/Deny grants, an inactive user still holding access)?
- What's the overall health of our content, and where should we focus cleanup?
- Is our nightly extract refresh actually running, and how long does it take?

It reads from Tableau on a schedule and caches the results locally so pages load instantly. **It never changes anything in Tableau** — no permission changes, no deletions, no ownership reassignment. The only things it writes are local notes (an assigned owner, a finding's review status), and those are logged.

## Logging in

- Go to the app's URL (ask whoever set it up for the address — commonly a shared machine's hostname/IP and port, e.g. `http://<hostname>:5000`).
- Enter the shared passcode. Everyone on the team uses the same one — it's separate from any Tableau login and just locks the local UI, not a personal account.
- If you're managing multiple Tableau sites, use the site dropdown in the top-right of the nav bar to switch between them. Each site has its own cached data. Your selected site is personal to your own browser — switching it doesn't change what anyone else looking at the app sees.

## Everyday actions

| Action | Where |
|---|---|
| Force an immediate data refresh | **Refresh Now** button, top nav bar |
| Export any table to CSV | **CSV** button above that table |
| Show/hide columns in a table | **Columns** button above that table |
| Toggle dark mode | Moon/sun icon, top nav bar |
| Search/sort/paginate any table | Built into every table — click column headers to sort, use the search box to filter |
| Log out | **Logout**, top nav bar |

Data refreshes automatically in the background on a schedule (ask your admin what interval is configured — commonly hourly). You don't need to trigger it manually unless you just fixed something in Tableau and want to see it reflected immediately.

## Page-by-page

**Overview** — the landing page: total workbook/data source counts, how many are stale, average health score, open findings by severity, and a top-5 list of the most urgent findings. Start here.

**Workbooks / Data Sources** — full inventories with owner, project, staleness, extract refresh status and schedule, tags, favorites, revision count, and (for workbooks) which data source(s) they use. Data Sources also has an "Underlying Source(s)" column showing what each connection actually points at — a database/file and server, or, when it's built on top of another published data source, that data source's name. A blank "Personal Space" badge instead of a project name means that content lives in the owner's private area — it has no permissions to manage and won't show up on the Permissions page, which is expected, not a bug.

**Permissions** — every explicit permission grant on projects and workbooks, plus each project's default-permission template, with group membership expanded to individual users. The **Risk** column links to any related finding (e.g. a same-resource Allow/Deny conflict).

**Lineage** — for each workbook, which published data source(s) it draws from. Requires the Tableau Metadata API to be enabled on your server; if it's not, this page (and the "Data Source(s)" column elsewhere) will be blank.

**Custom Views** — saved per-user views: which workbook/view they belong to, owner, and whether they're shared or private.

**Subscriptions** — who receives emailed snapshots of a workbook or view, on what schedule, and whether it's currently suspended.

**Connected Apps** — OAuth/JWT app registrations used for embedding. Requires an admin-level PAT and a recent-enough Tableau Server version; if either is missing this section just won't populate (see Refresh Health for the specific error).

**Data Alerts** — data-driven alert subscriptions: subject, creator, owner, frequency, and target view/workbook. Tableau's API doesn't expose the actual trigger threshold, so that's not shown.

**Webhooks** — site-level webhooks (name, target URL, triggering event, owner).

**Site Settings** — a snapshot of site-wide config: storage used/quota, extract encryption mode, guest access, revision history limit, Ask Data mode, and license tier capacity vs. actual usage. Also shows the Tableau Server's product version, build number, and REST API version — the same for every site since they're all on the same physical server.

**Users** — the full user roster for the current site: name, email, site role, last login, and an **Inactive?** flag for anyone who has never logged in or hasn't logged in for 90+ days (same threshold as the "Stale" flag elsewhere, just applied to login recency). A banner at the top summarizes how many users are inactive.

**Health** — a 0–100 score per workbook/data source built from usage, ownership, refresh status, certification, documentation, permission risk, and lineage presence. Click **Factors** on any row to see exactly which signals counted and which were skipped (a skipped signal's weight is redistributed, never scored as zero). You can also record an admin-assigned owner here — this is a local note only and doesn't touch Tableau.

**Findings** — the actual to-do list: every detected issue (orphaned content, permission risk, staleness, refresh failures, data quality warnings) with severity, evidence, and a recommended action. Filter by severity, category, project, owner, or status. Mark a finding **Acknowledged**, **Resolved**, or **Dismissed** as you work through it — that status sticks across future refreshes unless the underlying problem goes away on its own, in which case the app auto-resolves it. Every status change is logged. Export the current filtered view as CSV to share or track offline.

**Refresh Health** — is the app itself keeping up? Last successful sync, consecutive sync failures, next scheduled sync, and a trend chart of how long syncs have been taking. Also shows Tableau's own most-recent extract-refresh timestamp, and a recent sync-run log with redacted failure details. Use **Validate PAT access to all sites** here if something looks stale and you suspect the service account's token needs attention.

## A few things that look like bugs but aren't

- **Favorites column shows "n/a"** on some Tableau Server versions — Tableau's REST API doesn't return that field on this kind of deployment. Not fixable from our side.
- **"Extract Failures" (on Workbooks/Data Sources) vs. "Consecutive Sync Failures" (on Refresh Health)** are two different things: the first is Tableau's own extract-refresh job failures for that specific item; the second is how many times *this app's* own background sync has failed in a row. Same-sounding names, different meaning.
- **A blank "Next Scheduled Refresh"** just means that content has no server-managed refresh schedule (e.g. it's live-connection-only, or only ever refreshed manually) — it doesn't mean anything is broken.
- **Usage counts are lifetime totals**, not "views in the last 30 days" — Tableau doesn't expose a windowed count via the APIs this app uses.

## Who to ask

For access issues (passcode, which site to pick), config changes (refresh interval, alert emails, governance thresholds), or anything that looks like a real bug rather than one of the items above, contact whoever administers this app for your team.
