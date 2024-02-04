# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from ..helper import v3
from ...kodion import KodionException
from ...kodion.items import UriItem


def _process_list(provider, context):
    result = []

    page_token = context.get_param('page_token', '')
    # no caching
    json_data = provider.get_client(context).get_subscription('mine', page_token=page_token)
    if not json_data:
        return []
    result.extend(v3.response_to_items(provider, context, json_data))

    return result


def _process_add(provider, context):
    listitem_subscription_id = context.get_listitem_detail('subscription_id')

    subscription_id = context.get_param('subscription_id', '')
    if (not subscription_id and listitem_subscription_id
            and listitem_subscription_id.lower().startswith('uc')):
        subscription_id = listitem_subscription_id

    if subscription_id:
        json_data = provider.get_client(context).subscribe(subscription_id)
        if not json_data:
            return False

        context.get_ui().show_notification(
            context.localize('subscribed.to.channel'),
            time_ms=2500,
            audible=False
        )

        return True

    return False


def _process_remove(provider, context):
    listitem_subscription_id = context.get_listitem_detail('channel_subscription_id')
    listitem_channel_id = context.get_listitem_detail('channel_id')

    subscription_id = context.get_param('subscription_id', '')
    if not subscription_id and listitem_subscription_id:
        subscription_id = listitem_subscription_id

    channel_id = context.get_param('channel_id', '')
    if not channel_id and listitem_channel_id:
        channel_id = listitem_channel_id

    if subscription_id:
        success = provider.get_client(context).unsubscribe(subscription_id)
    elif channel_id:
        success = provider.get_client(context).unsubscribe_channel(channel_id)
    else:
        success = False

    if not success:
        return False

    context.get_ui().refresh_container()
    context.get_ui().show_notification(
        context.localize('unsubscribed.from.channel'),
        time_ms=2500,
        audible=False
    )
    return True


def process(method, provider, context):
    result = []

    # we need a login
    _ = provider.get_client(context)
    if not provider.is_logged_in():
        return UriItem(context.create_uri(('sign', 'in')))

    if method == 'list':
        result.extend(_process_list(provider, context))
    elif method == 'add':
        return _process_add(provider, context)
    elif method == 'remove':
        return _process_remove(provider, context)
    else:
        raise KodionException("Unknown subscriptions method '%s'" % method)

    return result
