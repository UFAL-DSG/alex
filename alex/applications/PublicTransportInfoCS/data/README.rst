
Public Transport Info (Czech) -- data
===========================================

This directory contains the database used by the Czech Public Transport Info system, i.e. a list of Prague Integrated Transport (PID) stops and a list of time expressions that are understood by the system. 

The main database module is located in ``database.py``. You may obtain a dump of the database by running ``./database.py dump``.

Some of the data (for the less populous slots) is included directly in the code of the database, but most of the data (stops and cities) is located in additional list files. The primary sources of the data are:

* ``cities.txt`` -- list of known cities and towns in the Czech Rep. (plain text, one entry per line with possible name variants separated by tabs; lines starting with ``#`` are treated as comments)
* ``stops.txt`` -- list of known stop names (the same format)
* ``cities_stops.tsv`` -- "compatibility table": lists compatible city-stops pairs, one entry per line (city and stop are separated by tabs). Only the primary stop and city names are used here.

The files ``cities.txt`` and ``stops.txt`` are not used directly, though. The database module loads the PID stops list from ``stops.expanded.txt`` and ``cities.expanded.txt``, where various inflection forms of the city and stop names are located (base form of the primary name is shown first, with other forms separated by semicolons). These files are generated using the ``expand_stops.pl`` script (see documentation in the file itself; you need to have `Treex <http://ufal.mff.cuni.cz/treex>`_ installed to successfully run this script).


Original data sources
---------------------

* The plain list of stops in Prague (including the surrounding towns) has been obtained by running ``pdftotext`` on `this PDF from the PID website <http://www.ropid.cz/data/Galleries/70/100/d790_1_Seznam_zastavek_2013-07.pdf>`_ and manual cleaning.

* The list of stops in Brno (not the surrounding towns) has been obtained from `this PDF <http://www.idsjmk.cz/cenik/historie/050901/Obce-zastavky.pdf>`_ (Note: a newer version is available and should be used).

