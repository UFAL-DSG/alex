#!/usr/bin/env python
# coding: utf-8

from __future__ import unicode_literals

import re

from alex.utils.config import load_as_module

class TTSPreprocessingException(object):
    pass
    
class TTSPreprocessing(object):
    """Process input sentences 
    """
    def __init__(self, cfg, file_name):
        self.cfg = cfg
        
        if file_name:
            self.load(file_name)

    def load(self, file_name):
        tp_mod = load_as_module(file_name, force=True)
        if not hasattr(tp_mod, 'substitutions'):
            raise TTSPreprocessingException("The TTS preprocessing file does not define the 'substitutions' object!")
        
        self.substitutions = tp_mod.substitutions
        
    def process(self, text):
        """Applies all substitutions on the input text and returns the result.
        """
        
        for pattern, repl in self.substitutions:
            text = re.sub(pattern, repl, text)
            
        return text
