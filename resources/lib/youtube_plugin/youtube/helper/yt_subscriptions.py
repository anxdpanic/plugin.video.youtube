# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2025 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from ..helper import v3
from ...kodion import KodionException
from ...kodion.constants import CHANNEL_ID, CONTENT, SUBSCRIPTION_ID
from ...kodion.items import UriItem


def _process_list(provider, context, client):
    json_data = client.get_subscription(
        'mine', page_token=context.get_param('page_token', '')
    )
    if not json_data:
        return []

    result = v3.response_to_items(provider, context, json_data)
    options = {
        provider.CONTENT_TYPE: {
            'content_type': CONTENT.LIST_CONTENT,
            'sub_type': None,
            'category_label': None,
        },
    }
    return result, options


def _process_add(_provider, context, client):
    ui = context.get_ui()
    li_subscription_id = ui.get_listitem_property(SUBSCRIPTION_ID)

    subscription_id = context.get_param(SUBSCRIPTION_ID)
    if (not subscription_id
            and li_subscription_id
            and li_subscription_id.lower().startswith('uc')):
        subscription_id = li_subscription_id

    if not subscription_id:
        return False

    json_data = client.subscribe(subscription_id)
    if not json_data:
        return False

    ui.show_notification(
        context.localize('subscribed.to.channel'),
        time_ms=2500,
        audible=False,
    )
    return True


def _process_remove(provider, context, client):
    ui = context.get_ui()
    li_subscription_id = ui.get_listitem_property(SUBSCRIPTION_ID)
    li_channel_id = ui.get_listitem_property(CHANNEL_ID)

    subscription_id = context.get_param(SUBSCRIPTION_ID)
    if not subscription_id and li_subscription_id:
        subscription_id = li_subscription_id

    channel_id = context.get_param(CHANNEL_ID)
    if not channel_id and li_channel_id:
        channel_id = li_channel_id

    if subscription_id:
        success = client.unsubscribe(subscription_id)
    elif channel_id:
        success = client.unsubscribe_channel(channel_id)
    else:
        success = False

    if not success:
        return False, None

    ui.show_notification(
        context.localize('unsubscribed.from.channel'),
        time_ms=2500,
        audible=False,
    )
    return True, {provider.FORCE_REFRESH: True}


def process(provider, context, re_match):
    command = re_match.group('command')

    # we need a login
    client = provider.get_client(context)
    if not client.logged_in:
        return UriItem(context.create_uri(('sign', 'in')))

    if command == 'list':
        return _process_list(provider, context, client)

    if command == 'add':
        return _process_add(provider, context, client)

    if command == 'remove':
        return _process_remove(provider, context, client)

    raise KodionException('Unknown subscriptions command: %s' % command)
