# -*- coding: utf-8 -*-
"""

    Copyright (C) 2023-2025 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from ..youtube_exceptions import YouTubeException
from ...kodion.compatibility import range_type, unescape, urljoin
from ...kodion.network import BaseRequestsClass
from ...kodion.utils.methods import merge_dicts


class YouTubeRequestClient(BaseRequestsClass):
    _API_KEYS = {
        'android': 'AIzaSyA8eiZmM1FaDVjRy-df2KTyQ_vz_yYM39w',
        'android_embedded': 'AIzaSyCjc_pVEDi4qsv5MtC2dMXzpIaDoRFLsxw',
        'ios': 'AIzaSyB-63vPrdThhKuerbB2N_l7Kwwcxj6yUAc',
        'ios_youtube_tv': 'AIzaSyAA2X8Iz20HQACliPKA2J9URIdPmS3xFUA',
        'youtube_tv': 'AIzaSyDCU8hByM-4DrUqRUYnGn-3llEO78bcxq8',
        'web': 'AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8',
    }
    _PLAYER_PARAMS = {
        'default': '8AEB',
        'testsuite': '2AMB',
    }

    BASE_URL = 'https://www.youtube.com'
    BASE_URL_MOBILE = 'https://m.youtube.com'
    V1_API_URL = BASE_URL + '/youtubei/v1/{_endpoint}'
    V3_API_URL = 'https://www.googleapis.com/youtube/v3/{_endpoint}'
    WATCH_URL = BASE_URL + '/watch?v={_video_id}'

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
            '_use_subtitles': 'optional',
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
                'cpn': None,
                'params': _PLAYER_PARAMS['default'],
            },
            'headers': {
                'Origin': BASE_URL_MOBILE,
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
                'client_version': '1.65.10',
                'android_sdk_version': '34',
                'device_codename': 'eureka',
                'device_make': 'Oculus',
                'device_model': 'Quest 3',
                'os_name': 'Android',
                'os_version': '14',
                'os_build': 'UP1A.231005.007.A1',
                'package_id': 'com.google.android.apps.youtube.vr.oculus',
            },
            '_auth_type': 'vr',
            '_use_subtitles': False,
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
                'Origin': BASE_URL,
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
        # Disabled - requires login but fails using OAuth2 authorisation
        # 4k with HDR
        # Some videos block this client, may also require embedding enabled
        # Limited subtitle availability
        # Limited audio streams
        'android_youtube_tv': {
            '_disabled': True,
            '_id': {
                'client_id': 29,
                'client_name': 'ANDROID_UNPLUGGED',
                'client_version': '9.21.0',
                'android_sdk_version': '34',
                'os_name': 'Android',
                'os_version': '14',
                'package_id': 'com.google.android.apps.youtube.unplugged',
                'platform': 'TV',
            },
            '_auth_required': True,
            '_auth_type': 'user',
            '_use_subtitles': False,
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
                'Origin': BASE_URL_MOBILE,
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
        'android_testsuite_params': {
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
            '_use_subtitles': 'optional',
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
                'cpn': None,
                'params': _PLAYER_PARAMS['testsuite'],
            },
            'headers': {
                'Origin': BASE_URL_MOBILE,
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
            '_disabled': True,
            '_id': {
                'client_id': 30,
                'client_name': 'ANDROID_TESTSUITE',
                'client_version': '1.9',
                'android_sdk_version': '32',
                'os_name': 'Android',
                'os_version': '15',
                'package_id': 'com.google.android.youtube',
                'platform': 'MOBILE',
            },
            '_auth_type': False,
            '_use_subtitles': False,
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
                'cpn': None,
                'params': _PLAYER_PARAMS['testsuite'],
            },
            'headers': {
                'Origin': BASE_URL_MOBILE,
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
        # Disabled - requires PO token
        # Requests for stream urls result in HTTP 403 errors
        # Only for videos that allow embedding
        # Limited to 720p on some videos
        'android_embedded': {
            '_disabled': True,
            '_id': {
                'client_id': 55,
                'client_name': 'ANDROID_EMBEDDED_PLAYER',
                'client_version': '20.10.38',
                'android_sdk_version': '32',
                'os_name': 'Android',
                'os_version': '15',
                'package_id': 'com.google.android.youtube',
                'platform': 'MOBILE',
            },
            '_auth_type': False,
            '_use_subtitles': 'optional',
            'json': {
                'context': {
                    'client': {
                        'clientName': '{_id[client_name]}',
                        'clientScreen': 'EMBED',
                        'clientVersion': '{_id[client_version]}',
                        'androidSdkVersion': '{_id[android_sdk_version]}',
                        'osName': '{_id[os_name]}',
                        'osVersion': '{_id[os_version]}',
                        'platform': '{_id[platform]}',
                    },
                },
                'thirdParty': {
                    'embedUrl': BASE_URL,
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
        'ios': {
            '_id': {
                'client_id': 5,
                'client_name': 'IOS',
                'client_version': '20.20.7',
                'device_make': 'Apple',
                'device_model': 'iPhone16,2',
                'os_name': 'iOS',
                'os_major': '18',
                'os_minor': '5',
                'os_patch': '0',
                'os_build': '22F76',
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
                'cpn': None,
            },
            'headers': {
                'Origin': BASE_URL_MOBILE,
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
        'ios_testsuite_params': {
            '_id': {
                'client_id': 5,
                'client_name': 'IOS',
                'client_version': '20.20.7',
                'device_make': 'Apple',
                'device_model': 'iPhone16,2',
                'os_name': 'iOS',
                'os_major': '18',
                'os_minor': '5',
                'os_patch': '0',
                'os_build': '22F76',
                'package_id': 'com.google.ios.youtube',
                'platform': 'MOBILE',
            },
            '_auth_type': False,
            '_use_subtitles': 'optional',
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
                'cpn': None,
                'params': _PLAYER_PARAMS['testsuite'],
            },
            'headers': {
                'Origin': BASE_URL_MOBILE,
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
        # Disabled - requires login but fails using OAuth2 authorisation
        'ios_youtube_tv': {
            '_disabled': True,
            '_id': {
                'client_id': 33,
                'client_name': 'IOS_UNPLUGGED',
                'client_version': '9.21',
                'device_make': 'Apple',
                'device_model': 'iPhone16,2',
                'os_name': 'iOS',
                'os_major': '18',
                'os_minor': '5',
                'os_patch': '0',
                'os_build': '22F76',
                'package_id': 'com.google.ios.youtubeunplugged',
                'platform': 'MOBILE',
            },
            '_auth_required': True,
            '_auth_type': 'user',
            '_use_subtitles': False,
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
                'Origin': BASE_URL_MOBILE,
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
        'v1': {
            '_id': {
                'client_id': 1,
                'client_name': 'WEB',
                'client_version': '2.20250925.01.00',
            },
            '_auth_type': False,
            'url': V1_API_URL,
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
            '_auth_type': 'user',
            'url': V3_API_URL,
            'method': None,
            'params': {
                'key': None,
            },
        },
        'tv': {
            '_id': {
                'browser_name': 'SamsungBrowser',
                'browser_version': '9.2',
                'client_id': 7,
                'client_name': 'TVHTML5',
                'client_version': '7.20250923.13.00',
                'device_make': 'Samsung',
                'device_model': 'SmartTV',
                'os_name': 'Tizen',
                'os_major': '4',
                'os_minor': '0',
                'os_patch': '0',
                'os_build': '2',
                'platform': 'TV',
            },
            '_auth_type': 'tv',
            '_auth_user_agent': (
                'Mozilla/5.0'
                ' (ChromiumStylePlatform)'
                ' Cobalt/25.lts.30.1034943-gold (unlike Gecko)'
                ' Unknown_TV_Unknown_0/Unknown (Unknown, Unknown)'
            ),
            '_use_subtitles': 'optional',
            'url': V1_API_URL,
            'method': None,
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
                    'Mozilla/5.0'
                    ' (ChromiumStylePlatform)'
                    ' Cobalt/Version'
                ),
                'X-YouTube-Client-Name': '{_id[client_id]}',
                'X-YouTube-Client-Version': '{_id[client_version]}',
            },
        },
        # Used to requests captions for clients that don't provide them
        # Requires handling of nsig to overcome throttling (TODO)
        'tv_embed': {
            '_id': {
                'client_id': 85,
                'client_name': 'TVHTML5_SIMPLY_EMBEDDED_PLAYER',
                'client_version': '2.0',
            },
            '_auth_type': 'tv',
            '_auth_user_agent': (
                'Mozilla/5.0'
                ' (ChromiumStylePlatform)'
                ' Cobalt/25.lts.30.1034943-gold (unlike Gecko)'
                ' Unknown_TV_Unknown_0/Unknown (Unknown, Unknown)'
            ),
            '_use_subtitles': True,
            'url': V1_API_URL,
            'method': None,
            'json': {
                'context': {
                    'client': {
                        'clientName': '{_id[client_name]}',
                        'clientVersion': '{_id[client_version]}',
                    },
                },
                'thirdParty': {
                    'embedUrl': 'https://www.google.com/',
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
        'tv_unplugged': {
            '_id': {
                'client_id': 65,
                'client_name': 'TVHTML5_UNPLUGGED',
                'client_version': '6.36',
            },
            '_auth_type': 'user',
            '_auth_user_agent': (
                'Mozilla/5.0'
                ' (ChromiumStylePlatform)'
                ' Cobalt/25.lts.30.1034943-gold (unlike Gecko)'
                ' Unknown_TV_Unknown_0/Unknown (Unknown, Unknown)'
            ),
            '_use_subtitles': True,
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
            '_auth_type': False,
            'url': V1_API_URL,
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
            '_id': {
                'client_id': 1,
                'client_name': 'WEB',
                'client_version': '2.20250925.01.00',
            },
            '_auth_type': False,
            'json': {
                'context': {
                    'client': {
                        'clientName': '{_id[client_name]}',
                        'clientVersion': '{_id[client_version]}',
                    },
                },
            },
            'headers': {
                # UA for a "Galaxy S20 Ultra" from Chrome dev tools device
                # emulation
                'User-Agent': (
                    'Mozilla/5.0 (Linux; Android 10; SM-G981B)'
                    ' AppleWebKit/537.36 (KHTML, like Gecko)'
                    ' Chrome/140.0.0.0'
                    ' Mobile Safari/537.36'
                ),
                'X-YouTube-Client-Name': '{_id[client_id]}',
                'X-YouTube-Client-Version': '{_id[client_version]}',
            },
        },
        'watch_history': {
            '_auth_required': True,
            '_auth_type': 'user',
            '_video_id': None,
            'headers': {
                'Host': 's.youtube.com',
                'Referer': WATCH_URL,
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
        'generate_204': {
            'url': BASE_URL + '/generate_204',
            'method': 'HEAD',
            'headers': {
                'Accept-Encoding': 'gzip, deflate',
                'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.5',
                'User-Agent': (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
                    ' AppleWebKit/537.36 (KHTML, like Gecko)'
                    ' Chrome/140.0.0.0'
                    ' Safari/537.36'
                ),
            },
            'cache': False,
        },
        '_common': {
            '_access_tokens': {
                'dev': None,
                'tv': None,
                'user': None,
                'vr': None,
            },
            '_api_keys': {
                'dev': None,
                'tv': None,
                'user': None,
                'vr': None,
            },
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
                'Authorization': None,
                'User-Agent': (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
                    ' AppleWebKit/537.36 (KHTML, like Gecko)'
                    ' Chrome/140.0.0.0'
                    ' Safari/537.36'
                ),
            },
            'params': {
                'key': ValueError,
                'prettyPrint': False,
            },
        },
    }

    _language = 'en_US'
    _region = 'US'

    def __init__(self, language='en_US', region='US', exc_type=None, **kwargs):
        super(YouTubeRequestClient, self).__init__(
            exc_type=(
                (YouTubeException,) + exc_type
                if isinstance(exc_type, tuple) else
                (YouTubeException, exc_type)
                if exc_type else
                (YouTubeException,)
            ),
            **kwargs)
        YouTubeRequestClient.init(language=language, region=region)

    @classmethod
    def init(cls,
             language='en_US',
             region='US',
             **_kwargs):
        common_client = cls.CLIENTS['_common']['json']['context']['client']
        # the default language is always en_US (like YouTube on the WEB)
        common_client['hl'] = 'en_US'
        cls._language = language.replace('-', '_')
        cls._region = common_client['gl'] = region

    def reinit(self, **kwargs):
        super(YouTubeRequestClient, self).reinit(**kwargs)

    def get_language(self):
        return self._language

    def get_region(self):
        return self._region

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
                parts = result[keys]
                if next_key is None:
                    new_path = path[idx + 2:]
                    for part in parts:
                        new_result = cls.json_traverse(part, new_path, default)
                        if not new_result or new_result == default:
                            continue
                        return new_result

                if isinstance(next_key, range_type):
                    results_limit = len(next_key)
                    new_path = path[idx + 2:]
                    new_results = []
                    for part in parts:
                        new_result = cls.json_traverse(part, new_path, default)
                        if not new_result or new_result == default:
                            continue
                        new_results.append(new_result)
                        if results_limit:
                            if results_limit == 1:
                                break
                            results_limit -= 1
                else:
                    new_path = path[idx + 1:]
                    new_results = [
                        cls.json_traverse(part, new_path, default)
                        for part in parts
                        if part
                    ]
                return new_results

            if not isinstance(keys, tuple):
                keys = (keys,)

            for key in keys:
                if isinstance(key, tuple):
                    new_result = cls.json_traverse(result, key, default)
                    if new_result:
                        result = new_result
                        break
                    continue

                try:
                    if callable(key):
                        result = key(result)
                    elif isinstance(key, dict):
                        result = next(
                            param for param in result
                            if param.get(key['name']) in key['match']
                        )[key['out']]
                    else:
                        result = result[key]
                except (KeyError, IndexError, StopIteration, TypeError):
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
            if not base_client or base_client.get('_disabled'):
                return None
        if not base_client:
            base_client = YouTubeRequestClient.CLIENTS['web']

        auth_required = base_client.get('_auth_required')
        auth_requested = base_client.get('_auth_requested')
        auth_type = base_client.get('_auth_type')

        if data:
            base_client = merge_dicts(base_client, data)
        client = merge_dicts(cls.CLIENTS['_common'], base_client, templates)
        client['_name'] = client_name

        if auth_required is not None:
            client['_auth_required'] = auth_required
        if auth_requested is not None:
            client['_auth_requested'] = auth_requested
        if auth_type is not None:
            client['_auth_type'] = auth_type

        headers = client.get('headers')
        client_json = client.get('json')
        if client_json:
            if 'cpn' in client_json:
                cpn = client.get('_cpn')
                if cpn:
                    client_json['cpn'] = cpn
                else:
                    client_json = client_json.copy()
                    del client_json['cpn']
                    client['json'] = client_json

            client_config = cls.json_traverse(
                client_json,
                ('context', 'client'),
            )
            playback_context = cls.json_traverse(
                client_json,
                ('playbackContext', 'contentPlaybackContext'),
            )
        else:
            client_config = None
            playback_context = None

        visitor_data = client.get('_visitor_data')
        if visitor_data:
            if client_config is not None:
                client_config['visitorData'] = visitor_data
            if headers is not None:
                headers['X-Goog-Visitor-Id'] = visitor_data

        for values, template_id, template in templates.values():
            if template_id in values:
                values[template_id] = template.format(**client)

        has_auth = None
        try:
            params = client['params']
            auth_required = client.get('_auth_required')
            auth_requested = client.get('_auth_requested')
            auth_type = client.get('_auth_type')
            if auth_type:
                auth_token = client.get('_access_tokens', {}).get(auth_type)
                api_key = client.get('_api_keys', {}).get(auth_type)
            else:
                auth_token = None
                api_key = None

            if auth_token and (auth_required or auth_requested):
                if headers is not None and 'Authorization' in headers:
                    headers = headers.copy()
                    auth_header = headers.get('Authorization') or 'Bearer {0}'
                    headers['Authorization'] = auth_header.format(auth_token)

                    auth_user_agent = client.get('_auth_user_agent')
                    if auth_user_agent:
                        headers['User-Agent'] = auth_user_agent

                    client['headers'] = headers
                    has_auth = auth_type

                if 'key' in params:
                    params = params.copy()
                    del params['key']
                    client['params'] = params
            elif auth_required and auth_required != 'ignore_fail':
                return None
            else:
                if headers is not None and 'Authorization' in headers:
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

    def internet_available(self, notify=True):
        response = self.request(**self.CLIENTS['generate_204'])
        if response is not None:
            with response:
                if response.status_code == 204:
                    return True
        if notify:
            self._context.get_ui().show_notification(
                self._context.localize('internet.connection.required')
            )
        return False

    @classmethod
    def _normalize_url(cls, url):
        if not url:
            url = ''
        elif url.startswith(('http://', 'https://')):
            pass
        elif url.startswith('//'):
            url = urljoin('https:', url)
        elif url.startswith('/'):
            url = urljoin(cls.BASE_URL, url)
        return url

    @classmethod
    def _unescape(cls, text):
        try:
            text = unescape(text)
        except Exception:
            cls.log.error(('Failed', 'Text: %r'), text)
        return text
