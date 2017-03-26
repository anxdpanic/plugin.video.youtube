__author__ = 'bromix'

from youtube_plugin.kodion.impl import Context
from youtube_plugin.kodion.constants import setting

if __name__ == '__main__':
    context = Context(plugin_id='plugin.video.youtube')

    context.log_debug('YouTube settings startup initialization...')
    version = context.get_system_version().get_version()
    application = context.get_system_version().get_app_name()
    settings = context.get_settings()

    mpd_addon = False
    mpd_builtin = False

    if version >= (17, 0):
        mpd_addon = True
    elif version >= (16, 5) and application == 'SPMC':
        mpd_builtin = True
    else:
        settings.set_bool(setting.USE_DASH, False)

    settings.set_bool(setting.DASH_SUPPORT_BUILTIN, mpd_builtin)
    settings.set_bool(setting.DASH_SUPPORT_ADDON, mpd_addon)
    context.log_notice('Startup: detected %s, setting DASH_SUPPORT_BUILTIN = %s, DASH_SUPPORT_ADDON = %s' %
        (context.get_system_version(), mpd_builtin, mpd_addon))
