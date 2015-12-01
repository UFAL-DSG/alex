#!/bin/bash

pushd ..

./wshub.py -c ./PublicTransportInfoCS/ptics.cfg ./PublicTransportInfoCS/kaldi.cfg ./PublicTransportInfoCS/ptics_hdc_slu.cfg


popd
