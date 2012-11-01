#!/usr/bin/env python
# -*- coding: utf-8 -*-

templates = {
'hello()':                                                  "Hello. How may I help you?",
'hello()&thankyou()':                                       "Hello. Thank you for calling! How may I help you?",
'affirm()&inform(task="find")&inform(pricerange="cheap")':  "Ok, you are looking for something cheap.",
'reqmore()':                                                'Can I help you with anything else?',
'affirm()&inform(pricerange="cheap")':                      'Ok, in a cheap price range.'
}

class TemplateNLG:
    def __init__(self, cfg):
        self.cfg = cfg

    def generate(self, da):
        try:
            return templates[str(da)]
        except:
            return templates[str('reqmore()')]


