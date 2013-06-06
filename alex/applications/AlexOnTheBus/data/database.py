#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import codecs

database = {
        u"task": {
            u"next_tram": [u"next_tram"]
        },
        u"time": {
            u'$time$': [u'$time$']
        },
        u"from": {
        #    "$from$": ["$from$"],
        #    "andel": ["andel"],
        #    "karlak": ["karlak"],
        #    "ipak": ["ipak", "ip"],
        },
        u"to": {
        #    "$to$": ["$to$"],
        #    "andel": ["andel"],
        #    "I. P. Pavlova": ["ipak", "ip", "ípák", "i p pavlova"],
        },
        u"stop": {
            u"$from$": [u"$from$"],
            u"$to$": [u"$to$"],

        },
}

numbers = ["nula", "jedna", "dve", "tri", "ctyri", "pet", "sest", "sedm", "osm", "devet", ]
numbers_10 = ["", "deset", "dvacet", "tricet", "ctyricet", "padesat", "sedesat", ]

def db_add(slot, canonical, surface):
    surface = surface.strip()
    if len(canonical) == 0 or len(surface) == 0:
        return


    if len(canonical) == 0 or len(surface) == 0:
        import ipdb; ipdb.set_trace()

    if not canonical in database[slot]:
        database[slot][canonical] = []

    database[slot][canonical] += [surface]


def num_to_word(x):
    res = ""
    if x / 10 > 0:
        res += numbers_10[x / 10]
        res += " "

    if x % 10 > 0:
        res += numbers[x % 10]

    res = res.strip()

    return res

def time_wrap(what):
    return "v %s" % what

def time_rel_wrap(what):
    return "za %s" % what

def time_rel_prefix(what):
    return "+%s" % what

def add_time():
    for hh in range(24):
        hh_word = num_to_word(hh)
        ftime = "%d:00" % (hh, )

        db_add("time", ftime, time_wrap("%d" % hh))
        db_add("time", ftime, time_wrap("%d hodin" % hh))

        time_str = "%s" % hh_word
        db_add("time", ftime, time_wrap(time_str))
        db_add("time", ftime, unicode(hh))
        # db_add("time", time_rel_prefix(ftime), time_rel_wrap(time_str))

        time_str = "%s hodin" % hh_word
        db_add("time", ftime, time_wrap(time_str))
        # db_add("time", time_rel_prefix(ftime), time_rel_wrap(time_str))

        for mm in range(60):
            mm_word = num_to_word(mm)
            ftime = "%d:%d" % (hh, mm,)
            db_add("time", ftime, time_wrap("%d %d" % (hh, mm)))
            db_add("time", ftime, time_wrap("%d hodin %d minut" % (hh, mm)))

            time_str = "%s hodin %s minut" % (hh_word, mm_word, )
            db_add("time", ftime, time_wrap(time_str))
            # db_add("time", time_rel_prefix(ftime), time_rel_wrap(time_str))

            time_str = "%s %s" % (hh_word, mm_word, )
            db_add("time", ftime, time_wrap(time_str))
            # db_add("time", time_rel_prefix(ftime), time_rel_wrap(time_str))

    for mm in range(60):
        ftime = "%d" % mm
        mm_word = num_to_word(mm)
        time_str = "%s minut" % (mm_word, )
        # db_add("time", time_rel_prefix(ftime), time_rel_wrap(time_str))

def add_stops():
    dir = os.path.dirname(os.path.abspath(__file__))
    with codecs.open(os.path.join(dir, "zastavky.expanded.txt"), encoding='utf-8') as f_in:
        for ln in f_in:
            ln = ln.strip().lower()
            ln = ln.split(';')

            db_add('stop', ln[0], ln[0])

            alternatives = set(ln[1:])
            for alternative_form in alternatives:
                db_add('stop', ln[0], alternative_form)

            #db_add('from', ln, ln)
            #db_add('to', ln, ln)
            #db_add('to', ln, ln)

def stem():
    import autopath
    from alex.utils.czech_stemmer import cz_stem

    for _, vals in database.iteritems():
        for cann_value in vals.keys():
            vals[cann_value] = [" ".join(cz_stem(ww) for ww in w.split()) for w in vals[cann_value]]


########################################################################
# Expand automatically the database
########################################################################

add_time()
add_stops()
stem()
