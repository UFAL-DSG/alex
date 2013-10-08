
Public Transport Info (Czech) -- data
===========================================

This directory contains the database used by the Czech Public Transport Info system, i.e. a list of Prague Integrated Transport (PID) stops and a list of time expressions that are understood by the system. 

The main database module is located in ``database.py``. You may obtain a dump of the database by running ``./database.py dump``.

The database module loads the PID stops list from ``stops.expanded.txt``, where various inflection forms of the stops are located. This file was generated from a plain list of PID stops using ``expand_stops.pl`` (see documentation in the file itself; you need to have `Treex <http://ufal.mff.cuni.cz/treex>`_ installed to successfully run this script).

The plain list of stops in ``stops.txt`` has been obtained by running ``pdftotext`` on `this PDF from the PID website <http://www.ropid.cz/data/Galleries/70/100/d790_1_Seznam_zastavek_2013-07.pdf>`_ and manual cleaning.

