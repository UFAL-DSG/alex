#!/bin/bash
set -e

apt-get install -y build-essential libatlas-base-dev python-dev python-pip git wget
# Addid pykaldi source files
cd /app
git clone https://github.com/UFAL-DSG/pykaldi.git
cd /app/pykaldi
# PyKaldi tools.
cd tools
make atlas openfst_tgt
# Compile the Kaldi src.
cd ../src
./configure --shared && make && echo 'KALDI LIBRARY INSTALLED OK'
# Compile Online recogniser.
cd onl-rec
make && make test && echo 'OnlineLatgenRecogniser build and test OK'
# Compile Kaldi module for Python.
cd ../../pykaldi
pip install -r pykaldi-requirements.txt
make install && echo 'Pykaldi build and installation files prepared: OK'
# Install locally installed Openfst to /usr/local
cd ../tools/openfst
for dir in lib include bin ; do cp -r $dir /usr/local/ ; done
ldconfig
# Test setup
python -c 'import fst; import kaldi.decoders'
# Remove Pykaldi source files
cd /app
rm -rf pykaldi
