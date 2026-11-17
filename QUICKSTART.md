# Quick Start: Set Up the Tableau Admin Dashboard for Your Organization

The Tableau Admin Dashboard is a governance tool for Tableau Server. It covers:
- content health scores
- stale and orphaned content
- permission risks
- extract refresh failures
- license seat usage
- custom-view tracking
- workbook compare

It only **reads** from Tableau. It never deletes content, changes permissions, or
reassigns anything.

This page gets you running in about 15 minutes. For the full reference (every
setting, Docker, Windows service, troubleshooting), see **[ADOPTION_GUIDE.md](ADOPTION_GUIDE.md)**.

**Repository:** https://github.com/rohit-nethikar/tableau-admin-dashboard

---

## 1. What you need before you start

- [ ] **Python 3.10 or newer** and **Git** installed
- [ ] **An admin account on your Tableau Server** that can see every site you want to monitor
- [ ] **A Personal Access Token (PAT)** for that account. In Tableau, open your
      profile menu, then **My Account Settings**, then **Personal Access Tokens**.
      Copy the **token name** and the **secret**; the secret is shown only once.
- [ ] **Your Tableau Server URL**, for example `https://tableau.yourorg.com`
- [ ] **Your site names**: the part after `/#/site/` in the browser address bar
- [ ] *(Optional)* SMTP relay and alert email addresses, if you want failure alerts
- [ ] *(Optional)* Your organization's name, a logo file, and your staff email domain

---

## 2. Set it up

### Step 1: Fork and clone
Fork the repo on GitHub (the **Fork** button, top right), so you can commit your own
changes. Then clone your fork:
```
git clone https://github.com/<your-github-user>/tableau-admin-dashboard.git
cd tableau-admin-dashboard
```

### Step 2: Install
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

### Step 3: Create your config
**Windows**
```
copy config.example.yaml config.yaml
```
**Mac / Linux**
```
cp config.example.yaml config.yaml
```
Open `config.yaml` and set at least these:

```yaml
server_url: "https://tableau.yourorg.com"   # base URL only, no trailing slash
sites:
  - "Finance"                                # your site names
  - "Analytics-DEV"
default_site: "Finance"
```

Every other setting is optional and explained in the file: email alerts, branding,
refresh interval. Leave `bigquery.enabled: false` unless you have your own BigQuery
table that maps user emails to account numbers.

> `config.yaml` is git-ignored, so your server name and emails are never committed.

### Step 4 (optional): Tune governance rules
Edit `governance.yaml` to match your policies. For example, set how many days
without login makes a user inactive (`inactive_user_days`), or the name of your
"All Users" group.

### Step 5: Start the app
```
python run.py
```

### Step 6: Finish setup in the browser
1. Open **http://127.0.0.1:5000**.
2. Enter your **PAT name** and **PAT secret**, then choose a **passcode** for signing in.
3. Submit. The first sync starts automatically. With several large sites it can
   take a few minutes.

You're done. The dashboard re-syncs on its own every 60 minutes, which you can
change in `config.yaml`.

---

## 3. Faster: let an AI assistant set it up

If you use **Claude Code** or a similar coding assistant, open it in the cloned
`tableau-admin-dashboard` folder and paste this prompt:

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

---

## 4. Build your own features

Once it's running, use this prompt to add features. Replace the `<...>` part with
your idea. For examples, see [FEATURE_IDEAS.md](FEATURE_IDEAS.md).

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

**Where things live**, if you're coding by hand:

| What | Where |
|---|---|
| Pages and APIs | `routes/<feature>.py` (Flask blueprints, registered in `app.py`) |
| HTML | `templates/` (extend `base.html`) |
| Database | functions in `db.py` (SQLite) |
| Tableau API calls | `tableau_client.py`, `metadata_client.py` |
| Scheduled jobs | `scheduler.py` |
| Settings | `config.py` + `config.example.yaml` |
| Tests | `tests/` (run with `pytest tests/<file>.py -q`) |

---

## 5. Get updates later

Run these once to link the original repo:
```
git remote add upstream https://github.com/rohit-nethikar/tableau-admin-dashboard.git
```
Then, whenever you want the latest changes:
```
git fetch upstream
git merge upstream/master
```
Updates never overwrite your `config.yaml`. If an update adds new settings, compare
your file with `config.example.yaml`.

---

## 6. Common problems

| Problem | Fix |
|---|---|
| `config.yaml not found` | You skipped Step 3. Copy `config.example.yaml` to `config.yaml`. |
| Setup says the PAT is invalid | Check `server_url` (base URL only) and `default_site`. Unused PATs expire after 15 days, so create a new one if needed. |
| A site shows no data | The PAT's account can't access that site, or the site name is wrong (it's case-sensitive) |
| Lineage page is empty | A server admin needs to run `tsm data-service enable`, then `tsm pending-changes apply` |
| No alert emails | `smtp_host` is blank in `config.yaml`, or your relay is rejecting the mail |
| Teammates can't connect | Set `host: "0.0.0.0"` in `config.yaml` and allow the port through the firewall |
| Start completely fresh | Stop the app, delete the `instance/` folder, and restart |

**Never commit or share:** `config.yaml`, `bigquery-credentials.json`, the
`instance/` folder, or your Personal Access Token.

More detail: **[ADOPTION_GUIDE.md](ADOPTION_GUIDE.md)**
