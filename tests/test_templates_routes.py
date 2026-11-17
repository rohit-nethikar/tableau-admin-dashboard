"""Tests for routes/templates.py.

Minimal Flask smoke tests proving the blueprint/route/login_required wiring
works. Mirrors tests/test_workbook_compare_routes.py: registers ONLY
routes.templates.bp on a throwaway Flask app - it never imports the real
app.py, which would trigger db.init_db(), scheduler.start(), and a
background BigQuery sync thread against the real instance/cache.db.
Authenticated renders are out of scope here since templates.html extends
base.html, which needs the app-level context processor (current_site,
available_sites, site_refresh_status) and ~20 other blueprints' url_for
targets that only create_app() wires up.
"""
import pytest
from flask import Blueprint, Flask

import routes.templates as templates_routes


def _app_with_login_stubs(monkeypatch):
    import auth

    monkeypatch.setattr(auth.db, "is_setup_complete", lambda: True)

    app = Flask(__name__)
    app.secret_key = "test-secret"
    app.testing = True
    app.register_blueprint(templates_routes.bp)

    setup_bp = Blueprint("setup", __name__)

    @setup_bp.route("/setup")
    def setup():
        return "setup", 200

    auth_routes_bp = Blueprint("auth_routes", __name__)

    @auth_routes_bp.route("/login")
    def login():
        return "login", 200

    app.register_blueprint(setup_bp)
    app.register_blueprint(auth_routes_bp)
    return app


@pytest.mark.parametrize("method,path", [
    ("get", "/templates"),
    ("post", "/templates/add"),
    ("post", "/templates/standards"),
    ("post", "/templates/1/delete"),
    ("get", "/templates/1/download"),
])
def test_unauthenticated_templates_routes_redirect_to_login(monkeypatch, method, path):
    app = _app_with_login_stubs(monkeypatch)
    client = app.test_client()
    response = getattr(client, method)(path)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_credentials_raises_without_pat(monkeypatch):
    monkeypatch.setattr(templates_routes.db, "get_config", lambda key: None)
    with pytest.raises(RuntimeError):
        templates_routes._credentials()
