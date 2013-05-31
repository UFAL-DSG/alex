from alex.utils.exception import AlexException

class TTSException(AlexException):
    pass

class TTSInterface(object):
    def synthesize(self, text):
        raise NotImplementedError("TTS")