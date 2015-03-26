from alex import AlexException

from alex.ml.hypothesis import ConfusionNetworkException

class SLUException(AlexException):
    pass


class SLUConfigurationException(SLUException):
    pass


class DAILRException(SLUException):
    pass


class CuedDialogueActError(SLUException):
    pass


class DAIKernelException(SLUException):
    pass


class DialogueActItemException(SLUException):
    pass


class DialogueActException(SLUException):
    pass


class DialogueActNBListException(SLUException):
    pass


class DialogueActConfusionNetworkException(SLUException, ConfusionNetworkException):
    pass
