#!/usr/bin/env python
# -*- coding: utf-8 -*-


class SDSException(Exception):
    pass


class ASRException(SDSException):
    pass


class SLUException(SDSException):
    pass


class DMException(SDSException):
    pass


class NLGException(SDSException):
    pass


class TTSException(SDSException):
    pass


class HubException(SDSException):
    pass


class SemHubException(HubException):
    pass


class TextHubEception(HubException):
    pass


class VoipHubException(HubException):
    pass


class VoipIOException(Exception):
    pass


class JuliusASRException(ASRException):
    pass


class JuliusASRTimeoutException(ASRException):
    pass


class UtteranceException(SLUException):
    pass


class UtteranceNBListException(SLUException):
    pass


class DialogueActException(SLUException):
    pass


class DialogueActItemException(SLUException):
    pass


class DialogueActNBListException(SLUException):
    pass


class DAIKernelException(SLUException):
    pass


class DialogueManagerException(SDSException):
    pass


class DummyDialogueManagerException(DialogueManagerException):
    pass
