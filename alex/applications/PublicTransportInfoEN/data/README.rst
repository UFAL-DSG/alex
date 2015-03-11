Public Transport Info (English) -- data
===========================================

This directory contains the database used by the English Public Transport Info system, i.e. a list of public transportation stops, number expressions etc. that are understood by the system.

The main database module is located in ``database.py``. You may obtain a dump of the database by running ``./database.py dump``.

To build all needed generated files that are not versioned, run ``build_data.sh``.

Contents of additional data files
=================================

Some of the data (for the less populous slots) is included directly in the code ``database.py``, but most of the data (e.g., stops and cities) is located in additional list files. 

Resources used by public transport direction finders and weather service
------------------------------------------------------------------------

The sources of the data that are loaded by the application are:

* ``cities.expanded.txt`` -- list of known cities and towns in the USA. (tab-separated: slot value name + possible forms separated by semicolons; lines starting with '#' are ignored)
* ``states.expanded.txt`` -- list of us state names (same format).
* ``stops.expanded.txt`` -- list of known stop names (same format) in NY.
* ``stops.expanded.txt`` -- list of known stop names (same format) in NY.
* ``streets.expanded.txt`` -- list of known street names (same format)
* ``boroughs.expanded.txt`` -- list of known borough names (same format)
* ``cities.locations.csv`` -- tab separated list of known cities and towns, their state and geo location (longitude|latitude).
* ``stops.locations.csv`` -- tab separated list of stops, their cities and geo location (longitude|latitude).
* ``stops.borough.locations.csv`` -- tab separated list of stops, their boroughs and geo location (longitude|latitude).
* ``streets.types.locations.csv`` -- tab separated list of streets, their boroughs and type (Avenue, Street, Court etc.)

All of these files are generated from ``states-in.csv``, ``cities-in.csv``, ``stops-in.csv``, ``streets-in.csv`` and ``boroughs-in.csv`` located at ``./preprocessing/resources`` using the ``expand_states_script.py``, ``expand_cities_script.py``, ``expand_stops_script.py``, ``expand_streets_script.py`` and ``expand_boroughs_script.py`` script respectively.
Please note that all forms in ``*.expanded.txt`` files are lowercased and do not include any punctuation.

Colloquial name variants that are added by hand are located in the ``./preprocessing/resources/*-add.txt`` files for each slot and are appended to
the expansion process.

``build_data.sh`` script is combining all the expansion scripts mentioned earlier into one process.