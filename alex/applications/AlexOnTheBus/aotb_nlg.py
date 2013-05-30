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
                return u"jeďte metrem"
            elif dai.value == u"TRAM":
                return u"jeďte tramvají číslo"
            elif dai.value == u"BUS":
                return u"jeďte autobusem číslo"
            else:
                return u"Systémová chyba 3"
        elif dai.name == u"line":
            return unicode(dai.value)
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
            return u"Odkud chcete jet?"
        elif dai.name == u"to_stop":
            return u"Kam chcete jet?"
        elif dai.name == u"time":
            return u"Kdy chcete jet"
        else:
            return u"Systémová chyba 1"

    def generate_implicit_confirm(self, dai):
        if dai.name == u"from_stop":
            return u"Dobře, z %s." % dai.value
        elif dai.name == u"to_stop":
            return u"Dobře, do %s." % dai.value
        elif dai.name == u"time":
            return u"Dobře, v %s." % dai.value
        else:
            return u"Dobře, %s." % dai.value

    def generate_help(self, dai):
        if dai.name == "from_stop":
            return u"Řekni například z Anděla."
        elif dai.name == "to_stop":
            return u"Řekni například na Zličín."
        else:
            return u"Dokážu hledat spojení MHD po Praze. Řekněte postupně odkud a kam chcete jet. Případně v kolik hodin."


    def generate(self, da):
        res = []
        for dai in da:
            if dai.dat == u"hello":
                res += [random.choice(
                          [
                            u"Dobrý den, dovolali jste se na informace o veřejné dopravě v Praze. ",
                            u'Dobrý den.',
                          ]
                        )
                       ]
                res += [random.choice(
                          [
                            u"Tato experimentální služba je poskytována laboratoří výzkumu hlasových dialogových systémů na Ústavu Fomrmální a Aplikované Lingvistiky na Karlově Univerzitě. " +
                            u'',
                          ]
                        )
                       ]
                res += [u"Hovor je nahráván. Více informací o této službě je na stránkách projektu."]
                res += [u"Odkud a kam chcete jet?",]
                res += [random.choice(
                          [
                            u"Můžete říct například chci jet z Malostranského náměstí na Zvonařku.",
                            u"",
                          ]
                        )
                       ]

            elif dai.dat == u"not_understood":
                res += [random.choice([u"Nerozuměla jsem. Jěště jednou prosím.", u"Můžete to zopakovat?", u"Ještě jednou prosím."])]
                #if dai.value is not None:
                #    res += [u"Rozuměla jsem: %s" % dai.value]
            elif dai.dat == u"request":
                res += [self.generate_request(dai)]
            elif dai.dat == u"inform":
                res += [self.generate_inform(dai)]
            elif dai.dat == u"implicit_confirm":
                res += [self.generate_implicit_confirm(dai)]
            elif dai.dat == u"bye":
                res += [u"Na shledanou."]
            elif dai.dat == u"not_found":
                res += [u"Cestu jsem nenašla."]
            elif dai.dat == u"help":
                res += [self.generate_help(dai)]
            else:
                return u"Systémová chyba 2"

        return u" ".join(res)
