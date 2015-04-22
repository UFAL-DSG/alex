# TODO: Move the exceptions to the objects that raise them.
from alex import AlexException


class ConfigException(AlexException):
    pass


class SessionLoggerException(AlexException):
    pass


class SessionClosedException(AlexException):
    pass
