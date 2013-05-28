#!/usr/bin/env python
# -*- coding: utf-8 -*-
import random

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

class AOTBNLG(object):
    def __init__(self, cfg):
        self.cfg = cfg

    def generate_inform(self, dai):
        if dai.name == u"vehicle":
            if dai.value == u"SUBWAY":
                return u"jeď metrem"
            elif dai.value == u"TRAM":
                return u"jeď tramvají číslo"
            elif dai.value == u"BUS":
                return u"jeď autobusem číslo"
            else:
                return u"Systémová chyba 3"
        elif dai.name == u"line":
            return str(dai.value)
        elif dai.name == u"go_at":
            return u"v %s" % dai.value
        elif dai.name == u"headsign":
            return u"směrem %s." % dai.value
        elif dai.name == u"enter_at":
            return u"z %s," % dai.value
        elif dai.name == u"exit_at":
            return u"vystup na %s." % dai.value
        elif dai.name == u"transfer":
            return u"a pak přestup a"
        elif dai.name == u"alternatives":
            return u"našla jsem %s cest." % dai.value
        elif dai.name == u"alternative":
            return u"možnost %s." % ORD_NUMBERS[dai.value]
        else:
            return u"Systémová chyba 4"

    def generate_request(self, dai):
        if dai.name == u"from_stop":
            return u"Odkud chceš jet?"
        elif dai.name == u"to_stop":
            return u"Kam chceš jet?"
        elif dai.name == u"time":
            return u"Kdy chceš jet"
        else:
            return u"Systémová chyba 1"

    def generate_implicit_confirm(self, dai):
        if dai.name == u"from_stop":
            return u"dobře, z %s." % dai.value
        elif dai.name == u"to_stop":
            return u"dobře, do %s." % dai.value
        elif dai.name == u"time":
            return u"dobře, v %s." % dai.value
        else:
            return u"dobře, %s." % dai.value

    def generate(self, da):
        res = []
        for dai in da:
            if dai.dat == u"hello":
                res += [u"Ahoj, odkud a kam chceš jet?"]
            elif dai.dat == u"not_understood":
                res += [random.choice([u"Promiň, nerozuměla jsem ti.", u"Co?", u"Cože?", u"Ještě jednou prosím?"])]
                #if dai.value is not None:
                #    res += [u"Rozuměla jsem: %s" % dai.value]
            elif dai.dat == u"request":
                res += [self.generate_request(dai)]
            elif dai.dat == u"help":
                res += [u"Dokážu hledat spojení po Praze. Stačí říct z jaké stanice chceš jet a do jaké stanice chceš jet. Když neřekneš kdy chceš jet, najdu nejbližší spojení."]
            elif dai.dat == u"inform":
                res += [self.generate_inform(dai)]
            elif dai.dat == u"implicit_confirm":
                res += [self.generate_implicit_confirm(dai)]
            elif dai.dat == u"bye":
                res += [u"Na shledanou."]
            elif dai.dat == u"bye":
                res += [u"Cestu jsem nenašla"]
            else:
                return u"Systémová chyba 2"

        return u" ".join(res)
