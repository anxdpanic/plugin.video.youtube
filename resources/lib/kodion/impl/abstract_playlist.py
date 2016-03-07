__author__ = 'bromix'


class AbstractPlaylist(object):
    def __init__(self):
        pass

    def clear(self):
        raise NotImplementedError()

    def add(self, base_item):
        raise NotImplementedError()

    def shuffle(self):
        raise NotImplementedError()

    def unshuffle(self):
        raise NotImplementedError()

    pass
