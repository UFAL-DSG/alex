FROM      ubuntu:14.04
MAINTAINER Lukas Zilka <lukas@zilka.me>

RUN apt-get update   # Run once at the beggining

# Alex prerequisites.
RUN apt-get install -y build-essential libpng12-dev libfreetype6-dev python-dev libopenblas-dev libopenblas-base liblapack-dev liblapack3 gfortran  git python python-pip libsqlite3-dev wget
RUN locale-gen en_US.UTF-8

# Clone Alex from repository.
RUN mkdir /app
WORKDIR /app
RUN git clone https://github.com/UFAL-DSG/alex.git
WORKDIR /app/alex
RUN pip install -r alex-requirements.txt
RUN pip install pystache cython flask theano
# RUN pip install --allow-unverified pyaudio --allow-unverified pyaudio pyaudio

#
# Install PyKaldi.
#
# Prerequesities.
RUN apt-get install -y build-essential libatlas-base-dev python-dev python-pip git wget
# Addid pykaldi source files
WORKDIR /app
RUN git clone https://github.com/UFAL-DSG/pykaldi.git
WORKDIR /app/pykaldi
# PyKaldi tools.
WORKDIR tools
RUN make atlas openfst_tgt
# Compile the Kaldi src.
WORKDIR ../src
RUN ./configure --shared && make && echo 'KALDI LIBRARY INSTALLED OK'
# Compile Online recogniser.
WORKDIR onl-rec
RUN make && make test && echo 'OnlineLatgenRecogniser build and test OK'
# Compile Kaldi module for Python.
WORKDIR ../../pykaldi
RUN pip install -r pykaldi-requirements.txt
RUN make install && echo 'Pykaldi build and installation files prepared: OK'
# Install locally installed Openfst to /usr/local
WORKDIR ../tools/openfst
RUN for dir in lib include bin ; do cp -r $dir /usr/local/ ; done
RUN ldconfig
# Test setup
RUN python -c 'import fst; import kaldi.decoders'
# Remove Pykaldi source files
WORKDIR /app
RUN rm -rf pykaldi



#
# Install PjSip & its Python module.
#
WORKDIR /app/
RUN git clone https://github.com/UFAL-DSG/pjsip.git
WORKDIR /app/pjsip
RUN ./configure CXXFLAGS=-fPIC CFLAGS=-fPIC LDFLAGS=-fPIC CPPFLAGS=-fPIC
RUN make dep
RUN make
RUN make install
WORKDIR /app/pjsip/pjsip-apps/src/python/
RUN python setup-pjsuaxt.py install
