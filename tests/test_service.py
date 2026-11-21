import socket

import xbmc
import xbmcgui

from resources.lib.leanback import service


def busy_port():
    """A listening socket holding a port, like another Kodi service or program would."""
    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    sock.listen(1)
    return sock


def test_start_server_skips_ports_in_use(monkeypatch):
    holder = busy_port()
    taken = holder.getsockname()[1]
    monkeypatch.setattr(service, 'PREFERRED_PORTS', (taken, 0))
    try:
        server = service._start_server()
        assert server is not None and server.server_address[1] != taken
        server.server_close()
    finally:
        holder.close()
    assert any('port %d unavailable' % taken in msg for _, msg in xbmc.LOG)


def run_service(monkeypatch, during=None):
    """Run the service until Kodi asks it to stop, calling during(port) while it is up."""
    monkeypatch.setattr(service, 'PREFERRED_PORTS', (0,))
    seen = {}

    def wait(self, timeout=0):
        seen['port'] = int(xbmcgui.Window(10000).getProperty(service.PORT_PROPERTY))
        if during:
            during(seen['port'])
        return True

    monkeypatch.setattr(xbmc.Monitor, 'waitForAbort', wait)
    service.run()
    return seen['port']


def test_service_releases_port_and_property_on_exit(monkeypatch):
    port = run_service(monkeypatch)
    assert xbmcgui.Window(10000).getProperty(service.PORT_PROPERTY) == ''
    # The listening socket is closed, so the next start can bind the same port straight away.
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
    assert xbmcgui.Window(10000).getProperty(service.PORT_PROPERTY) == str(port + 1)


def test_preferred_ports_avoid_other_addons_and_ephemeral_range():
    fixed = [port for port in service.PREFERRED_PORTS if port]
    assert not set(fixed) & set(service.OTHER_ADDON_PORTS)
    assert all(port > 60999 for port in fixed)  # above Linux's default ephemeral range
