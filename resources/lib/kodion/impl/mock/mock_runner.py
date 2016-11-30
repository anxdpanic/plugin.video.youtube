__author__ = 'bromix'

from ..abstract_provider_runner import AbstractProviderRunner
from ... import constants
from ...items import *
from ...logging import *
from ...exceptions import KodionException


class MockRunner(AbstractProviderRunner):
    def __init__(self):
        AbstractProviderRunner.__init__(self)
        pass

    def run(self, provider, context=None):
        results = None
        try:
            results = provider.navigate(context)
        except KodionException, ex:
            if provider.handle_exception(context, ex):
                provider.log(ex.message, constants.log.ERROR)
                pass
            return

        result = results[0]
        options = {}
        options.update(results[1])

        if isinstance(result, bool) and not result:
            log("navigate returned 'False'")
        elif isinstance(result, VideoItem):
            log("resolve video item for '%s'" % (result.get_name()))
        elif isinstance(result, list):
            for content_item in result:
                log("%s" % (content_item.get_name()))
                pass
            pass
        else:
            # handle exception
            pass
        pass

    pass
