# -*- coding: utf-8 -*-
"""

    Copyright (C) 2023-present plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from ..youtube_exceptions import YouTubeException
from ...kodion.network import BaseRequestsClass
from ...kodion.utils import merge_dicts


class YouTubeRequestClient(BaseRequestsClass):
    _API_KEYS = {
        'android': 'AIzaSyA8eiZmM1FaDVjRy-df2KTyQ_vz_yYM39w',
        'android_embedded': 'AIzaSyCjc_pVEDi4qsv5MtC2dMXzpIaDoRFLsxw',
        'ios': 'AIzaSyB-63vPrdThhKuerbB2N_l7Kwwcxj6yUAc',
        'ios_youtube_tv': 'AIzaSyAA2X8Iz20HQACliPKA2J9URIdPmS3xFUA',
        'android_youtube_tv': 'AIzaSyDCU8hByM-4DrUqRUYnGn-3llEO78bcxq8',
        'web': 'AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8',
    }
    _PLAYER_PARAMS = {
        'android': 'CgIIAdgDAQ==',
        'android_testsuite': '2AMB',
    }

    CLIENTS = {
        # Disabled - requires PO token
        # Requests for stream urls result in HTTP 403 errors
        'android': {
            '_disabled': True,
            '_id': {
                'client_id': 3,
                'client_name': 'ANDROID',
                'client_version': '20.10.38',
                'android_sdk_version': '32',
                'os_name': 'Android',
                'os_version': '15',
                'package_id': 'com.google.android.youtube',
                'platform': 'MOBILE',
            },
            '_auth_type': False,
            '_query_subtitles': 'optional',
            'json': {
                'context': {
                    'client': {
                        'clientName': '{_id[client_name]}',
                        'clientVersion': '{_id[client_version]}',
                        'androidSdkVersion': '{_id[android_sdk_version]}',
                        'osName': '{_id[os_name]}',
                        'osVersion': '{_id[os_version]}',
                        'platform': '{_id[platform]}',
                    },
                },
            },
            'headers': {
                'User-Agent': (
                    '{_id[package_id]}/{_id[client_version]}'
                    ' (Linux; U;'
                    ' {_id[os_name]} {_id[os_version]}'
                    ') gzip'
                ),
                'X-YouTube-Client-Name': '{_id[client_id]}',
                'X-YouTube-Client-Version': '{_id[client_version]}',
            },
        },
        'android_vr': {
            '_id': {
                'client_id': 28,
                'client_name': 'ANDROID_VR',
                'client_version': '1.62.27',
                'android_sdk_version': '32',
                'device_codename': 'eureka',
                'device_make': 'Oculus',
                'device_model': 'Quest 3',
                'os_name': 'Android',
                'os_version': '12L',
                'os_build': 'SQ3A.220605.009.A1',
                'package_id': 'com.google.android.apps.youtube.vr.oculus',
            },
            '_query_subtitles': False,
            'json': {
                'context': {
                    'client': {
                        'androidSdkVersion': '{_id[android_sdk_version]}',
                        'clientName': '{_id[client_name]}',
                        'clientVersion': '{_id[client_version]}',
                        'deviceMake': '{_id[device_make]}',
                        'deviceModel': '{_id[device_model]}',
                        'osName': '{_id[os_name]}',
                        'osVersion': '{_id[os_version]}',
                    },
                },
            },
            'headers': {
                'User-Agent': (
                    '{_id[package_id]}/{_id[client_version]}'
                    ' (Linux; U;'
                    ' {_id[os_name]} {_id[os_version]};'
                    ' {_id[device_codename]}-user'
                    ' Build/{_id[os_build]}'
                    ') gzip'
                ),
                'X-YouTube-Client-Name': '{_id[client_id]}',
                'X-YouTube-Client-Version': '{_id[client_version]}',
            },
        },
        # 4k with HDR
        # Some videos block this client, may also require embedding enabled
        # Limited subtitle availability
        # Limited audio streams
        'android_youtube_tv': {
            '_id': {
                'client_id': 29,
                'client_name': 'ANDROID_UNPLUGGED',
                'client_version': '9.03.2',
                'android_sdk_version': '32',
                'os_name': 'Android',
                'os_version': '12',
                'package_id': 'com.google.android.apps.youtube.unplugged',
                'platform': 'TV',
            },
            '_auth_required': True,
            '_auth_type': 'personal',
            '_query_subtitles': True,
            'json': {
                'context': {
                    'client': {
                        'clientName': '{_id[client_name]}',
                        'clientVersion': '{_id[client_version]}',
                        'androidSdkVersion': '{_id[android_sdk_version]}',
                        'osName': '{_id[os_name]}',
                        'osVersion': '{_id[os_version]}',
                        'platform': '{_id[platform]}',
                    },
                },
            },
            'headers': {
                'User-Agent': (
                    '{_id[package_id]}/{_id[client_version]}'
                    ' (Linux; U;'
                    ' {_id[os_name]} {_id[os_version]}'
                    ') gzip'
                ),
                'X-YouTube-Client-Name': '{_id[client_id]}',
                'X-YouTube-Client-Version': '{_id[client_version]}',
            },
        },
        # Disabled - all player requests result in following response
        # UNPLAYABLE - This video is not available
        # 4k no VP9 HDR
        # Limited subtitle availability
        'android_testsuite': {
            '_id': 30,
            '_disabled': True,
            '_query_subtitles': True,
            'json': {
                # 'params': _PLAYER_PARAMS['android_testsuite'],
                'context': {
                    'client': {
                        'clientName': 'ANDROID_TESTSUITE',
                        'clientVersion': '1.9',
                        'androidSdkVersion': '30',
                        'osName': 'Android',
                        'osVersion': '11',
                        'platform': 'MOBILE',
                    },
                },
            },
            'headers': {
                'User-Agent': (
                    'com.google.android.youtube/'
                    '{json[context][client][clientVersion]}'
                    ' (Linux; U; {json[context][client][osName]}'
                    ' {json[context][client][osVersion]}) gzip'
                ),
                'X-YouTube-Client-Name': '{_id}',
                'X-YouTube-Client-Version': '{json[context][client][clientVersion]}',
            },
        },
        # Disabled - requires PO token
        # Requests for stream urls result in HTTP 403 errors
        # Only for videos that allow embedding
        # Limited to 720p on some videos
        'android_embedded': {
            '_id': 55,
            '_disabled': True,
            '_query_subtitles': 'optional',
            'json': {
                'context': {
                    'client': {
                        'clientName': 'ANDROID_EMBEDDED_PLAYER',
                        'clientScreen': 'EMBED',
                        'clientVersion': '19.29.37',
                        'androidSdkVersion': '30',
                        'osName': 'Android',
                        'osVersion': '11',
                        'platform': 'MOBILE',
                    },
                },
                'thirdParty': {
                    'embedUrl': 'https://www.youtube.com/',
                },
            },
            'headers': {
                'User-Agent': (
                    'com.google.android.youtube/'
                    '{json[context][client][clientVersion]}'
                    ' (Linux; U; {json[context][client][osName]}'
                    ' {json[context][client][osVersion]}) gzip'
                ),
                'X-YouTube-Client-Name': '{_id}',
                'X-YouTube-Client-Version': '{json[context][client][clientVersion]}',
            },
        },
        'ios': {
            '_id': {
                'client_id': 5,
                'client_name': 'IOS',
                'client_version': '20.11.6',
                'device_make': 'Apple',
                'device_model': 'iPhone16,2',
                'os_name': 'iOS',
                'os_major': '18',
                'os_minor': '3',
                'os_patch': '2',
                'os_build': '22D82',
                'package_id': 'com.google.ios.youtube',
                'platform': 'MOBILE',
            },
            '_auth_type': False,
            'json': {
                'context': {
                    'client': {
                        'clientName': '{_id[client_name]}',
                        'clientVersion': '{_id[client_version]}',
                        'deviceMake': '{_id[device_make]}',
                        'deviceModel': '{_id[device_model]}',
                        'osName': '{_id[os_name]}',
                        'osVersion': (
                            '{_id[os_major]}'
                            '.{_id[os_minor]}'
                            '.{_id[os_patch]}'
                            '.{_id[os_build]}'
                        ),
                        'platform': '{_id[platform]}',
                    },
                },
            },
            'headers': {
                'User-Agent': (
                    '{_id[package_id]}/{_id[client_version]}'
                    ' ({_id[device_model]}; U; CPU'
                    ' {_id[os_name]}'
                    ' {_id[os_major]}_{_id[os_minor]}_{_id[os_patch]}'
                    ' like Mac OS X)'
                ),
                'X-YouTube-Client-Name': '{_id[client_id]}',
                'X-YouTube-Client-Version': '{_id[client_version]}',
            },
        },
        'ios_youtube_tv': {
            '_id': {
                'client_id': 33,
                'client_name': 'IOS_UNPLUGGED',
                'client_version': '9.04',
                'device_make': 'Apple',
                'device_model': 'iPhone16,2',
                'os_name': 'iOS',
                'os_major': '18',
                'os_minor': '3',
                'os_patch': '2',
                'os_build': '22D82',
                'package_id': 'com.google.ios.youtubeunplugged',
                'platform': 'MOBILE',
            },
            '_auth_required': True,
            '_auth_type': 'personal',
            'json': {
                'context': {
                    'client': {
                        'clientName': '{_id[client_name]}',
                        'clientVersion': '{_id[client_version]}',
                        'deviceMake': '{_id[device_make]}',
                        'deviceModel': '{_id[device_model]}',
                        'osName': '{_id[os_name]}',
                        'osVersion': (
                            '{_id[os_major]}'
                            '.{_id[os_minor]}'
                            '.{_id[os_patch]}'
                            '.{_id[os_build]}'
                        ),
                        'platform': '{_id[platform]}',
                    },
                },
            },
            'headers': {
                'User-Agent': (
                    '{_id[package_id]}/{_id[client_version]}'
                    ' ({_id[device_model]}; U; CPU'
                    ' {_id[os_name]}'
                    ' {_id[os_major]}_{_id[os_minor]}_{_id[os_patch]}'
                    ' like Mac OS X)'
                ),
                'X-YouTube-Client-Name': '{_id[client_id]}',
                'X-YouTube-Client-Version': '{_id[client_version]}',
            },
        },
        # Disabled - request are now blocked with following response
        # 403 Forbidden - The caller does not have permission
        # Provides progressive streams
        'media_connect_frontend': {
            '_id': 95,
            '_disabled': True,
            '_query_subtitles': True,
            'json': {
                'context': {
                    'client': {
                        'clientName': 'MEDIA_CONNECT_FRONTEND',
                        'clientVersion': '0.1',
                    },
                },
            },
            'headers': {},
        },
        # Used to requests captions for clients that don't provide them
        # Requires handling of nsig to overcome throttling (TODO)
        'smart_tv_embedded': {
            '_id': 85,
            'json': {
                'context': {
                    'client': {
                        'clientName': 'TVHTML5_SIMPLY_EMBEDDED_PLAYER',
                        'clientScreen': 'WATCH',
                        'clientVersion': '2.0',
                    },
                },
                'thirdParty': {
                    'embedUrl': 'https://www.google.com/',
                },
            },
            # Headers from a 2022 Samsung Tizen 6.5 based Smart TV
            'headers': {
                'User-Agent': ('Mozilla/5.0 (SMART-TV; LINUX; Tizen 6.5)'
                               ' AppleWebKit/537.36 (KHTML, like Gecko)'
                               ' 85.0.4183.93/6.5 TV Safari/537.36'),
            },
        },
        'v1': {
            '_id': {
                'client_id': 1,
                'client_name': 'WEB',
                'client_version': '2.20250312.04.00',
            },
            'url': 'https://www.youtube.com/youtubei/v1/{_endpoint}',
            'method': None,
            'json': {
                'context': {
                    'client': {
                        'clientName': '{_id[client_name]}',
                        'clientVersion': '{_id[client_version]}',
                    },
                },
            },
            'headers': {
                'X-YouTube-Client-Name': '{_id[client_id]}',
                'X-YouTube-Client-Version': '{_id[client_version]}',
            },
        },
        'v3': {
            '_auth_requested': 'personal',
            'url': 'https://www.googleapis.com/youtube/v3/{_endpoint}',
            'method': None,
            'headers': {
                'Host': 'www.googleapis.com',
            },
            'params': {
                'key': None,
            },
        },
        'tv': {
            '_id': {
                'client_id': 7,
                'client_name': 'TVHTML5',
                'client_version': '7.20250312.16.00',
            },
            'url': 'https://www.youtube.com/youtubei/v1/{_endpoint}',
            'method': None,
            'json': {
                'context': {
                    'client': {
                        'clientName': '{_id[client_name]}',
                        'clientVersion': '{_id[client_version]}',
                    },
                },
            },
            'headers': {
                'User-Agent': (
                    'Mozilla/5.0'
                    ' (ChromiumStylePlatform)'
                    ' Cobalt/Version'
                ),
                'X-YouTube-Client-Name': '{_id[client_id]}',
                'X-YouTube-Client-Version': '{_id[client_version]}',
            },
        },
        'tv_embed': {
            '_id': {
                'client_id': 85,
                'client_name': 'TVHTML5_SIMPLY_EMBEDDED_PLAYER',
                'client_version': '2.0',
            },
            'url': 'https://www.youtube.com/youtubei/v1/{_endpoint}',
            'method': None,
            'json': {
                'context': {
                    'client': {
                        'clientName': '{_id[client_name]}',
                        'clientVersion': '{_id[client_version]}',
                    },
                },
            },
            'headers': {
                'X-YouTube-Client-Name': '{_id[client_id]}',
                'X-YouTube-Client-Version': '{_id[client_version]}',
            },
        },
        'mweb': {
            '_id': {
                'client_id': 2,
                'client_name': 'MWEB',
                'client_version': '2.20250311.03.00',
                'device_make': 'Apple',
                'device_model': 'iPad',
                'os_name': 'OS',
                'os_major': '16',
                'os_minor': '7',
                'os_patch': '10',
                'os_build': '15E148',
                'platform': 'MOBILE',
            },
            'url': 'https://www.youtube.com/youtubei/v1/{_endpoint}',
            'method': None,
            'json': {
                'context': {
                    'client': {
                        'clientName': '{_id[client_name]}',
                        'clientVersion': '{_id[client_version]}',
                    },
                },
            },
            'headers': {
                'User-Agent': (
                    'Mozilla/5.0'
                    ' ({_id[device_model]};'
                    ' CPU'
                    ' {_id[os_name]}'
                    ' {_id[os_major]}_{_id[os_minor]}_{_id[os_patch]}'
                    ' like Mac OS X)'
                    ' AppleWebKit/605.1.15 (KHTML, like Gecko)'
                    ' Version/{_id[os_major]}.{_id[os_minor]}'
                    ' {_id[platform]}/{_id[os_build]}'
                    ' Safari/604.1,gzip(gfe)'
                ),
                'X-YouTube-Client-Name': '{_id[client_id]}',
                'X-YouTube-Client-Version': '{_id[client_version]}',
            },
        },
        # Used for misc api requests by default
        # Requires handling of nsig to overcome throttling (TODO)
        'web': {
            '_id': 1,
            'json': {
                'context': {
                    'client': {
                        'clientName': 'WEB',
                        'clientVersion': '2.20250312.04.00',
                    },
                },
            },
            # Headers for a "Galaxy S20 Ultra" from Chrome dev tools device
            # emulation
            'headers': {
                'User-Agent': ('Mozilla/5.0 (Linux; Android 10; SM-G981B)'
                               ' AppleWebKit/537.36 (KHTML, like Gecko)'
                               ' Chrome/80.0.3987.162 Mobile Safari/537.36'),
            },
        },
        'watch_history': {
            '_auth_required': True,
            '_auth_type': 'personal',
            '_video_id': None,
            'headers': {
                'Host': 's.youtube.com',
                'Referer': 'https://www.youtube.com/watch?v={_video_id}',
            },
            'params': {
                'referrer': 'https://accounts.google.com/',
                'ns': 'yt',
                'el': 'detailpage',
                'ver': '2',
                'fs': '0',
                'volume': '100',
                'muted': '0',
            },
        },
        '_common': {
            '_access_token': None,
            '_access_token_tv': None,
            'json': {
                'contentCheckOk': True,
                'context': {
                    'client': {
                        'gl': None,
                        'hl': None,
                        'utcOffsetMinutes': 0,
                    },
                    'request': {
                        'internalExperimentFlags': [],
                        'useSsl': True,
                    },
                },
                'racyCheckOk': True,
                'thirdParty': {},
                'user': {
                    'lockedSafetyMode': False
                },
            },
            'headers': {
                'Accept-Encoding': 'gzip, deflate',
                'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.5',
                'Authorization': 'Bearer {{0}}',
                'User-Agent': (
                    'Mozilla/5.0 (Linux; Android 10; SM-G981B)'
                    ' AppleWebKit/537.36 (KHTML, like Gecko)'
                    ' Chrome/80.0.3987.162'
                    ' Mobile Safari/537.36'
                ),
            },
            'params': {
                'key': ValueError,
                'prettyPrint': False,
            },
        },
    }

    def __init__(self,
                 context,
                 language=None,
                 region=None,
                 exc_type=None,
                 **_kwargs):
        common_client = self.CLIENTS['_common']['json']['context']['client']
        # the default language is always en_US (like YouTube on the WEB)
        language = language.replace('-', '_') if language else 'en_US'
        self._language = common_client['hl'] = language
        self._region = common_client['gl'] = region if region else 'US'

        if isinstance(exc_type, tuple):
            exc_type = (YouTubeException,) + exc_type
        elif exc_type:
            exc_type = (YouTubeException, exc_type)
        else:
            exc_type = (YouTubeException,)

        super(YouTubeRequestClient, self).__init__(
            context=context,
            exc_type=exc_type,
        )

    @classmethod
    def json_traverse(cls, json_data, path, default=None):
        if not json_data or not path:
            return default

        result = json_data
        for idx, keys in enumerate(path):
            if not isinstance(result, (dict, list)):
                return default

            if isinstance(keys, slice):
                next_key = path[idx + 1]
                if next_key is None:
                    for part in result[keys]:
                        new_result = cls.json_traverse(
                            part,
                            path[idx + 2:],
                            default=default,
                        )
                        if not new_result or new_result == default:
                            continue
                        return new_result

                if isinstance(next_key, (range, list)):
                    results_limit = len(next_key)
                    new_results = []
                    for part in result[keys]:
                        new_result = cls.json_traverse(
                            part,
                            path[idx + 2:],
                            default=default,
                        )
                        if not new_result or new_result == default:
                            continue
                        new_results.append(new_result)
                        if results_limit:
                            if results_limit == 1:
                                break
                            results_limit -= 1
                else:
                    new_results = [
                        cls.json_traverse(part, path[idx + 1:], default=default)
                        for part in result[keys]
                        if part
                    ]
                return new_results

            if not isinstance(keys, tuple):
                keys = (keys,)

            for key in keys:
                if isinstance(key, tuple):
                    new_result = cls.json_traverse(result, key, default=default)
                    if new_result:
                        result = new_result
                        break
                    continue

                try:
                    if callable(key):
                        result = key(result)
                    else:
                        result = result[key]
                except (KeyError, IndexError, TypeError):
                    continue
                break
            else:
                return default

        if result == json_data:
            return default
        return result

    @classmethod
    def build_client(cls, client_name=None, data=None):
        templates = {}

        base_client = None
        if client_name:
            base_client = cls.CLIENTS.get(client_name)
            if base_client and base_client.get('_disabled'):
                return None
        if not base_client:
            base_client = YouTubeRequestClient.CLIENTS['web']

        auth_required = base_client.get('_auth_required')
        auth_requested = base_client.get('_auth_requested')

        if data:
            base_client = merge_dicts(base_client, data)
        client = merge_dicts(cls.CLIENTS['_common'], base_client, templates)
        client['_name'] = client_name

        if auth_required:
            client['_auth_required'] = auth_required
        if auth_requested:
            client['_auth_requested'] = auth_requested

        visitor_data = client.get('_visitor_data')
        if visitor_data:
            client['json']['context']['client']['visitorData'] = visitor_data

        for values, template_id, template in templates.values():
            if template_id in values:
                values[template_id] = template.format(**client)

        has_auth = False
        try:
            params = client['params']
            auth_required = client.get('_auth_required')
            auth_requested = client.get('_auth_requested')
            auth_type = client.get('_auth_type')
            if auth_type == 'tv' and auth_requested != 'personal':
                auth_token = client.get('_access_token_tv')
                api_key = client.get('_api_key_tv')
            elif auth_type is not False:
                auth_token = client.get('_access_token')
                api_key = client.get('_api_key')
            else:
                auth_token = None
                api_key = None

            if auth_token and (auth_required or auth_requested):
                headers = client['headers']
                if 'Authorization' in headers:
                    headers = headers.copy()
                    auth_header = headers.get('Authorization') or 'Bearer {0}'
                    headers['Authorization'] = auth_header.format(auth_token)
                    client['headers'] = headers
                    has_auth = True

                if 'key' in params:
                    params = params.copy()
                    del params['key']
                    client['params'] = params
            elif auth_required:
                return None
            else:
                headers = client['headers']
                if 'Authorization' in headers:
                    headers = headers.copy()
                    del headers['Authorization']
                    client['headers'] = headers

                if 'key' in params:
                    params = params.copy()
                    if params['key'] is ValueError:
                        del params['key']
                    elif api_key:
                        params['key'] = api_key
                    client['params'] = params

        except KeyError:
            pass
        client['_has_auth'] = has_auth

        return client
