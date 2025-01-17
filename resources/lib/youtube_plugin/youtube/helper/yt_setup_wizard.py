# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import os

from ...kodion.compatibility import urlencode, xbmcvfs
from ...kodion.constants import ADDON_ID, DATA_PATH, WAIT_END_FLAG
from ...kodion.network import httpd_status, get_listen_addresses
from ...kodion.sql_store import PlaybackHistory, SearchHistory
from ...kodion.utils import to_unicode
from ...kodion.utils.datetime_parser import strptime


def process_language(provider, context, step, steps):
    localize = context.localize
    ui = context.get_ui()

    step += 1
    if ui.on_yes_no_input(
            '{youtube} - {setup_wizard} ({step}/{steps})'.format(
                youtube=localize('youtube'),
                setup_wizard=localize('setup_wizard'),
                step=step,
                steps=steps,
            ),
            (localize('setup_wizard.prompt')
             % localize('setup_wizard.prompt.locale'))
    ):
        context.execute(
            'RunScript({addon_id},config/language_region)'.format(
                addon_id=ADDON_ID,
            ),
            wait_for=WAIT_END_FLAG,
        )
        context.get_settings(refresh=True)
    return step


def process_geo_location(context, step, steps, **_kwargs):
    localize = context.localize

    step += 1
    if context.get_ui().on_yes_no_input(
            '{youtube} - {setup_wizard} ({step}/{steps})'.format(
                youtube=localize('youtube'),
                setup_wizard=localize('setup_wizard'),
                step=step,
                steps=steps,
            ),
            (localize('setup_wizard.prompt')
             % localize('setup_wizard.prompt.my_location'))
    ):
        context.execute(
            'RunScript({addon_id},config/geo_location)'.format(
                addon_id=ADDON_ID,
            ),
            wait_for=WAIT_END_FLAG,
        )
        context.get_settings(refresh=True)
    return step


def process_default_settings(context, step, steps, **_kwargs):
    localize = context.localize
    settings = context.get_settings()
    ui = context.get_ui()

    step += 1
    if ui.on_yes_no_input(
            '{youtube} - {setup_wizard} ({step}/{steps})'.format(
                youtube=localize('youtube'),
                setup_wizard=localize('setup_wizard'),
                step=step,
                steps=steps,
            ),
            (localize('setup_wizard.prompt')
             % localize('setup_wizard.prompt.settings.defaults'))
    ):
        settings.use_isa(True)
        settings.use_mpd_videos(True)
        settings.stream_select(4 if settings.ask_for_video_quality() else 3)
        settings.set_subtitle_download(False)
        if context.get_system_version().compatible(21):
            settings.live_stream_type(3)
        else:
            settings.live_stream_type(1)
        if not xbmcvfs.exists('special://profile/playercorefactory.xml'):
            settings.support_alternative_player(False)
            settings.default_player_web_urls(False)
            settings.alternative_player_web_urls(False)
            settings.alternative_player_mpd(False)
        if settings.cache_size() < 20:
            settings.cache_size(20)
        if context.get_infobool('System.Platform.Linux'):
            settings.httpd_sleep_allowed(False)
        with ui.create_progress_dialog(
                heading=localize('httpd'),
                message=localize('httpd.connect.wait'),
                total=1,
                background=False,
        ) as progress_dialog:
            progress_dialog.update()
            if settings.httpd_listen() == '0.0.0.0':
                settings.httpd_listen('127.0.0.1')
            if not httpd_status(context):
                port = settings.httpd_port()
                addresses = get_listen_addresses()
                progress_dialog.grow_total(delta=len(addresses))
                for address in addresses:
                    progress_dialog.update()
                    if httpd_status(context, (address, port)):
                        settings.httpd_listen(address)
                        break
                    context.sleep(5)
                else:
                    ui.show_notification(
                        localize('httpd.connect.failed'),
                        header=localize('httpd'),
                    )
                    settings.httpd_listen('0.0.0.0')
    return step


def process_list_detail_settings(context, step, steps, **_kwargs):
    localize = context.localize
    settings = context.get_settings()

    step += 1
    if context.get_ui().on_yes_no_input(
            '{youtube} - {setup_wizard} ({step}/{steps})'.format(
                youtube=localize('youtube'),
                setup_wizard=localize('setup_wizard'),
                step=step,
                steps=steps,
            ),
            (localize('setup_wizard.prompt')
             % localize('setup_wizard.prompt.settings.list_details'))
    ):
        settings.show_detailed_description(False)
        settings.show_detailed_labels(False)
    else:
        settings.show_detailed_description(True)
        settings.show_detailed_labels(True)
    return step


def process_performance_settings(context, step, steps, **_kwargs):
    localize = context.localize
    settings = context.get_settings()
    ui = context.get_ui()

    step += 1
    if ui.on_yes_no_input(
            '{youtube} - {setup_wizard} ({step}/{steps})'.format(
                youtube=localize('youtube'),
                setup_wizard=localize('setup_wizard'),
                step=step,
                steps=steps,
            ),
            (localize('setup_wizard.prompt')
             % localize('setup_wizard.prompt.settings.performance'))
    ):
        device_types = {
            '720p30': {
                'max_resolution': 3,  # 720p
                'stream_features': ('avc1', 'mp4a', 'filter', 'alt_sort'),
                'num_items': 10,
            },
            '1080p30_avc': {
                'max_resolution': 4,  # 1080p
                'stream_features': ('avc1', 'vorbis', 'mp4a', 'filter', 'alt_sort'),
                'num_items': 10,
            },
            '1080p30': {
                'max_resolution': 4,  # 1080p
                'stream_features': ('avc1', 'vp9', 'vorbis', 'mp4a', 'ssa', 'ac-3', 'ec-3', 'dts', 'filter', 'alt_sort'),
                'num_items': 20,
            },
            '1080p60': {
                'max_resolution': 4,  # 1080p
                'stream_features': ('avc1', 'vp9', 'hfr', 'vorbis', 'mp4a', 'ssa', 'ac-3', 'ec-3', 'dts', 'filter'),
                'num_items': 30,
            },
            '4k30': {
                'max_resolution': 6,  # 4k
                'stream_features': ('avc1', 'vp9', 'hdr', 'hfr', 'no_hfr_max', 'vorbis', 'mp4a', 'ssa', 'ac-3', 'ec-3', 'dts', 'filter'),
                'num_items': 50,
            },
            '4k60': {
                'max_resolution': 6,  # 4k
                'stream_features': ('avc1', 'vp9', 'hdr', 'hfr', 'vorbis', 'mp4a', 'ssa', 'ac-3', 'ec-3', 'dts', 'filter'),
                'num_items': 50,
            },
            '4k60_av1': {
                'max_resolution': 6,  # 4k
                'stream_features': ('avc1', 'vp9', 'av01', 'hdr', 'hfr', 'vorbis', 'mp4a', 'ssa', 'ac-3', 'ec-3', 'dts', 'filter'),
                'num_items': 50,
            },
            'max': {
                'max_resolution': 7,  # 8k
                'stream_features': ('avc1', 'vp9', 'av01', 'hdr', 'hfr', 'vorbis', 'mp4a', 'ssa', 'ac-3', 'ec-3', 'dts', 'filter'),
                'num_items': 50,
            },
        }
        items = [
            localize('setup_wizard.capabilities.' + item).split(' | ') + [item]
            for item in device_types
        ]
        device_type = ui.on_select(
            localize('setup_wizard.capabilities'),
            items=items,
            use_details=True,
        )
        if device_type == -1:
            return step

        device_type = device_types[device_type]
        if 'settings' in device_type:
            for setting in device_type['settings']:
                setting[0](*setting[1])
        settings.mpd_video_qualities(device_type['max_resolution'])
        if not settings.use_mpd_videos():
            settings.fixed_video_quality(device_type['max_resolution'])
        settings.stream_features(device_type['stream_features'])
        settings.items_per_page(device_type['num_items'])
    return step


def process_subtitles(context, step, steps, **_kwargs):
    localize = context.localize

    step += 1
    if context.get_ui().on_yes_no_input(
            '{youtube} - {setup_wizard} ({step}/{steps})'.format(
                youtube=localize('youtube'),
                setup_wizard=localize('setup_wizard'),
                step=step,
                steps=steps,
            ),
            (localize('setup_wizard.prompt')
             % localize('setup_wizard.prompt.subtitles'))
    ):
        context.execute(
            'RunScript({addon_id},config/subtitles)'.format(
                addon_id=ADDON_ID,
            ),
            wait_for=WAIT_END_FLAG,
        )
        context.get_settings(refresh=True)
    return step


def process_old_search_db(context, step, steps, **_kwargs):
    localize = context.localize
    ui = context.get_ui()

    search_db_path = (
        xbmcvfs.translatePath(DATA_PATH),
        'kodion',
        'search.sqlite'
    )
    search_db_path_str = os.path.join(*search_db_path)
    step += 1
    if xbmcvfs.exists(search_db_path_str) and ui.on_yes_no_input(
            '{youtube} - {setup_wizard} ({step}/{steps})'.format(
                youtube=localize('youtube'),
                setup_wizard=localize('setup_wizard'),
                step=step,
                steps=steps,
            ),
            localize('setup_wizard.prompt.import_search_history'),
    ):
        def _convert_old_search_item(value, item):
            return {
                'text': to_unicode(value),
                'timestamp': strptime(item[1]).timestamp(),
            }

        search_history = context.get_search_history()
        old_search_db = SearchHistory(
            search_db_path,
            migrate='storage',
        )
        items = old_search_db.get_items(process=_convert_old_search_item)
        for search in items:
            search_history.update_item(search['text'], search['timestamp'])

        ui.show_notification(localize('succeeded'))
        context.execute(
            'RunScript({addon},maintenance/{action}?{query})'.format(
                addon=ADDON_ID,
                action='delete',
                query=urlencode({
                    'target': 'other_file',
                    'path': search_db_path_str,
                }),
            ),
            wait_for=WAIT_END_FLAG,
        )
    return step


def process_old_history_db(context, step, steps, **_kwargs):
    localize = context.localize
    ui = context.get_ui()

    history_db_path = (
        xbmcvfs.translatePath(DATA_PATH),
        'playback',
        context.get_access_manager().get_current_user_id() + '.sqlite',
    )
    history_db_path_str = os.path.join(*history_db_path)
    step += 1
    if xbmcvfs.exists(history_db_path_str) and ui.on_yes_no_input(
            '{youtube} - {setup_wizard} ({step}/{steps})'.format(
                youtube=localize('youtube'),
                setup_wizard=localize('setup_wizard'),
                step=step,
                steps=steps,
            ),
            localize('setup_wizard.prompt.import_playback_history'),
    ):
        def _convert_old_history_item(value, item):
            values = value.split(',')
            return {
                'play_count': int(values[0]),
                'total_time': float(values[1]),
                'played_time': float(values[2]),
                'played_percent': int(values[3]),
                'timestamp': strptime(item[1]).timestamp(),
            }

        playback_history = context.get_playback_history()
        old_history_db = PlaybackHistory(
            history_db_path,
            migrate='storage',
        )
        items = old_history_db.get_items(process=_convert_old_history_item)
        for video_id, history in items.items():
            timestamp = history.pop('timestamp', None)
            playback_history.update_item(video_id, history, timestamp)

        ui.show_notification(localize('succeeded'))
        context.execute(
            'RunScript({addon},maintenance/{action}?{query})'.format(
                addon=ADDON_ID,
                action='delete',
                query=urlencode({
                    'target': 'other_file',
                    'path': history_db_path_str,
                }),
            ),
            wait_for=WAIT_END_FLAG,
        )
    return step


def process_refresh_settings(context, step, steps, **_kwargs):
    localize = context.localize

    step += 1
    if context.get_ui().on_yes_no_input(
            '{youtube} - {setup_wizard} ({step}/{steps})'.format(
                youtube=localize('youtube'),
                setup_wizard=localize('setup_wizard'),
                step=step,
                steps=steps,
            ),
            localize('setup_wizard.prompt.settings.refresh'),
    ):
        context.execute(
            'RunScript({addon},maintenance/{action}?{query})'.format(
                addon=ADDON_ID,
                action='refresh',
                query='target=settings_xml',
            ),
            wait_for=WAIT_END_FLAG,
        )
    return step
