#!/bin/bash

pykaldi_dir=/ha/work/people/oplatek/kaldi/src/pykaldi
export LD_LIBRARY_PATH=$pykaldi_dir:$LD_LIBRARY_PATH
export PYTHONPATH=$pykaldi_dir:$pykaldi_dir/pyfst:$PYTHONPATH


./decode_indomain.py -c kaldi.cfg
