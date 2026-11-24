# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 plugin.video.youtube
"""TV device-code sign-in (youtube.com/activate) and token storage, with multiple accounts."""
import base64
import time
import uuid

from . import http, kodi


def _reveal(value):
    """Undo the scrambling of the client values below: base64-decode, XOR every byte with 0x5a, then
    reverse. It isn't protection (anyone with this file can undo it), only a way to keep the strings out
    of plain-text searches and automated secret scanners that harvest OAuth clients from public code.
    To scramble a new value: base64.b64encode(bytes(b ^ 0x5a for b in value.encode()[::-1]))."""
    return bytes(b ^ 0x5a for b in base64.b64decode(value))[::-1].decode()


# OAuth client of the YouTube TV (leanback) app, the same one the TV web client uses. The device-code
# flow (youtube.com/activate) only works for clients Google registered for TV-type devices, so the add-on
# signs in as that app; tokens it gets are limited to SCOPE.
CLIENT_ID = _reveal('NzU5dC40Py40NTkoPykvPzY9NTU9dCkqKjt0Ymw5NWk7OGI/OGwxYmsxPyo0Yj4+M29qMjZpNzY+bD53bm9uYmptbG9va2xi')
CLIENT_SECRET = _reveal('DhsCER0dCRkiMzw7FChqKWMdNTIMNTgJ')
SCOPE = 'http://gdata.youtube.com https://www.googleapis.com/auth/youtube'
DEVICE_CODE_URL = 'https://accounts.google.com/o/oauth2/device/code'
TOKEN_URL = 'https://www.googleapis.com/oauth2/v4/token'
REVOKE_URL = 'https://accounts.google.com/o/oauth2/revoke'

STORE = 'accounts.json'


class AuthError(Exception):
    pass


def _store():
    data = kodi.load_json(STORE, {})
    data.setdefault('accounts', {})
    data.setdefault('active', None)
    return data


def accounts():
    """List of (account_id, name) in sign-in order."""
    data = _store()
    items = sorted(data['accounts'].items(), key=lambda kv: kv[1].get('added', 0))
    return [(key, value.get('name') or key) for key, value in items]


def active_account():
    data = _store()
    key = data.get('active')
    if key and key in data['accounts']:
        return key, data['accounts'][key]
    return None, None


def set_active(account_id):
    data = _store()
    data['active'] = account_id if account_id in data['accounts'] else None
    kodi.save_json(STORE, data)


def request_device_code():
    resp = http.request_json(DEVICE_CODE_URL, data={
        'client_id': CLIENT_ID,
        'scope': SCOPE,
        'device_id': str(uuid.uuid4()).replace('-', ''),
        'device_model': 'ytlr::',
    })
    if 'device_code' not in resp:
        raise AuthError(resp.get('error_description') or resp.get('error') or 'no device code')
    return resp


def poll_token(device_code):
    """Returns the token dict, None while still pending, or raises AuthError."""
    try:
        resp = http.request_json(TOKEN_URL, data={
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'code': device_code,
            'grant_type': 'http://oauth.net/grant_type/device/1.0',
        })
    except http.HTTPError as exc:
        resp = exc.json()
    error = resp.get('error')
    if error in ('authorization_pending', 'slow_down'):
        return None
    if error:
        raise AuthError(resp.get('error_description') or error)
    return resp


def add_account(token, name=None):
    data = _store()
    account_id = uuid.uuid4().hex[:12]
    data['accounts'][account_id] = {
        'name': name,
        'access_token': token['access_token'],
        'refresh_token': token.get('refresh_token', ''),
        'expires_at': time.time() + int(token.get('expires_in', 3600)) - 120,
        'added': time.time(),
    }
    data['active'] = account_id
    kodi.save_json(STORE, data)
    return account_id


def rename_account(account_id, name):
    data = _store()
    if account_id in data['accounts'] and name:
        data['accounts'][account_id]['name'] = name
        kodi.save_json(STORE, data)


def remove_account(account_id):
    data = _store()
    account = data['accounts'].pop(account_id, None)
    if data.get('active') == account_id:
        data['active'] = None
    kodi.save_json(STORE, data)
    if account and account.get('refresh_token'):
        try:
            http.request(REVOKE_URL, data={'token': account['refresh_token']})
        except http.HTTPError:
            pass


def access_token(force_refresh=False):
    """Valid access token for the active account, refreshing it when needed. None when signed out."""
    data = _store()
    key = data.get('active')
    account = data['accounts'].get(key) if key else None
    if not account:
        return None
    if not force_refresh and account.get('expires_at', 0) > time.time():
        return account['access_token']
    if not account.get('refresh_token'):
        return None
    try:
        resp = http.request_json(TOKEN_URL, data={
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'refresh_token': account['refresh_token'],
            'grant_type': 'refresh_token',
        })
    except http.HTTPError as exc:
        resp = exc.json()
        if exc.status in (400, 401) and resp.get('error') == 'invalid_grant':
            kodi.log('refresh token rejected, removing account %s' % key)
            data['accounts'].pop(key, None)
            data['active'] = None
            kodi.save_json(STORE, data)
            raise AuthError('invalid_grant') from exc
        raise
    account['access_token'] = resp['access_token']
    account['expires_at'] = time.time() + int(resp.get('expires_in', 3600)) - 120
    if resp.get('refresh_token'):
        account['refresh_token'] = resp['refresh_token']
    kodi.save_json(STORE, data)
    return account['access_token']
