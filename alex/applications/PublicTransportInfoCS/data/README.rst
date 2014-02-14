
Public Transport Info (Czech) -- data
===========================================

This directory contains the database used by the Czech Public Transport Info system, i.e. a list of public transportation stops, time expressions etc. that are understood by the system. 

The main database module is located in ``database.py``. You may obtain a dump of the database by running ``./database.py dump``.

To build all needed generated files that are not versioned, run ``build_data.sh``.

Contents of additional data files
=================================

Some of the data (for the less populous slots) is included directly in the code ``database.py``, but most of the data (e.g., stops and cities) is located in additional list files. 

Resources used by public transport direction finders
----------------------------------------------------

The sources of the data that are loaded by the application are:

* ``cities.expanded.txt`` -- list of known cities and towns in the Czech Rep. (tab-separated: slot value name + possible surface forms separated by semicolons; lines starting with '#' are ignored)
* ``stops.expanded.txt`` -- list of known stop names (same format)
* ``cities_stops.tsv`` -- "compatibility table": lists compatible city-stops pairs, one entry per line (city and stop are separated by tabs). Only the primary stop and city names are used here.

The files ``cities.expanded.txt`` and ``stops.expanded.txt`` are generated from ``cities.txt`` and ``stops.txt`` using the ``expand_stops.py`` script (see documentation in the file itself; you need to have `Morphodita <http://ufal.mff.cuni.cz/morphodita>`_ Python bindings installed to successfully run this script). Please note that the surface forms in them are lowercased and do not include any punctuation (this can be obtained by setting the ``-l`` and ``-p`` parameters of the ``expand_stops.py`` script).

Colloquial stop names' variants that are added by hand are located in the ``stops-add.txt`` file and are appended to the ``stops.txt`` before performing the expansion.

Additional resources for the CRWS/IDOS directions finder
--------------------------------------------------------

Since the CRWS/IDOS directions finder uses abbreviated stop names that need to be spelled out in ALEX, there is an additional resource file loaded by the system:

* ``idos_map.tsv`` -- a mapping from the slot value names (city + stop) to abbreviated CRWS/IDOS names (stop list + stop)

The ``convert_idos_stops.py`` script is used to expand all possible abreviations and produce a mapping from/to the original CRWS/IDOS stop names as they appear, e.g., at `the IDOS portal <http://portal.idos.cz>`_ .

Resources used by the weather information service
-------------------------------------------------

The weather service uses one additional file:

* ``cities_locations.tsv`` -- this file contains GPS locations of all cities in the Czech Republic.

