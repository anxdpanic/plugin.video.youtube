import shutil

import pytest
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs


@pytest.fixture(autouse=True)
def no_request_pacing(monkeypatch):
    """Requests are spaced out on a device; tests don't wait (test_broker and test_http check the pacing)."""
    import xbmcgui

    from resources.lib.leanback import broker
    monkeypatch.setattr(broker, 'GAPS', {})
    xbmcgui.Window(10000).clearProperty('leanback.port')  # no service: requests go straight to http.send


@pytest.fixture(autouse=True)
def no_banner_fetching(monkeypatch):
    """Listings look up unknown channels' banners before drawing; tests stay offline."""
    from resources.lib.leanback import art
    monkeypatch.setattr(art.Banners, 'fetch_all', lambda self, channel_ids, fetch=None: 0)


@pytest.fixture(autouse=True)
def clean_state():
    """Fresh profile, settings and recorded plugin output for every test."""
    shutil.rmtree(xbmcvfs.ROOT, ignore_errors=True)
    xbmcaddon.SETTINGS.clear()
    xbmcaddon.SETTINGS.update({'shelves_as_folders': True, 'watched_threshold': 80, 'subs_asr': True})
    xbmcplugin.reset()
    del xbmcgui.NOTIFICATIONS[:]
    yield
    shutil.rmtree(xbmcvfs.ROOT, ignore_errors=True)
