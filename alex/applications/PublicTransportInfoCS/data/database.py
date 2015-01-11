#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

if __name__ == '__main__':
    import autopath
import codecs
import os
import re
import sys


from alex.utils.config import online_update, to_project_path

__all__ = ['database']


database = {
    "task": {
        "find_connection": ["najít spojení", "najít spoj", "zjistit spojení",
                            "zjistit spoj", "hledám spojení", 'spojení', 'spoj',
                           ],
        "find_platform": ["najít nástupiště", "zjistit nástupiště", ],
        'weather': ['počasí', ],
    },
    "number": {
        "1": ["jednu"]
    },
    "time": {
        "now": ["nyní", "teď", "teďka", "hned", "nejbližší", "v tuto chvíli", "co nejdřív"],
    },
    "date_rel": {
        "today": ["dnes", "dneska",
                  "dnešek", "dneška", "dnešku", "dneškem",
                  "dnešní", "dnešnímu", "dnešního", "dnešním"],
        "tomorrow": ["zítra", "zejtra",
                     "zítřek", "zítřka", "zítřku", "zítřkem",
                     "zítřejší", "zítřejšímu", "zítřejším", "zítřejšího"],
        "day_after_tomorrow": ["pozítří", "pozejtří"],
    },
    "stop": {
    },
    "vehicle": {
        "dontcare": ["čímkoliv", "jakkoliv", "jakýmkoliv způsobem", "jakýmkoliv prostředkem",
                     "jakýmkoliv dopravním prostředkem", "libovolným dopravním prostředkem"],
        "bus": ["bus", "busem", "autobus", "autobusy", "autobusem", "autobusové", "autobusovýho"],
        "tram": ["tram", "tramvaj", "tramvajový", "tramvaje", "tramvají", "tramvajka", "tramvajkou", "šalina", "šalinou"],
        "subway": ["metro", "metrem", "metrema", "metru", "metra", "krtek", "krtkem", "podzemka", "podzemkou"],
        "train": ["vlak", "vlakem", "vláčkem", "vlaky", "vlakovém", "rychlík", "rychlíky", "rychlíkem", "panťák", "panťákem"],
        "cable_car": ["lanovka", "lanovky", "lanovce", "lanovkou", "lanová dráha", "lanovou dráhou"],
        "ferry": ["přívoz", "přívozy", "přívozem", "přívozu", "loď", "lodí"],
    },
    "ampm": {
        "morning": ["ráno", "nadránem"],
        "am": ["dopo", "dopoledne", ],
        "pm": ["odpo", "odpoledne", ],
        "evening": ["večer", "podvečer", ],
        "night": ["noc", "noci"],
    },
    "city": {
    },
}

# TODO tens, hundreds? "dvacátý/á/ou/ třetí"?
NUMBERS_1 = ["nula", "jedna", ["dvě", "dva"], "tři", ["čtyři", "čtyry"], "pět", "šest", ["sedm", "sedum"],
             ["osm", "osum"], "devět", ]
NUMBERS_10 = ["", "deset", "dvacet", "třicet", ["čtyřicet", "čtyrycet"], "padesát",
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
STOPS_FNAME = "stops.expanded.txt"
CITIES_FNAME = "cities.expanded.txt"

# load new stops & cities list from the server if needed
online_update(to_project_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), STOPS_FNAME)))
online_update(to_project_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), CITIES_FNAME)))


def db_add(category_label, value, form):
    """A wrapper for adding a specified triple to the database."""
#    category_label = category_label.strip()
#    value = value.strip()
#    form = form.strip()

    if len(value) == 0 or len(form) == 0:
        return

    if value in database[category_label] and isinstance(database[category_label][value], list):
        database[category_label][value] = set(database[category_label][value])

#    if category_label == 'stop':
#        if value in set(['Nová','Praga','Metra','Konečná','Nádraží',]):
#            return

#    for c in '{}+/&[],-':
#        form = form.replace(' %s ' % c, ' ')
#        form = form.replace(' %s' % c, ' ')
#        form = form.replace('%s ' % c, ' ')
#    form = form.strip()

    database[category_label].setdefault(value, set()).add(form)

def spell_number(num):
    """Spells out the number given in the argument.

    Returns various forms for each number including:
        - basic and reversed form ("dvacetdva"/"dvaadvacet")
        - one- and two-word form ("čtyřicetšest"/"čtyřicet šest")
        - alternative pronounciations ("čtyry", "sedum")
    """
    tens, units = num / 10, num % 10
    tens_strs = [NUMBERS_10[tens]] if not isinstance(NUMBERS_10[tens], list) else NUMBERS_10[tens]
    units_strs = [NUMBERS_1[units]] if not isinstance(NUMBERS_1[units], list) else NUMBERS_1[units]
    if tens == 1:
        return [NUMBERS_TEEN[units]]
    elif tens:
        if units:
            spellings = []
            spellings += ["{t} {u}".format(t=tens_str, u=units_str) for units_str in units_strs for tens_str in tens_strs]
            spellings += ["{t}{u}".format(t=tens_str, u=units_str) for units_str in units_strs for tens_str in tens_strs]
            spellings += ["{u}{a}{t} ".format(t=tens_str, u=units_str, a='' if units is 1 else 'a')
                          for units_str in units_strs for tens_str in tens_strs]
            return spellings
        return ["{t}".format(t=tens_str) for tens_str in tens_strs]
    else:
        return units_strs


def add_numbers():
    """
    Basic approximation of all known explicit number expressions.

    Handles:
        fractions (půl/čtvrt/tři čtvrtě)
        cardinal numbers <1, 59>
        ordinal numbers <1, 23>
    """

    for fraction, fraction_spelling in [(0.25,'čtvrt'),(0.5,'půl'),(0.75,'tři čtrtě')]:
        add_db_number(fraction, fraction_spelling)

    for cardinal in xrange(60):
        for cardinal_spelling in spell_number(cardinal):
            add_db_number(cardinal, cardinal_spelling)

    for ordinal in xrange(24):
        hr_ord = NUMBERS_ORD[ordinal]
        if ordinal == 1:
            hr_ord = 'jedný'
        add_db_number(ordinal, hr_ord)
        if hr_ord.endswith('ý'):
            add_db_number(ordinal, hr_ord[:-1] + 'é')
            add_db_number(ordinal, hr_ord[:-1] + 'ou')

def add_db_number(number, spelling):
    """Add a number expression to the database (given number and its spelling)."""
    db_add("number", str(number), spelling)

def preprocess_cl_line(line):
    """Process one line in the category label database file."""
    name, forms = line.strip().split("\t")
    forms = [form.strip() for form in forms.split(';')]
    return name, forms


def add_from_file(category_label, fname):
    """Adds to the database names + surface forms of all category labels listed in the given file.
    The file must contain the category lablel name + tab + semicolon-separated surface forms on each
    line.
    """
    dirname = os.path.dirname(os.path.abspath(__file__))
    with codecs.open(os.path.join(dirname, fname), encoding='utf-8') as stops_file:
        for line in stops_file:
            if line.startswith('#'):
                continue
            val_name, val_surface_forms = preprocess_cl_line(line)
            for form in val_surface_forms:
                db_add(category_label, val_name, form)


def add_stops():
    """Add stop names from the stops file."""
    add_from_file('stop', STOPS_FNAME)


def add_cities():
    """Add city names from the cities file."""
    add_from_file('city', CITIES_FNAME)


def save_c2v2f(file_name):
    c2v2f = []
    for k in database:
        for v in database[k]:
            for f in database[k][v]:
                if re.search('\d', f):
                    continue
                c2v2f.append((k, v, f))

    c2v2f.sort()

    # save the database vocabulary - all the surface forms
    with codecs.open(file_name, 'w', 'UTF-8') as f:
        for x in c2v2f:
            f.write(' => '.join(x))
            f.write('\n')


def save_surface_forms(file_name):
    surface_forms = []
    for k in database:
        for v in database[k]:
            for f in database[k][v]:
                if re.search('\d', f):
                    continue
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
                if re.search('\d', f):
                    continue
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
add_numbers()
add_stops()
add_cities()


if __name__ == '__main__':
    if "dump" in sys.argv or "--dump" in sys.argv:
        save_c2v2f('database_c2v2f.txt')
        save_surface_forms('database_surface_forms.txt')
        save_SRILM_classes('database_SRILM_classes.txt')
