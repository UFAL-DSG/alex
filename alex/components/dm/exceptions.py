from alex import AlexException


class DMException(AlexException):
    pass


class DialogueStateException(AlexException):
    pass


class DialoguePolicyException(AlexException):
    pass


class DialogueManagerException(AlexException):
    pass


class DeterministicDiscriminativeDialogueStateException(DialogueStateException):
    pass


class DummyDialoguePolicyException(DialoguePolicyException):
    pass
