from alex import AlexException


class SessionLoggerException(AlexException):
    pass


class SessionClosedException(AlexException):
    pass


class HookMultipleInstanceException(AlexException):
    pass
