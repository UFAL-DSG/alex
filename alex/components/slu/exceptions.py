from alex import AlexException


class SLUException(AlexException):
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


class DialogueActConfusionNetworkException(SLUException):
    pass
