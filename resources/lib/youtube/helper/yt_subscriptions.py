from resources.lib.kodion.items import UriItem

__author__ = 'bromix'

from resources.lib import kodion
from resources.lib.youtube.helper import v3


def _process_list(provider, context, re_match):
    result = []

    page_token = context.get_param('page_token', '')
    # no caching
    json_data = provider.get_client(context).get_subscription('mine', page_token=page_token)
    result.extend(v3.response_to_items(provider, context, json_data))

    return result


def _process_add(provider, context, re_match):
    subscription_id = context.get_param('subscription_id', '')
    if subscription_id:
        json_data = provider.get_client(context).subscribe(subscription_id)
        if not v3.handle_error(provider, context, json_data):
            return False
    return True


def _process_remove(provider, context, re_match):
    subscription_id = context.get_param('subscription_id', '')
    if subscription_id:
        json_data = provider.get_client(context).unsubscribe(subscription_id)
        if not v3.handle_error(provider, context, json_data):
            return False

        context.get_ui().refresh_container()
        pass
    return True


def process(method, provider, context, re_match):
    result = []

    # we need a login
    client = provider.get_client(context)
    if not provider.is_logged_in():
        return UriItem(context.create_uri(['sign', 'in']))

    if method == 'list':
        result.extend(_process_list(provider, context, re_match))
        pass
    elif method == 'add':
        return _process_add(provider, context, re_match)
    elif method == 'remove':
        return _process_remove(provider, context, re_match)
    else:
        raise kodion.KodionException("Unknown subscriptions method '%s'" % method)

    return result
