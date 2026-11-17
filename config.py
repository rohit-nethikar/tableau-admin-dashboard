"""Loads non-secret settings from config.yaml."""
import os
import yaml

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.environ.get("APP_CONFIG_PATH", os.path.join(BASE_DIR, "config.yaml"))
APP_DATA_DIR = os.path.abspath(
    os.environ.get("APP_DATA_DIR", os.path.join(BASE_DIR, "instance"))
)
INSTANCE_DIR = APP_DATA_DIR
DB_PATH = os.path.join(INSTANCE_DIR, "cache.db")
SECRET_KEY_PATH = os.path.join(INSTANCE_DIR, "secret.key")


class Settings:
    def __init__(self, data):
        self.server_url = os.environ.get("TABLEAU_SERVER_URL", data["server_url"]).rstrip("/")
        self.host = os.environ.get("APP_HOST", data.get("host", "127.0.0.1"))
        self.port = int(os.environ.get("APP_PORT", data.get("port", 5000)))
        sites_env = os.environ.get("TABLEAU_SITES")
        self.sites = (
            [site.strip() for site in sites_env.split(",") if site.strip()]
            if sites_env
            else data["sites"]
        )
        self.default_site = os.environ.get("TABLEAU_DEFAULT_SITE", data.get("default_site", self.sites[0]))
        self.refresh_interval_minutes = int(data.get("refresh_interval_minutes", 60))
        self.site_switch_staleness_minutes = int(data.get("site_switch_staleness_minutes", 5))
        self.stale_threshold_days = int(data.get("stale_threshold_days", 90))
        # Extract-failure email alerting - optional; leave smtp_host unset to disable.
        self.smtp_host = data.get("smtp_host")
        self.smtp_port = int(data.get("smtp_port", 25))
        self.alert_email_from = data.get("alert_email_from")
        self.alert_email_to = data.get("alert_email_to")
        self.license_alert_threshold_pct = float(data.get("license_alert_threshold_pct", 90))

        # Organization branding - shown in the page header, login, landing and setup pages.
        # org_logo is a filename under static/img/; leave blank to show no org logo.
        self.org_name = data.get("org_name") or "Your Organization"
        self.org_logo = data.get("org_logo") or ""
        # Email domain that marks a user as "internal" (e.g. "yourorg.com"). Drives the
        # Internal/External filter on the Custom Views page. Blank disables that filter.
        self.internal_email_domain = (data.get("internal_email_domain") or "").strip().lstrip("@").lower()

        # Optional BigQuery account-number sync (see bigquery_sync.py). Off unless
        # bigquery.enabled is true AND project/dataset/view are set.
        bq = data.get("bigquery") or {}
        self.bq_project = bq.get("project") or ""
        self.bq_dataset = bq.get("dataset") or ""
        self.bq_view = bq.get("view") or ""
        self.bq_email_column = bq.get("email_column") or "USERNAME"
        self.bq_account_number_column = bq.get("account_number_column") or "CLIENT_ACCOUNT_NUMBER"
        self.bq_enabled = bool(bq.get("enabled")) and bool(self.bq_project and self.bq_dataset and self.bq_view)


def load_settings():
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(
            f"{CONFIG_PATH} not found. Copy config.example.yaml to config.yaml and "
            "fill in your Tableau server URL and site names (see ADOPTION_GUIDE.md)."
        )
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return Settings(data)


os.makedirs(INSTANCE_DIR, exist_ok=True)
settings = load_settings()

