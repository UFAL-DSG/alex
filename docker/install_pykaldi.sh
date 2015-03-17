#!/bin/bash
set -e

apt-get install -y build-essential libatlas-base-dev python-dev python-pip git wget zip
# Addid pykaldi source files
cd /app
git clone --recursive https://github.com/UFAL-DSG/pykaldi.git
cd /app/pykaldi
make install
ldconfig

# Test setup
python -c 'import fst; import kaldi.decoders'
# Remove Pykaldi source files
cd /app
rm -rf pykaldi
