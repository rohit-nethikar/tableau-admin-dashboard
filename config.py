"""Loads non-secret settings from config.yaml."""
import os
import yaml

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.yaml")
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


def load_settings():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return Settings(data)


os.makedirs(INSTANCE_DIR, exist_ok=True)
settings = load_settings()

