#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import codecs
import os
import re
import sys

__all__ = ['database']


database = {
    "task": {
        "find_connection": ["najít spojení", "najít spoj", "zjistit spojení", "zjistit spoj", "hledám spojení",],
        "find_platform": ["najít nastupště", "zjistit nástupiště",],
    },
    "time": {
    },
    "time_rel": {
        "now": ["nyní", "teď", "hned", "nejbližší"],
        "0:05": ["pět minut", ],
        "0:10": ["deset minut", ],
        "0:20": ["dvacet minut", ],
        "0:30": ["půl hodiny", ],
        "0:45": ["tři čtvrtě hodiny", ],
        "1:00": ["hodinu", ],
        "2:00": ["dvě hodiny", ],
    },
    "date_rel": {
        "today": ["dnes", "dneska", ],
        "tomorrow": ["zítra", ],
        "day_after_tomorrow": ["pozítří", ],
    },
    "stop": {
    },
    "trans_type": {
        "bus": ["bus", "busem", "autobus", "autobusy", "autobusem", "autobusové"],
        "tram": ["tram", "tramvaj", "tramvajoví", "tramvaje", "tramvají", "tramvajka", "tramvajkou", "šalina", "šalinou"],
        "metro": ["metro", "metrem", "metrema", "metru","krtek", "krtkem", "podzemka", "podzemkou"],
        "train": ["vlak", "vlakem", "vlaky", "vlakovém", "rychlík", "rychlíky", "rychlíkem", "panťák", "panťákem"],
        "cable_car": ["lanovka", "lanovky", "lanovce", "lanovkou", "lanová dráha", "lanovou dráhou"],
        "ferry": ["přívoz", "přívozy", "přívozem", "přívozu", "loď", "lodí"],
    },
    "ampm": {
        "morning": ["ráno", "nadránem"],
        "am": ["dopo", "dopoledne",],
        "pm": ["odpo", "odpoledne",],
        "evening": ["večer", "podvečer", ],
        "night": ["noc", "noci"],
    },
}

NUMBERS_1 = ["nula", "jedna", "dvě", "tři", "čtyři", "pět", "šest", "sedm",
             "osm", "devět", ]
NUMBERS_10 = ["", "deset", "dvacet", "třicet", "čtyřicet", "padesát",
              "šedesát", ]
NUMBERS_TEEN = ["deset", "jedenáct", "dvanáct", "třináct", "čtrnáct",
                "patnáct", "šestnáct", "sedmnáct", "osmnáct", "devatenáct"]
NUMBERS_ORD = ["nultý", "první", "druhý", "třetí", "čtvrtý", "pátý", "šestý",
               "sedmý", "osmý", "devátý", "desátý", "jedenáctý", "dvanáctý",
               "třináctý", "čtrnáctý", "patnáctý", "šestnáctý", "sedmnáctý",
               "osmnáctý", "devatenáctý", "dvacátý", "jednadvacátý",
               "dvaadvacátý", "třiadvacátý"]

# name of the file with one stop per line, assumed to reside in the same
# directory as this script
#
# The file is expected to have this format:
#   <value>; <phrase>; <phrase>; ...
# where <value> is the value for a slot and <phrase> is its possible surface
# form.
STOPS_FNAME = "stops.expanded.txt"  # this has been expanded to include
                                    # other forms of the words; still very
                                    # dirty, though
#STOPS_FNAME = "stops.txt"

_substs_lit = [
    ('\\bn\\.L\\.', ['nad Labem']),
    ('\\bn\\.Vlt\\.', ['nad Vltavou']),
    ('žel\\.st\\.', ['železniční stanice']), # FIXME None would say this.
                                              # Factorise.
    ('aut\\.st\\.', ['autobusová stanice', 'stanice autobusů']),
    ('žel\\.zast\\.', ['železniční zastávka']),
    ('[Kk]ult\\.dům', ['kulturní dům', 'kulturák']),
    ('n\\.Č\\.[Ll]\\.', ['nad černými lesy']),
    ('n\\.[Ll]\\.', ['nad lesy']),
    ('St\\.Bol\\.', ['stará boleslav']),
    ('\\brozc\\.', ['rozcestí']),
    ('\\bnádr\\.', ['nádraží']),
    ('\\bsídl\\.', ['sídliště']),
    ('\\bnám\\.', ['náměstí']),
    ('\\bnem\\.', ['nemocnice']),
    ('\\bzdr\\.stř\\.', ['zdravotní středisko']),
    ('\\bzdrav\\.stř\\.', ['zdravotní středisko']),
    ('\\bhost\\.', ['hostinec']),
    ('\\bháj\\.', ['hájovna']),
    ('\\bkřiž\\.', ['křižovatka']),
    ('\\bodb\\.', ['odbočka']),
    ('\\bzast\\.', ['zastávka']),
    ('\\bhl\\.sil\\.', ['hlavní silnice']),
    ('\\bn\\.', ['nad']),
    ('\\bp\\.', ['pod']),
    ('\\b(\w)\\.', ['\\1']), # ideally uppercase...
    ('\\bI$', ['jedna']),
    ('\\bII\\b', ['dva']),
    ('\\bD1\\b', ['dé jedna']),
    ('\\bD8\\b', ['dé osm']),
]

_substs = [(re.compile(regex), [val + ' ' for val in vals]) for (regex, vals) in _substs_lit]
_num_rx = re.compile('[1-9][0-9]*')
_num_rx_exh = re.compile('^[1-9][0-9]*$')


def db_add(category_label, value, form):
    """A wrapper for adding a specified triple to the database."""
    form = form.strip()
    if len(value) == 0 or len(form) == 0:
        return
    database[category_label].setdefault(value, set()).add(form)


# TODO allow "jednadvacet" "dvaadvacet" etc.
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


def add_time():
    """
    Basic approximation of all known explicit time expressions.

    Handles:
        <hour>
        <hour> hodin(a/y)
        <hour> hodin(a/y) <minute>
        <houn> <minute>
        půl/čtvrt/tři čtvrtě <hour>
    where <hour> and <minute> are spelled /given as numbers.

    Cannot yet handle:
        pět nula jedna
        za pět osum
        dvě odpoledne         ...only "čtrnáct" is taken to denote "14"

    """
    # ["nula", "jedna", ..., "padesát devět"]
    numbers_str = [spell_number(num) for num in xrange(60)]

    for hour in xrange(24):
        hour_str = numbers_str[hour]
        hour_ord = NUMBERS_ORD[hour]
        if hour_ord.endswith('ý'):
            hour_ord = hour_ord[:-1] + 'é'
        if hour == 1:
            hour_ord = 'jedné'
        hour_id = 'hodin'
        if hour == 1:
            hour_id = 'hodina'
        elif hour in [2, 3, 4]:
            hour_id = 'hodiny'
        # X:00
        time_val = "{h}:00".format(h=hour)
        #db_add("time", time_val, str(hour))
        db_add("time", time_val, hour_str)
        time_str = "{h} nula nula".format(h=hour_str)
        db_add("time", time_val, time_str)
        time_str = "{h} {hi}".format(h=hour_str, hi=hour_id)
        db_add("time", time_val, time_str)
        #time_str = "{h} {hi}".format(h=hour, hi=hour_id)
        #db_add("time", time_val, time_str)
        time_str = "{h} hodině".format(h=hour_ord)
        db_add("time", time_val, time_str)

        if hour >= 1 and hour <= 12:
            # (X-1):15 quarter past (X-1)
            time_val = "{h}:15".format(h=(hour - 1))
            time_str = "čtvrt na {h}".format(h=hour_str)
            db_add("time", time_val, time_str)
            #time_str = "čtvrt na {h}".format(h=hour)
            #db_add("time", time_val, time_str)
            # (X-1):30 half past (X-1)
            time_val = "{h}:30".format(h=(hour - 1))
            time_str = "půl {ho}".format(ho=hour_ord)
            db_add("time", time_val, time_str)
            # (X-1):45 quarter to X
            time_val = "{h}:45".format(h=(hour - 1))
            time_str = "tři čtvrtě na {h}".format(h=hour_str)
            db_add("time", time_val, time_str)
            #time_str = "tři čtvrtě na {h}".format(h=hour)
            #db_add("time", time_val, time_str)

        for minute in xrange(60):
            minute_str = numbers_str[minute]
            time_val = "{h}:{m}".format(h=hour, m=minute)
            time_str = "{h} {hi} {m}".format(h=hour_str, hi=hour_id, m=minute_str)
            db_add("time", time_val, time_str)
            #time_str = "{h} {hi} {m}".format(h=hour, hi=hour_id, m=minute)
            #db_add("time", time_val, time_str)
            time_str = "{h} {m}".format(h=hour_str, m=minute_str)
            db_add("time", time_val, time_str)
            #time_str = "{h} {m}".format(h=hour, m=minute)
            #db_add("time", time_val, time_str)


def preprocess_stops_line(line, expanded_format=False):
    line = line.strip()
    if expanded_format:
        line = line.split(';')
        name = line[0]
        forms = line
    else:
        name = line
        forms = [line,]

    # Do some basic pre-processing. Expand abbreviations.
    new_forms = []
    for form in forms:
        new_form = form
        for regex, subs in _substs:
            if regex.search(form):
                for sub in subs:
                    new_form = regex.sub(sub, new_form)

        new_forms.append(new_form)
    forms = new_forms

    # Spell out numerals.
    if any(map(_num_rx.search, forms)):
        old_names = forms
        forms = list()
        for name in old_names:
            new_words = list()
            for word in name.split():
                if _num_rx_exh.match(word):
                    try:
                        new_words.append(spell_number(int(word)))
                    except:
                        new_words.append(word)
                else:
                    new_words.append(word)
            forms.append(' '.join(new_words))

    # Remove extra spaces, lowercase.
    forms = [' '.join(form.replace(',', ' ').replace('-', ' ')
                      .replace('(', ' ').replace(')', ' ').replace('5', ' ')
                      .replace('0', ' ').replace('.', ' ').split()).lower()
             for form in forms]

    return name, forms


def add_stops():
    """Adds names of all stops as listed in `STOPS_FNAME' to the database."""
    dirname = os.path.dirname(os.path.abspath(__file__))
    is_expanded = 'expanded' in STOPS_FNAME
    with codecs.open(os.path.join(dirname, STOPS_FNAME), encoding='utf-8') as stops_file:
        for line in stops_file:
            stop_name, stop_surface_forms = preprocess_stops_line(line, expanded_format=is_expanded)
            for form in stop_surface_forms:
                db_add('stop', stop_name, form)

def stem():
    """Stems words of all surface forms in the database."""
    import autopath
    from alex.utils.czech_stemmer import cz_stem

    for _, vals in database.iteritems():
        for value in vals.keys():
            vals[value] = set([" ".join(cz_stem(word) for word in surface.split()) for surface in vals[value]])

def save_surface_forms(file_name):
    surface_forms = []
    for k in database:
        for v in database[k]:
            for f in database[k][v]:
                surface_forms.append(f)
    surface_forms.sort()

    # save the database vocabulary - all the surface forms
    with codecs.open(file_name, 'w', 'UTF-8') as f:
        for sf in surface_forms:
            f.write(sf)
            f.write('\n')


def save_SRILM_classes(file_name):
    surface_forms = []
    for k in database:
        for v in database[k]:
            for f in database[k][v]:
                surface_forms.append("CL_" + k.upper() + " " + f.upper())
    surface_forms.sort()

    # save the database vocabulary - all the surface forms
    with codecs.open(file_name, 'w', 'UTF-8') as f:
        for sf in surface_forms:
            f.write(sf)
            f.write('\n')

########################################################################
#                  Automatically expand the database                   #
########################################################################
add_time()
add_stops()

if len(sys.argv) > 1 and sys.argv[1] == "dump":
    save_surface_forms('database_surface_forms.txt')
    save_SRILM_classes('database_SRILM_classes.txt')

# WARNING: This is not the best place to do stemming.
# we will not use stemming anymore because we have much better stop expansion
#stem()
#
#if len(sys.argv) > 1 and sys.argv[1] == "dump":
#    save_surface_forms('database_surface_forms_stemmed.txt')
