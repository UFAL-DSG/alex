
Public Transport Info (Czech) -- data
===========================================

This directory contains the database used by the Czech Public Transport Info system, i.e. a list of public transportation stops and a list of time expressions that are understood by the system. 

The main database module is located in ``database.py``. You may obtain a dump of the database by running ``./database.py dump``.

Some of the data (for the less populous slots) is included directly in the code of the database, but most of the data (stops and cities) is located in additional list files. The primary sources of the data are:

* ``cities.txt`` -- list of known cities and towns in the Czech Rep. (plain text, one entry per line with possible name variants separated by semicolons; lines starting with ``#`` are treated as comments)
* ``stops.txt`` -- list of known stop names (the same format)
* ``cities_stops.tsv`` -- "compatibility table": lists compatible city-stops pairs, one entry per line (city and stop are separated by tabs). Only the primary stop and city names are used here.

The files ``cities.txt`` and ``stops.txt`` are not used directly, though. The database module loads the stops list from ``stops.expanded.txt`` and ``cities.expanded.txt``, where various inflection forms of the city and stop names are located (base form of the primary name is shown first, with other forms separated by semicolons). These files are generated using the ``expand_stops.py`` script (see documentation in the file itself; you need to have `Morphodita <http://ufal.mff.cuni.cz/morphodita>`_ Python bindings installed to 
successfully run this script).

Colloquial stop names' variants that are added by hand are located in the ``stops-add.txt`` file and are appended to the ``stops.txt`` before performing the expansion.

Additional resources for the CRWS/IDOS directions finder
--------------------------------------------------------

Since the CRWS/IDOS directions finder uses abbreviated stop names that need to be spelled out in ALEX, the ``convert_idos_stops.py`` script is used to expand all possible abreviations and produce a mapping from/to the original CRWS/IDOS stop names as they appear, e.g., at `the IDOS portal <http://portal.idos.cz>`_ . This mapping is located in ``idos-map.tsv``.

