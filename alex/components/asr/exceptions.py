from alex import AlexException


class ASRException(AlexException):
    pass


class JuliusASRException(ASRException):
    pass


class JuliusASRTimeoutException(ASRException):
    pass


class KaldiASRException(ASRException):
    pass


class KaldiSetupException(KaldiASRException):
    pass
