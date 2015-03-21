#!/bin/bash

for A in {1..1000}
do
    ./ram_hub.py -n 10 -c ram_hub_cs.cfg ../../resources/private/ext-sw-277278111.cfg
done


