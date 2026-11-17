"""Regression tests for scheduler._poll_all_sites().

_poll_all_sites is the 5-minute real-time alert poller. From when it was added
(Aug 11) until this fix, it called `tableau_client.get_server(site)`, a
function that never existed in tableau_client.py. Every single run raised
AttributeError, which the broad `except Exception` swallowed and logged - so
real-time alerts silently never fired. This suite exercises the actual
scheduler.py code path (not a reimplementation) to make sure background_poller
keeps receiving a real signed-in server on every poll cycle.
"""
import contextlib
import sys
from pathlib import Path
from unittest import mock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import scheduler


@contextlib.contextmanager
def _fake_signed_in_server(server_url, site_name, pat_name, pat_secret):
    yield f"server-for-{site_name}"


class TestPollAllSitesSetupGuard:
    def test_skips_when_pat_not_configured(self):
        """No PAT saved yet (fresh install) - must not attempt to sign in."""
        with mock.patch.object(scheduler.db, "get_config", return_value=None), \
             mock.patch.object(scheduler.tableau_client, "signed_in_server") as mock_signin, \
             mock.patch.object(scheduler.background_poller, "poll_site") as mock_poll:
            scheduler._poll_all_sites()

        mock_signin.assert_not_called()
        mock_poll.assert_not_called()


class TestPollAllSitesHappyPath:
    def test_signs_in_and_polls_every_configured_site(self):
        """Regression test for the missing tableau_client.get_server bug.

        Under the old code this raised AttributeError on the first site and
        background_poller.poll_site was never reached.
        """
        config = {"pat_name": "my-pat", "pat_encrypted": "cipher-text"}

        with mock.patch.object(scheduler.db, "get_config", side_effect=lambda k, default=None: config.get(k, default)), \
             mock.patch.object(scheduler.crypto, "decrypt_value", return_value="plain-secret") as mock_decrypt, \
             mock.patch.object(scheduler.settings, "sites", ["default", "marketing"]), \
             mock.patch.object(scheduler.settings, "server_url", "https://tableau.example.com"), \
             mock.patch.object(scheduler.tableau_client, "signed_in_server", side_effect=_fake_signed_in_server) as mock_signin, \
             mock.patch.object(scheduler.background_poller, "poll_site") as mock_poll:
            scheduler._poll_all_sites()

        mock_decrypt.assert_called_once_with("cipher-text")
        assert mock_signin.call_count == 2
        mock_signin.assert_any_call("https://tableau.example.com", "default", "my-pat", "plain-secret")
        mock_signin.assert_any_call("https://tableau.example.com", "marketing", "my-pat", "plain-secret")

        assert mock_poll.call_count == 2
        mock_poll.assert_any_call("default", "server-for-default")
        mock_poll.assert_any_call("marketing", "server-for-marketing")


class TestPollAllSitesErrorIsolation:
    def test_one_site_failing_does_not_stop_the_others(self):
        """A sign-in error on one site (e.g. expired PAT) must not prevent
        the poller from still checking the remaining sites."""
        config = {"pat_name": "my-pat", "pat_encrypted": "cipher-text"}

        def flaky_signin(server_url, site_name, pat_name, pat_secret):
            if site_name == "broken-site":
                raise RuntimeError("sign-in failed")
            return _fake_signed_in_server(server_url, site_name, pat_name, pat_secret)

        with mock.patch.object(scheduler.db, "get_config", side_effect=lambda k, default=None: config.get(k, default)), \
             mock.patch.object(scheduler.crypto, "decrypt_value", return_value="plain-secret"), \
             mock.patch.object(scheduler.settings, "sites", ["broken-site", "default"]), \
             mock.patch.object(scheduler.settings, "server_url", "https://tableau.example.com"), \
             mock.patch.object(scheduler.tableau_client, "signed_in_server", side_effect=flaky_signin), \
             mock.patch.object(scheduler.background_poller, "poll_site") as mock_poll:
            scheduler._poll_all_sites()

        mock_poll.assert_called_once_with("default", "server-for-default")
