#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import codecs
import os
import re
import sys

from alex.utils.config import online_update, to_project_path


__all__ = ['database']


database = {
    "task": {
        "find_connection": ["find connection", "find a connection", "find out connection", "find link", "find a link"
                            "find out link", "looking for a connection", 'connection', 'link',
                           ],
        "find_platform": ["find platform", "find out platform", ],
        'weather': ['weather', ],
    },
    "time": {
        "now": [ "now", "at once", "immediately", "offhand", "at this time",
                 "the closest", "this instant"],
        "0:01": ["minute", ],
        "0:15": ["quarter of an hour", ],
        "0:30": ["half an hour", "half past"],
        "0:45": ["three quarters of an hour", ],
        "1:00": ["hour", ],
    },
    "date_rel": {
        "today": ["today", "this day", "todays", "this days"],
        "tomorrow": ["tomorrow", "tomorrows", "morrow", "morrows"],
        "day_after_tomorrow": ["day after tomorrow", "after tomorrow" ,"after tomorrows"],
    },
    "street": {
    },
    "stop": {
    },
    "vehicle": {
        "dontcare": ["whatever", "no matter how", "not matter", "don't matter", "doesn't matter",
                     "any way possible", "any possible way", "any means", "don't care how", "do not care how"],
        "bus": ["bus", "buses", "coach"],
        "tram": ["tram", "trams", "streetcar", "streetcars", "tramcar", "tramcars", "trammy", "tramm", "tramms"],
        "subway": ["metro", "sub", "subway", "tube", "underground"],
        "train": ["train", "choo-choo", "choochoo", "choo choo", "railway", "railstation", "express", "fast train", "speed train", "rail", "rails"],
        "cable_car": ["cable car", "cablecar", "air railway"],
        "ferry": ["ferry", "boat", "ferryboat", "gondola", ],
        "monorail": ["monorail", "single rail"]
    },
    "ampm": {
        "morning": ["morning", "dawn"],
        "am": [ "forenoon", "a.m." ],
        "pm": [ "afternoon", "p.m."],
        "evening": ["evening", "dusk", ],
        "night": ["night", "nighttime"],
    },
    "city": {
    },
    "state": {
    },
}

NUMBERS_1 = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", ]
NUMBERS_10 = ["", "ten", "twenty", "thirty", "forty", "fifty", "sixty", ]
NUMBERS_TEEN = ["ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
                "sixteen", "seventeen", "eighteen", "nineteen"]
# NUMBERS_ORD = ["zero", "first", "second", "third", "fourth", "fifth", "sixth", # nultý - zero/prime?
#                "seventh", "eighth", "ninth", "tenth", "eleventh", "twelfth",
#                "thirteenth", "fourteenth", "fifteenth", "sixteenth", "seventeenth",
#                "eighteenth", "nineteenth", "twentieth", "twenty first",
#                "twenty second", "twenty third"]

# name of the file with one stop per line, assumed to reside in the same
# directory as this script
#
# The file is expected to have this format:
#   <value>; <phrase>; <phrase>; ...
# where <value> is the value for a slot and <phrase> is its possible surface
# form.
STREETS_FNAME = "streets.expanded.txt"
STOPS_FNAME = "stops.expanded.txt"
CITIES_FNAME = "cities.expanded.txt"
STATES_FNAME = "states.expanded.txt"

# load new stops & cities list from the server if needed
online_update(to_project_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), STREETS_FNAME)))
online_update(to_project_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), STOPS_FNAME)))
online_update(to_project_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), CITIES_FNAME)))
online_update(to_project_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), STATES_FNAME)))


def db_add(category_label, value, form):
    """A wrapper for adding a specified triple to the database."""
#    category_label = category_label.strip()
#    value = value.strip()
#    form = form.strip()

    if len(value) == 0 or len(form) == 0:
        return

    if value in database[category_label] and isinstance(database[category_label][value], list):
        database[category_label][value] = set(database[category_label][value])

#    for c in '{}+/&[],-':
#        form = form.replace(' %s ' % c, ' ')
#        form = form.replace(' %s' % c, ' ')
#        form = form.replace('%s ' % c, ' ')
#    form = form.strip()

    database[category_label].setdefault(value, set()).add(form)


def spell_number(num):
    """Spells out the number given in the argument. not greater than 69"""
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
        <hour> o'clock
        <hour> hour(s)
        <hour> hour(s) <minute>
        <hour> <minute>
        half past/quarter past/quarter to <hour>
        <minute> minute(s)
    where <hour> and <minute> are spelled /given as numbers.

    Cannot yet handle:
        five minutes to ten
    """
    # ["zero", "one", ..., "fifty nine"]
    numbers_str = [spell_number(num) for num in xrange(60)]

    for hour in xrange(24):
        if hour == 1:
            hr_id = 'hour'
        else:
            hr_id = 'hours'

        hr_str = numbers_str[hour]

        # X:00
        add_db_time(hour, 0, '{ho} o\'clock', {'ho': hr_str})

        if hour >= 1 and hour <= 12:
            # (X-1):15 quarter past (X)
            add_db_time(hour, 15, "quarter past {h}", {'h': hr_str})
            # (X-1):30 half past (X)
            add_db_time(hour, 30, "half past {ho}", {'ho': hr_str})
            # (X-1):45 quarter to X
            add_db_time(hour - 1, 45, "quarter to {h}", {'h': hr_str})

        # some must be declined (but variants differ only for hour=1)
        # X:00
        add_db_time(hour, 0, "{h}", {'h': hr_str})
        add_db_time(hour, 0, "{h} {hi}", {'h': hr_str, 'hi': hr_id})
        # X:YY
        for minute in xrange(60):
            min_str = numbers_str[minute]
            add_db_time(hour, minute, "{h} {hi} {m}", {'h': hr_str, 'hi': hr_id, 'm': min_str})
            add_db_time(hour, minute, "{h} {hi} and {m}", {'h': hr_str, 'hi': hr_id, 'm': min_str})
            if minute < 10:
                add_db_time(hour, minute, "{h} {m}", {'h': hr_str, 'm': 'zero ' + min_str})
                if minute > 0:
                    add_db_time(hour, minute, "{h} {m}", {'h': hr_str, 'm': 'o ' + min_str})
                #TODO: "van ou van"i
            add_db_time(hour, minute, "{h} {m}", {'h': hr_str, 'm': min_str})

    # YY minut(u/y)
    for minute in xrange(60):
        min_str = numbers_str[minute]

        if minute == 1:
            min_id = 'minute'
        else:
            min_id = "minutes"

        add_db_time(0, minute, "{m} {mi}", {'m': min_str, 'mi': min_id})

        # if minute < 10 and minute > 0:
        #     add_db_time(0, minute, "{m} {mi}", {'m': 'o ' + min_str, 'mi': min_id})


def add_db_time(hour, minute, format_str, replacements):
    """Add a time expression to the database
    (given time, format string and all replacements as a dict)."""
    time_val = "%d:%02d" % (hour, minute)
    db_add("time", time_val, format_str.format(**replacements))


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

def add_streets():
    """Add street names from the streets file."""
    # todo: temporary hack street = stop for street handling
    add_from_file('stop', STREETS_FNAME)

def add_stops():
    """Add stop names from the stops file."""
    add_from_file('stop', STOPS_FNAME)


def add_cities():
    """Add city names from the cities file."""
    add_from_file('city', CITIES_FNAME)


def add_states():
    """Add state names from the states file."""
    add_from_file('state', STATES_FNAME)


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
add_time()
add_streets()
add_stops()
add_cities()
add_states()

if "dump" in sys.argv or "--dump" in sys.argv:
    save_c2v2f('database_c2v2f.txt')
    save_surface_forms('database_surface_forms.txt')
    save_SRILM_classes('database_SRILM_classes.txt')
