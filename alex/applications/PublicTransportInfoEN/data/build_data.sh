#!/bin/bash
#
# Build all necessary data
#

die() { echo "$@" 1>&2 ; exit 1; }

echo 'Updating source files from the server...' 1>&2
python -c \
    'import autopath; \
     from alex.utils.config import online_update; \
     online_update("applications/PublicTransportInfoEN/data/preprocessing/resources/streets-in.csv"); \
     online_update("applications/PublicTransportInfoEN/data/preprocessing/resources/stops-in.csv"); \
     online_update("applications/PublicTransportInfoEN/data/preprocessing/resources/cities-in.csv"); \
     online_update("applications/PublicTransportInfoEN/data/preprocessing/resources/states-in.csv"); \
     online_update("applications/PublicTransportInfoEN/data/preprocessing/resources/stops-add.txt"); \
     online_update("applications/PublicTransportInfoEN/data/preprocessing/resources/cities-add.txt"); \
     online_update("applications/PublicTransportInfoEN/data/preprocessing/resources/states-add.csv")' \
     || die 'Could not update source files'

echo 'Expanding states...' 1>&2
./expand_states_script.py \
    -c \
    --states=preprocessing/resources/states-in.csv \
    --append-states=preprocessing/resources/states-add.txt \
    || die 'Could not expand states.'

echo 'Expanding cities...' 1>&2
./expand_cities_script.py \
    -c \
    --cities=preprocessing/resources/cities-in.csv \
    --append-cities=preprocessing/resources/cities-add.txt \
    || die 'Could not expand cities.'

echo 'Expanding stops...' 1>&2
./expand_stops_script.py \
    -c \
    --stops=preprocessing/resources/stops-in.csv \
    --append-stops=preprocessing/resources/stops-add.txt \
    || die 'Could not expand stops.'

echo 'Expanding streets...' 1>&2
./expand_streets_script.py \
    -c \
    --streets=preprocessing/resources/streets-in.csv \
    --append-streets=preprocessing/resources/streets-add.txt \
    || die 'Could not expand streets.'

echo ''
echo 'Expansion completed successfully!'