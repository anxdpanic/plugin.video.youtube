import socket

import pytest
import xbmc
import xbmcaddon
import xbmcgui

from resources.lib.youtube import service


def busy_port():
    """A listening socket holding a port, like another Kodi service or program would."""
    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    sock.listen(1)
    return sock


def published():
    value = xbmcgui.Window(10000).getProperty(service.PORT_PROPERTY)
    return int(value) if value else None


def free_port():
    sock = busy_port()
    port = sock.getsockname()[1]
    sock.close()
    return port


@pytest.fixture
def httpd():
    instance = service.Httpd(xbmcgui.Window(10000))
    yield instance
    instance.stop()


def test_default_port_is_not_the_earlier_default_and_avoids_ephemeral_range():
    assert service.DEFAULT_PORT != 50152  # earlier plugin.video.youtube versions' default
    fallbacks = [p for p in service.candidate_ports(service.DEFAULT_PORT) if p]
    assert all(p > 60999 for p in fallbacks)  # above Linux's default ephemeral range


@pytest.mark.parametrize('setting, expected', [
    (61200, 61200),
    (0, 0),                                  # any free port
    (80, service.DEFAULT_PORT),              # needs root
    (70000, service.DEFAULT_PORT),
])
def test_wanted_port_reads_and_checks_the_setting(setting, expected):
    xbmcaddon.SETTINGS['service_port'] = setting
    assert service.wanted_port() == expected


def test_candidate_ports():
    assert service.candidate_ports(61152) == (61152, 61153, 61154, 0)
    assert service.candidate_ports(65535) == (65535, 0)
    assert service.candidate_ports(0) == (0,)


def test_starts_on_the_chosen_port(httpd):
    port = free_port()
    assert httpd.start(port)
    assert httpd.port == port == published()
    assert xbmcgui.NOTIFICATIONS == []


def test_busy_port_falls_back_and_says_so(httpd):
    xbmcaddon.STRINGS[30146] = 'Port %d is in use, using %d'  # loaded
    holder = busy_port()
    taken = holder.getsockname()[1]
    try:
        assert httpd.start(taken)
    finally:
        holder.close()
    assert httpd.port != taken and published() == httpd.port
    assert any('port %d unavailable' % taken in msg for _, msg in xbmc.LOG)
    [(_, message, icon)] = xbmcgui.NOTIFICATIONS
    assert icon == xbmcgui.NOTIFICATION_WARNING
    assert message == 'Port %d is in use, using %d' % (taken, httpd.port)


def test_any_free_port_needs_no_notice(httpd):
    assert httpd.start(0)
    assert httpd.port and xbmcgui.NOTIFICATIONS == []


def test_changing_the_setting_moves_the_server(httpd):
    first, second = free_port(), free_port()
    httpd.start(first)
    xbmcaddon.SETTINGS['service_port'] = second
    httpd.follow_setting()
    assert httpd.port == second == published()
    # The old port is released straight away.
    again = socket.socket()
    again.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    again.bind(('127.0.0.1', first))
    again.close()


def test_unchanged_setting_keeps_the_server(httpd):
    port = free_port()
    xbmcaddon.SETTINGS['service_port'] = port
    httpd.start(port)
    server = httpd.server
    httpd.follow_setting()
    assert httpd.server is server


def test_failed_move_keeps_the_old_server(httpd, monkeypatch):
    httpd.start(free_port())
    server = httpd.server
    monkeypatch.setattr(service, '_start_server', lambda ports: None)
    xbmcaddon.SETTINGS['service_port'] = free_port()
    httpd.follow_setting()
    assert httpd.server is server and published() == httpd.port


def run_service(monkeypatch, during=None):
    """Run the service until Kodi asks it to stop, calling during(port) while it is up."""
    xbmcaddon.SETTINGS['service_port'] = 0
    seen = {}

    def wait(self, timeout=0):
        seen['port'] = published()
        if during:
            during(seen['port'])
        return True

    monkeypatch.setattr(xbmc.Monitor, 'waitForAbort', wait)
    service.run()
    return seen['port']


def test_service_releases_port_and_property_on_exit(monkeypatch):
    port = run_service(monkeypatch)
    assert published() is None
    again = socket.socket()
    again.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    again.bind(('127.0.0.1', port))
    again.close()


def test_exiting_service_keeps_a_newer_instances_port(monkeypatch):
    # An add-on update starts the new service before the old one has stopped; the new one
    # publishes its own port, and the old one must not clear it on the way out.
    def newer_instance_started(port):
        xbmcgui.Window(10000).setProperty(service.PORT_PROPERTY, str(port + 1))

    port = run_service(monkeypatch, newer_instance_started)
    assert published() == port + 1


def test_service_follows_a_port_change_while_running(monkeypatch):
    target = free_port()
    ticks = []

    def wait(self, timeout=0):
        ticks.append(published())
        if len(ticks) == 1:
            xbmcaddon.SETTINGS['service_port'] = target
            self.onSettingsChanged()
            return False
        return True

    xbmcaddon.SETTINGS['service_port'] = 0
    monkeypatch.setattr(xbmc.Monitor, 'waitForAbort', wait)
    service.run()
    assert ticks[1] == target


def test_failed_port_switch_does_not_stop_the_service(monkeypatch):
    ticks = []

    def wait(self, timeout=0):
        ticks.append(published())
        if len(ticks) == 1:
            self.onSettingsChanged()
        return len(ticks) > 2

    def broken(self):
        raise TypeError('boom')

    xbmcaddon.SETTINGS['service_port'] = 0
    monkeypatch.setattr(xbmc.Monitor, 'waitForAbort', wait)
    monkeypatch.setattr(service.Httpd, 'follow_setting', broken)
    service.run()
    assert len(ticks) == 3 and ticks[2] == ticks[0]
    assert any('boom' in msg for _, msg in xbmc.LOG)
