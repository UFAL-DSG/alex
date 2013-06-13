#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import random

from alex.components.nlg.template import TemplateNLG
from alex.utils.exception import TemplateNLGException

ORD_NUMBERS = {
    '1': u'první',
    '2': u'druhá',
    '3': u'třetí',
    '4': u'čtvrtá',
    '5': u'pátá',
    '6': u'šestá',
    '7': u'sedmá',
    '8': u'osmá',
    '9': u'devátá',
}

CARD_NUMBERS = {
    '1': u'jedna',
    '2': u'dva',
    '3': u'tři',
    '4': u'čtyři',
    '5': u'pět',
    '6': u'šest',
    '7': u'sedm',
    '8': u'osm',
    '9': u'devět',
}

class AOTBNLG(TemplateNLG):
    def __init__(self, cfg):
        super(AOTBNLG, self).__init__(cfg)

#    def generate_inform(self, dai):
#        if dai.name == u"vehicle":
#            if dai.value == u"SUBWAY":
#                return u"Jeďte metrem"
#            elif dai.value == u"TRAM":
#                return u"Jeďte tramvají číslo"
#            elif dai.value == u"BUS":
#                return u"Jeďte autobusem číslo"
#            else:
#                return u"Systémová chyba 3"
#        elif dai.name == u"line":
#            return unicode(dai.value)
#        elif dai.name == u"go_at":
#            return u"v %s" % dai.value
#        elif dai.name == u"headsign":
#            return u"směrem %s." % dai.value
#        elif dai.name == u"enter_at":
#            return u"z %s," % dai.value
#        elif dai.name == u"exit_at":
#            return u"Vystupte na %s." % dai.value
#        elif dai.name == u"transfer":
#            return u"A pak přestupte a "
#        elif dai.name == u"alternatives":
#            return u"Našla jsem %s cesty." % dai.value
#        elif dai.name == u"alternative":
#            return u"Možnost %s." % ORD_NUMBERS[dai.value]
#        elif dai.name == u"not_understood":
#            return random.choice(
#                    [
#                        u"Nerozuměla jsem. Jěště jednou prosím.",
#                        u"Můžete to zopakovat?",
#                        u"Ještě jednou prosím.",
#                    ])
#
#        elif dai.name == u"not_found":
#            return random.choice(
#                     [
#                        u"Jemi líto, ale žádné spojení jsem nenašla.",
#                        u"Promiňte požadovanou cestu jsem nenašla.",
#                     ])
#        elif dai.name == u"from_stop":
#            return u"Chcete cestovat z %s " % dai.value
#        elif dai.name == u"to_stop":
#            return " cestujete do %s" % dai.value
#        else:
#            return u"Systémová chyba 4"
#
#    def generate_request(self, dai):
#        if dai.name == u"from_stop":
#            return u"Odkud chcete jet?"
#        elif dai.name == u"to_stop":
#            return u"Kam chcete jet?"
#        elif dai.name == u"time":
#            return u"Kdy chcete jet"
#        else:
#            return u"Systémová chyba 1"
#
#    def generate_implicit_confirm(self, dai):
#        if dai.name == u"from_stop":
#            return u"Dobře, z %s." % dai.value
#        elif dai.name == u"to_stop":
#            return u"Dobře, do %s." % dai.value
#        elif dai.name == u"time":
#            return u"Dobře, v %s." % dai.value
#        else:
#            return u"Dobře, %s." % dai.value

    def backoff(self, da):
#        print "AOTBNLG backoff"
#
#        res = []
#        for dai in da:
#            if dai.dat == u"request":
#                res += [self.generate_request(dai)]
#            elif dai.dat == u"inform" and dai.name == u"repeat":
#                res += [self.last_utterance]
#            elif dai.dat == u"inform":
#                res += [self.generate_inform(dai)]
#            elif dai.dat == u"iconfirm":
#                res += [self.generate_implicit_confirm(dai)]
#            elif dai.dat == u"help":
#                res += [self.generate_help(dai)]
#            else:
#                return u"Systémová chyba 2"
#
#        return u" ".join(res)

        raise TemplateNLGException("The backoff NLG should not be necessary at this moment.")
