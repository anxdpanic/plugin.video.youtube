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
        'smart_tv': 'AIzaSyDCU8hByM-4DrUqRUYnGn-3llEO78bcxq8',
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
            '_id': 3,
            '_disabled': True,
            '_query_subtitles': 'optional',
            'json': {
                'context': {
                    'client': {
                        'clientName': 'ANDROID',
                        'clientVersion': '19.44.38',
                        'androidSdkVersion': '30',
                        'osName': 'Android',
                        'osVersion': '11',
                        'platform': 'MOBILE',
                    },
                },
            },
            'headers': {
                'User-Agent': ('com.google.android.youtube/'
                               '{json[context][client][clientVersion]}'
                               ' (Linux; U; {json[context][client][osName]}'
                               ' {json[context][client][osVersion]}) gzip'),
                'X-YouTube-Client-Name': '{_id}',
                'X-YouTube-Client-Version': '{json[context][client][clientVersion]}',
            },
        },
        'android_vr': {
            '_id': 28,
            '_query_subtitles': False,
            '_os': {
                'deviceCodename': 'eureka',
                'build': 'SQ3A.220605.009.A1',
            },
            'json': {
                'context': {
                    'client': {
                        'clientName': 'ANDROID_VR',
                        'clientVersion': '1.61.48',
                        'deviceMake': 'Oculus',
                        'deviceModel': 'Quest 3',
                        'osName': 'Android',
                        'osVersion': '12L',
                        'androidSdkVersion': '32',
                    }
                }
            },
            'headers': {
                'User-Agent': ('com.google.android.apps.youtube.vr.oculus/'
                               '{json[context][client][clientVersion]}'
                               ' (Linux; U; {json[context][client][osName]}'
                               ' {json[context][client][osVersion]};'
                               ' {_os[deviceCodename]}-user Build/{_os[build]}) gzip'),
                'X-YouTube-Client-Name': '{_id}',
                'X-YouTube-Client-Version': '{json[context][client][clientVersion]}',
            },
        },
        # 4k with HDR
        # Some videos block this client, may also require embedding enabled
        # Limited subtitle availability
        # Limited audio streams
        'android_youtube_tv': {
            '_id': 29,
            '_auth_required': True,
            '_auth_type': 'personal',
            '_query_subtitles': True,
            'json': {
                'context': {
                    'client': {
                        'clientName': 'ANDROID_UNPLUGGED',
                        'clientVersion': '9.03.2',
                        'androidSdkVersion': '32',
                        'osName': 'Android',
                        'osVersion': '12',
                        'platform': 'TV',
                    },
                },
            },
            'headers': {
                'User-Agent': ('com.google.android.apps.youtube.unplugged/'
                               '{json[context][client][clientVersion]}'
                               ' (Linux; U; {json[context][client][osName]}'
                               ' {json[context][client][osVersion]}) gzip'),
                'X-YouTube-Client-Name': '{_id}',
                'X-YouTube-Client-Version': '{json[context][client][clientVersion]}',
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
                'User-Agent': ('com.google.android.youtube/'
                               '{json[context][client][clientVersion]}'
                               ' (Linux; U; {json[context][client][osName]}'
                               ' {json[context][client][osVersion]}) gzip'),
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
                'User-Agent': ('com.google.android.youtube/'
                               '{json[context][client][clientVersion]}'
                               ' (Linux; U; {json[context][client][osName]}'
                               ' {json[context][client][osVersion]}) gzip'),
                'X-YouTube-Client-Name': '{_id}',
                'X-YouTube-Client-Version': '{json[context][client][clientVersion]}',
            },
        },
        'ios': {
            '_id': 5,
            '_auth_type': False,
            '_os': {
                'major': '18',
                'minor': '2',
                'patch': '1',
                'build': '22C161',
            },
            'json': {
                'context': {
                    'client': {
                        'clientName': 'IOS',
                        'clientVersion': '20.03.02',
                        'deviceMake': 'Apple',
                        'deviceModel': 'iPhone16,2',
                        'osName': 'iOS',
                        'osVersion': '{_os[major]}.{_os[minor]}.{_os[patch]}.{_os[build]}',
                        'platform': 'MOBILE',
                    },
                },
            },
            'headers': {
                'User-Agent': ('com.google.ios.youtube/'
                               '{json[context][client][clientVersion]}'
                               ' ({json[context][client][deviceModel]};'
                               ' U; CPU {json[context][client][osName]}'
                               ' {_os[major]}_{_os[minor]}_{_os[patch]}'
                               ' like Mac OS X)'),
                'X-YouTube-Client-Name': '{_id}',
                'X-YouTube-Client-Version': '{json[context][client][clientVersion]}',
            },
        },
        'ios_youtube_tv': {
            '_id': 33,
            '_auth_required': True,
            '_auth_type': 'personal',
            '_os': {
                'major': '18',
                'minor': '2',
                'patch': '1',
                'build': '22C161',
            },
            'json': {
                'context': {
                    'client': {
                        'clientName': 'IOS_UNPLUGGED',
                        'clientVersion': '9.04',
                        'deviceMake': 'Apple',
                        'deviceModel': 'iPhone16,2',
                        'osName': 'iOS',
                        'osVersion': '{_os[major]}.{_os[minor]}.{_os[patch]}.{_os[build]}',
                        'platform': 'MOBILE',
                    },
                },
            },
            'headers': {
                'User-Agent': ('com.google.ios.youtubeunplugged/'
                               '{json[context][client][clientVersion]}'
                               ' ({json[context][client][deviceModel]};'
                               ' U; CPU {json[context][client][osName]}'
                               ' {_os[major]}_{_os[minor]}_{_os[patch]}'
                               ' like Mac OS X)'),
                'X-YouTube-Client-Name': '{_id}',
                'X-YouTube-Client-Version': '{json[context][client][clientVersion]}',
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
        # Used for misc api requests by default
        # Requires handling of nsig to overcome throttling (TODO)
        'web': {
            '_id': 1,
            'json': {
                'context': {
                    'client': {
                        'clientName': 'WEB',
                        'clientVersion': '2.20240726.00.00',
                    },
                },
            },
            # Headers for a "Galaxy S20 Ultra" from Chrome dev tools device
            # emulation
            'headers': {
                'User-Agent': ('Mozilla/5.0 (Linux; Android 10; SM-G981B)'
                               ' AppleWebKit/537.36 (KHTML, like Gecko)'
                               ' Chrome/80.0.3987.162 Mobile Safari/537.36'),
                'Referer': 'https://www.youtube.com/watch?v={json[videoId]}'
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
                    },
                    'request': {
                        'internalExperimentFlags': [],
                        'useSsl': True,
                    },
                },
                'playbackContext': {
                    'contentPlaybackContext': {
                        'html5Preference': 'HTML5_PREF_WANTS',
                    },
                },
                'racyCheckOk': True,
                'thirdParty': {},
                'user': {
                    'lockedSafetyMode': False
                },
                'videoId': None,
            },
            'headers': {
                'Accept-Encoding': 'gzip, deflate',
                'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.5',
                'Authorization': 'Bearer {{0}}',
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
            if not isinstance(result, (dict, list, tuple)):
                return default

            if isinstance(keys, slice):
                return [
                    cls.json_traverse(part, path[idx + 1:], default=default)
                    for part in result[keys]
                    if part
                ]

            if not isinstance(keys, (list, tuple)):
                keys = [keys]

            for key in keys:
                if isinstance(key, (list, tuple)):
                    new_result = cls.json_traverse(result, key, default=default)
                    if new_result:
                        result = new_result
                        break
                    continue

                try:
                    result = result[key]
                except (KeyError, IndexError):
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
