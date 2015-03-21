#!/bin/bash
#
# Build all necessary data
#

die() { echo "$@" 1>&2 ; exit 1; }

echo 'Updating source files from the server...' 1>&2
python -c 'import autopath; from alex.utils.config import online_update; online_update("applications/PublicTransportInfoCS/data/czech.dict"); online_update("applications/PublicTransportInfoCS/data/czech.tagger"); online_update("applications/PublicTransportInfoCS/data/stops-idos.tsv")' || die 'Could not update source files'

echo 'Converting IDOS stops...' 1>&2
./convert_idos_stops.py cities.txt stops-idos.tsv stops.txt cities_stops.tsv idos_map.tsv 2>errors.txt || die 'Could not convert IDOS stops (see errors.txt).'

echo 'Expanding stops...' 1>&2
./expand_stops.py -c 1,2,3,4,6 -l -p stops.txt stops-add.txt stops.expanded.txt || die 'Could not expand stops'

echo 'Expanding cities...' 1>&2
./expand_stops.py -c 1,2,3,4,6 -l -p cities.txt cities.expanded.txt || die 'Could not expand cities'

echo 'Expanding train names...'
# TODO: Add proper expanding.
paste train_names.txt train_names.txt | tr "[A-Z]" "[a-z]" > train_names.expanded.txt
