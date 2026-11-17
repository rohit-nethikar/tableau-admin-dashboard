# Adoption Guide: Running the Tableau Admin Dashboard at Your Organization

This guide is for Tableau Server administrators who want to run their own copy of this
dashboard and build on it. Everything that is specific to one organization lives in
`config.yaml`, so you don't have to change any code to get started.

**Repository:** https://github.com/rohit-nethikar/tableau-admin-dashboard (branch `master`)

**What you get:** content health scoring, a findings and remediation queue,
orphaned-content and permission-risk detection, refresh reliability, license seat
usage, custom-view tracking, workbook compare, lineage, and more. It runs on a local
SQLite cache that syncs on a schedule.

**Safety:** the app never deletes content, changes permissions, downgrades licenses,
or reassigns ownership in Tableau. It only reports. Its only writes are local (finding
status, owner overrides), and each one is recorded in an audit log.

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Python 3.10+ | The Docker image uses 3.11 |
| Git | To clone the repo |
| Tableau Server (or Tableau Cloud) | You need site or server admin rights on every site you monitor |
| Personal Access Token (PAT) | Created in Step 3 |
| SMTP relay *(optional)* | For failure and license alert emails |
| `tsm` access *(optional)* | Only needed for the Lineage view (Metadata API) |
| Google BigQuery *(optional)* | Only for the account-number sync on Custom Views |

---

## Step 1: Get the code

The recommended way is to fork the repo on GitHub, so you can commit your own changes
and still pull updates from upstream:

```
git clone https://github.com/<your-github-user>/tableau-admin-dashboard.git
cd tableau-admin-dashboard
git remote add upstream https://github.com/rohit-nethikar/tableau-admin-dashboard.git
```

Or clone it directly:

```
git clone https://github.com/rohit-nethikar/tableau-admin-dashboard.git
cd tableau-admin-dashboard
```

## Step 2: Install

**Windows**
```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

**Mac / Linux**
```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Step 3: Create a Tableau Personal Access Token

1. Sign in to Tableau Server with an admin account.
2. Click your profile icon and choose **My Account Settings**, then go to **Personal Access Tokens**.
3. Enter a token name (for example `admin-dashboard`) and click **Create Token**.
4. Copy both the **token name** and the **token secret**. The secret is shown only once.

The account must be able to see every site you list in Step 4. Don't put the token in
any file: the app asks for it in Step 8 and stores it encrypted.

## Step 4: Create `config.yaml`

```
copy config.example.yaml config.yaml      (Windows)
cp config.example.yaml config.yaml        (Mac/Linux)
```

Open `config.yaml` and fill in your values. Git ignores this file, so your server
names and email addresses never get committed.

| Setting | What to put | Example |
|---|---|---|
| `server_url` | Base URL of your Tableau Server, with no path and no trailing slash | `https://tableau.yourorg.com` |
| `sites` | Each site's content URL: the part after `/#/site/` in the browser address. Use `""` for the Default site. | `["Finance", "Analytics-DEV"]` |
| `default_site` | One of the sites above; used to validate setup | `"Finance"` |
| `host` | `127.0.0.1` if only you will use it; `0.0.0.0` if teammates will connect over a trusted network | `127.0.0.1` |
| `port` | Port the app listens on | `5000` |
| `refresh_interval_minutes` | How often every site re-syncs | `60` |
| `stale_threshold_days` | Days unused before content is flagged as stale | `90` |
| `smtp_host` / `smtp_port` | Your mail relay. Leave `smtp_host` blank to turn off email alerts. | `smtp.yourorg.com` / `25` |
| `alert_email_from` / `alert_email_to` | Sender and recipient for alerts | `tableau-admins@yourorg.com` |
| `license_alert_threshold_pct` | Alert when a seat tier passes this % of capacity | `90` |
| `org_name` | Your organization's name, used in labels such as "YourOrg only" | `"Contoso"` |
| `org_logo` | A logo filename in `static/img/`; blank means no logo | `"contoso-logo.png"` |
| `internal_email_domain` | Email domain of your own staff. Turns on the Internal/External filter on Custom Views. | `"contoso.com"` |
| `bigquery.*` | Optional; see Step 6 | `enabled: false` |

Environment variables override these settings, which is handy for Docker:
`TABLEAU_SERVER_URL`, `TABLEAU_SITES` (comma-separated), `TABLEAU_DEFAULT_SITE`,
`APP_HOST`, `APP_PORT`, `APP_DATA_DIR` (where the cache database and keys are
stored), and `APP_CONFIG_PATH` (which config file to load).

## Step 5: Tune `governance.yaml` to your policies

Every field is optional. Anything you leave out falls back to the built-in defaults.

| Setting | Default | What it controls |
|---|---|---|
| `weights` | usage 0.20, ownership 0.15, refresh_status 0.20, certification 0.10, documentation 0.10, permission_risk 0.15, lineage 0.10 | Health-score weighting (normalized automatically) |
| `inactive_user_days` | `180` | Days without login before an owner counts as inactive (used for orphaned content) |
| `all_users_group_name` | `"All Users"` | Name of your server's built-in "everyone" group |
| `high_risk_capabilities` | Download, ExportData, ExportXml, Delete, ChangePermissions, ChangeHierarchy | Capabilities flagged when granted broadly |
| service-account patterns, `approved_baseline` | see the file | Accounts and grants that should not raise findings |

## Step 6 (optional): BigQuery account-number sync

This fills the **Account #** column on Custom Views from a BigQuery table or view that
maps user emails to account numbers. Most organizations can skip it: leave
`bigquery.enabled: false`, and the sync button is hidden and nothing tries to connect.

To turn it on:

```yaml
bigquery:
  enabled: true
  project: "your-gcp-project"
  dataset: "your_dataset"
  view: "YOUR_USER_ACCOUNT_MAP"        # table or view
  email_column: "USERNAME"             # column holding the user's email
  account_number_column: "CLIENT_ACCOUNT_NUMBER"
```

Then authenticate in one of these ways:
- Put a service-account key in the project root as `bigquery-credentials.json`. Git ignores this file.
- Set `GOOGLE_APPLICATION_CREDENTIALS` to the path of a key file.
- Run `gcloud auth application-default login`.

Check the connection with `python validate-bigquery-setup.py`.

## Step 7: Branding

1. Copy your logo into `static/img/`, for example `static/img/contoso-logo.png`.
2. Set `org_logo: "contoso-logo.png"` and `org_name: "Contoso"` in `config.yaml`.

The logo appears in the page footer and on the landing, login, and setup pages.

## Step 8 (optional): Turn on the Metadata API for the Lineage view

Run this on Tableau Server as a server admin:

```
tsm data-service enable
tsm pending-changes apply
```

Every view except Lineage works without it.

## Step 9: Start the app and finish setup

```
python run.py
```

1. Browse to **http://127.0.0.1:5000**, or `http://<host-name>:5000` if `host` is `0.0.0.0`.
2. On the **Setup** screen, enter:
   - **PAT Name** and **PAT Secret** from Step 3
   - **Passcode** and **Confirm Passcode**: a passcode you choose for signing in to this dashboard
3. Submit. The app checks the PAT against `default_site`, stores it encrypted (the
   passcode is stored as a hash) in `instance/cache.db`, and starts the first sync.
   With several large sites, the first sync can take a few minutes.

From then on, a sync runs every `refresh_interval_minutes`. To start over, stop the
app and delete the `instance/` folder.

## Step 10 (optional): Run it permanently

**Docker** (run only one container: the app uses SQLite and a scheduler that runs inside the app process):
```
docker build -t tableau-admin-dashboard .
docker run -d --name tad -p 5000:5000 \
  -v tad-data:/app/data \
  -v "$(pwd)/config.yaml:/app/config.yaml:ro" \
  tableau-admin-dashboard
```
The `tad-data` volume keeps the cache, the encrypted PAT, and the passcode across
restarts. The health check endpoint is `/healthz`.

**Windows service (NSSM):** run `scripts\setup-service.ps1` from an elevated
PowerShell. The scripts find the project folder from their own location, so they work
wherever you cloned the repo. For a scheduled health check, use
`scripts\setup-health-check-task.ps1`, and set the email defaults at the top of
`scripts\health-check.ps1`. `DEPLOYMENT.md` has the details.

**Network access:** if anyone else will use the app, put a reverse proxy with TLS
(IIS, nginx, or similar) in front of it. Don't expose port 5000 directly.

## Step 11: Build on it

Read `CLAUDE.md` first. The main conventions:

| Area | Convention |
|---|---|
| Pages and APIs | One Flask blueprint per feature in `routes/<feature>.py`, registered in `app.py`; templates go in `templates/` |
| Database | All access goes through plain functions in `db.py` (SQLite, no ORM) |
| Tableau calls | `tableau_client.py` (REST, via tableauserverclient) and `metadata_client.py` (GraphQL Metadata API) |
| Settings | Read with `config.settings.<name>`; add new settings to `config.py` **and** `config.example.yaml` |
| Governance rules | `governance.yaml`, loaded by `governance_config.py` |
| Scheduled jobs | Defined only in `scheduler.py` |
| Tests | pytest in `tests/`; run one file at a time, e.g. `pytest tests/test_alerts_engine.py -q` |
| Golden rule | The app never writes to Tableau on its own. It reports, and a person acts. |

`FEATURE_IDEAS.md` has a list of ideas to start from, such as server health, active
sessions, and a user audit trail.

To pull updates from upstream later:
```
git fetch upstream
git merge upstream/master
```
Your `config.yaml` is git-ignored, so updates never overwrite it. When upstream adds
new settings, compare your file with `config.example.yaml`.

---

## Using an AI coding assistant

These prompts are written for Claude Code, but any coding agent that can read the repo
and run commands will work. Open the assistant in the cloned `tableau-admin-dashboard`
folder and paste one of them.

### Prompt 1: Set it up for my organization

```text
I want to set up the Tableau Admin Dashboard in this folder for my organization.
Read ADOPTION_GUIDE.md and CLAUDE.md first, then walk me through setup one step
at a time.

Before you change anything, ask me for these values and wait for my answers.
Don't guess or invent any of them:
1. Tableau Server URL
2. Site content URLs to monitor, and which one is the default
3. Whether only I will use it (127.0.0.1) or teammates will connect too (0.0.0.0)
4. SMTP relay host and port, plus alert sender and recipient emails,
   or "none" to turn off email alerts
5. Organization name, the logo file path (if any), and our staff email domain
6. Whether we have a BigQuery table that maps user emails to account numbers.
   If yes: project, dataset, view, and the two column names. If no, leave it disabled.
7. Anything in governance.yaml we should change (inactive-user days,
   the name of our "All Users" group, service-account name patterns)

Then:
- Create the virtual environment and install requirements.txt.
- Create config.yaml from config.example.yaml using my answers. Don't commit it.
- Copy my logo into static/img/ if I gave you one.
- Run the test suite once and show me the result.
- Start the app with `python run.py` and tell me the URL to open. Don't ask me for
  my PAT secret. I'll enter it on the /setup page myself.

Rules: don't hard-code organization values in Python or template files; they belong
in config.yaml. Don't change anything in Tableau. Show me each file change before
you make it.
```

### Prompt 2: Add a feature

```text
I want to add a feature to the Tableau Admin Dashboard in this folder:

<describe the feature, e.g. "an Active Sessions page listing who is signed in to
each site, with session duration, refreshed by the scheduled sync">

Read CLAUDE.md and ADOPTION_GUIDE.md ("Build on it") first. Find the closest
existing feature and follow its pattern: a blueprint in routes/, DB functions in
db.py, Tableau calls in tableau_client.py or metadata_client.py, scheduled work in
scheduler.py, and a template that extends base.html. Add a nav link the same way the
other pages do.

Before writing code, give me a short plan: which files you'll change, which Tableau
API calls you'll use, and any new config settings. New settings go in config.py and
config.example.yaml with a comment.

Constraints:
- Read-only toward Tableau. Never delete, change permissions, or reassign anything.
- Keep the change small. Don't refactor unrelated code.
- Add pytest tests in tests/ and run only those tests, plus any existing tests for
  the files you touched.
- When you're done, summarize what changed and how to try it in the browser.
```

---

## Troubleshooting

| Problem | What to check |
|---|---|
| `config.yaml not found` on startup | You skipped Step 4. Copy `config.example.yaml` to `config.yaml`. |
| Setup says the PAT is invalid | Check `server_url` (base URL only) and `default_site`. PATs expire after 15 days unused, so create a new one if needed. |
| A site shows no data | The PAT's account doesn't have access to that site, or the site name is wrong (it's case-sensitive) |
| Lineage page is empty | The Metadata API isn't enabled (Step 8) |
| No alert emails | `smtp_host` is blank, or the relay rejects mail from `alert_email_from` |
| No Internal/External filter on Custom Views | `internal_email_domain` isn't set |
| "BigQuery sync failed" | Check the `bigquery` settings and credentials, then run `python validate-bigquery-setup.py` |
| Teammates can't connect | Check `host: "0.0.0.0"` and that the Windows firewall allows the port |
| Start completely fresh | Stop the app, delete the `instance/` folder, and restart |
