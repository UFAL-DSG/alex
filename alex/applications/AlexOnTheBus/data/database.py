#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import os
import codecs


__all__ = ['database']


database = {
        "task": {
            "next_tram": ["další"]
        },
        "time": {
        },
        "stop": {
        },
        u"tt": {
            u"bus": [u"bus", u"autobus"],
            u"tram": [u"tram", u"tramvaj", u"tramvajka"],
            u"metro": [u"metro", u"krtek", u"podzemka"],
            u"vlak": [u"vlak", u"rychlík", u"panťák"],
            u"lanovka": [u"lanovka"],
            u"přívoz": [u"přívoz", u"loď"],
        },
        u"ampm": {
            u"am": [u"dopo", u"dopoledne", u"ráno"],
            u"pm": [u"odpo", u"odpoledne", u"večer"],
        },
}

NUMBERS_1 = ["nula", "jedna", "dvě", "tři", "čtyři", "pět", "šest", "sedm",
             "osm", "devět", ]
NUMBERS_10 = ["", "deset", "dvacet", "třicet", "čtyřicet", "padesát",
              "šedesát", ]
NUMBERS_TEEN = ["deset", "jedenáct", "dvanáct", "třináct", "čtrnáct",
                "patnáct", "šestnáct", "sedmnáct", "osmnáct", "devatenáct"]

# name of the file with one stop per line, assumed to reside in the same
# directory as this script
#
# The file is expected to have this format:
#   <value>; <phrase>; <phrase>; ...
# where <value> is the value for a slot and <phrase> is its possible surface
# form.
STOPS_FNAME = "zastavky.expanded.txt"  # this has been expanded to include
                                       # other forms of the words; still very
                                       # dirty, though


def db_add(slot, value, surface):
    """A wrapper for adding a specified triple to the database."""
    surface = surface.strip()
    if len(value) == 0 or len(surface) == 0:
        return
    database[slot].setdefault(value, list()).append(surface)


def spell_number(num):
    """Spells out the number given in the argument."""
    tens, units = num / 10, num % 10
    tens_str = NUMBERS_10[tens]
    units_str = NUMBERS_1[units]
    if tens == 1:
        return NUMBERS_TEEN[units]
    elif tens:
        if units:
            return "{t} {u}".format(t=tens_str, u=units_str)
        return "{t}".format(t=tens_str)
    else:
        return units_str


# DEPRECATED
# def time_wrap(what):
#     return "v %s" % what
# DEPRECATED
# def time_rel_wrap(what):
#     return "za %s" % what
# DEPRECATED
# def time_rel_prefix(what):
#     return "+%s" % what


def add_time():
    """\
    Basic approximation of all known explicit time expressions.

    Handles:
        <hour>
        <hour> hodin <minute>
        <houn> <minute>
    where <hour> and <minute> are spelled as numbers.

    Cannot handle:
        pět nula nula
        pět nula jedna
        jedna hodina dvacet   ...would have to be "jedna hodin dvacet"
        tři hodiny dvacet     ...would have to be "tři hodin dvacet"
        za pět osum
        dvě odpoledne         ...only "čtrnáct" is taken to denote "14"

    """
    numbers_str = [spell_number(num) for num in xrange(60)]
    # ["nula", "jedna", ..., "padesát devět"]
    for hour in xrange(24):
        hour_str = numbers_str[hour]
        time_val = "{h}:00".format(h=hour)
        db_add("time", time_val, hour_str)
        # db_add("time", time_val, time_wrap(hour_str))
        # db_add("time", time_rel_prefix(time_val), time_rel_wrap(hour_str))

        for minute in xrange(60):
            minute_str = numbers_str[minute]
            time_val = "{h}:{m}".format(h=hour, m=minute)
            # FIXME This is not always appropriate.
            time_str = "{h} hodin {m}".format(h=hour_str, m=minute_str)
            db_add("time", time_val, time_str)
            time_str = "{h} {m}".format(h=hour_str, m=minute_str)
            db_add("time", time_val, time_str)
            # db_add("time", time_val, time_wrap(time_str))
            # db_add("time", time_rel_prefix(time_val), time_rel_wrap(time_str))

    # DEPRECATED
    # for minute in xrange(60):
        # time_val = "%d" % minute
        # mm_word = spell_number(minute)
        # time_str = "%s minut" % (mm_word, )
        # db_add("time", time_rel_prefix(time_val), time_rel_wrap(time_str))


def add_stops():
    """Adds names of all stops as listed in `STOPS_FNAME' to the database."""
    dirname = os.path.dirname(os.path.abspath(__file__))
    with codecs.open(os.path.join(dirname, STOPS_FNAME),
                     encoding='utf-8') as stops_file:
        for ln in stops_file:
            ln = ln.strip().lower()
            stop_val, stop_names = ln.split(';', 1)
            for synonym in stop_names.split(';'):
                db_add('stop', stop_val, synonym)


def stem():
    """Stems words of all surface forms in the database."""
    import autopath
    from alex.utils.czech_stemmer import cz_stem

    for _, vals in database.iteritems():
        for value in vals.keys():
            vals[value] = [" ".join(cz_stem(word) for word in surface.split())
                           for surface in vals[value]]


########################################################################
#                  Automatically expand the database                   #
########################################################################
add_time()
add_stops()
# FIXME: This is not the best place to do stemming.
stem()
