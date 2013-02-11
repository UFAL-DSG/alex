#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This code is PEP8-compliant. See http://www.python.org/dev/peps/pep-0008.

# FIXME: move the definitions of exceptions into their packages or modules


class AlexException(Exception):
    pass


class ASRException(AlexException):
    pass


class SLUException(AlexException):
    pass


class DMException(AlexException):
    pass


class NLGException(AlexException):
    pass


class TTSException(AlexException):
    pass


class HubException(AlexException):
    pass


class SemHubException(HubException):
    pass


class TextHubException(HubException):
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


class UtteranceConfusionNetworkException(SLUException):
    pass


class DialogueActException(SLUException):
    pass


class DialogueActItemException(SLUException):
    pass


class DialogueActNBListException(SLUException):
    pass


class DialogueActConfusionNetworkException(SLUException):
    pass


class DAIKernelException(SLUException):
    pass


class DAILRException(SLUException):
    pass


class DialogueManagerException(AlexException):
    pass


class DummyDialogueManagerException(DialogueManagerException):
    pass


class TemplateNLGException(NLGException):
    pass
