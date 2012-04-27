#!/usr/bin/env python
# -*- coding: utf-8 -*-

class SDSException(Exception):
  pass

class SLUException(SDSException):
  pass

class UtteranceException(SLUException):
  pass

class UtteranceNBListException(SLUException):
  pass

class DialogueActItemException(SLUException):
  pass

class DialogueActNBListException(SLUException):
  pass

class DAIKernelException(SLUException):
  pass
