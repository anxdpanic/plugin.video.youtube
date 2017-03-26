from ..abstract_settings import AbstractSettings


class MockSettings(AbstractSettings):
    def __init__(self):
        AbstractSettings.__init__(self)

        self._settings = {}
        pass

    def get_string(self, settings_id, default_value=None):
        return self._settings.get(settings_id, default_value)

    def set_string(self, settings_id, value):
        self._settings[settings_id] = value
        pass

    pass